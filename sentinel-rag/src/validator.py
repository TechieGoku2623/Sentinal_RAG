"""Two-model cross-validation for Sentinel-RAG.

==============================================================================
WHY A SECOND MODEL — CATCHING WHAT THE HEURISTIC SCORER MISSES
==============================================================================
The deterministic confidence scorer (src/reflection.py) is fast, transparent,
and auditable — but it is a *surface* heuristic. It measures vocabulary overlap,
hedging, length, and crude negation. That means it can be fooled by the most
dangerous failure mode in clinical RAG: an answer that **reuses the source's
vocabulary while misstating the relationship between those terms** (e.g. swapping
a threshold, inverting a contraindication, or adding an unsupported claim). Such
an answer scores HIGH on coverage yet is factually wrong.

Cross-validation closes that gap with an independent LLM pass acting purely as a
*fact-checker*: given the source documents and the drafted answer, it judges
whether the answer is SUPPORTED, PARTIALLY_SUPPORTED, or CONTRADICTED. This is a
defense-in-depth design:

  * The heuristic scorer is the cheap, always-on, explainable first gate.
  * The validator is a semantic second gate that reasons about entailment.

The two are complementary — a hallucination must beat BOTH the lexical heuristic
and the semantic check to reach a clinician unflagged. We run the validator at
temperature 0.0 for deterministic, reproducible verdicts.

Note: this is still an LLM and can err; it augments — never replaces — the
human-in-the-loop flag. A CONTRADICTED verdict forces escalation.
"""

from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq

from src import config
from src.chains import CONTEXT_SEPARATOR, GROQ_MODEL

load_dotenv()

logger = logging.getLogger(__name__)

# Deterministic temperature: a fact-check must be stable and reproducible.
VALIDATOR_TEMPERATURE = config.VALIDATOR_TEMPERATURE

VALIDATOR_PROMPT = """
You are a clinical fact-checker.
Read this response and the source documents carefully.

SOURCE DOCUMENTS:
{context}

RESPONSE TO VALIDATE:
{response}

Answer with ONLY one of these three options:
SUPPORTED - response is fully supported by sources
PARTIALLY_SUPPORTED - response mostly correct but adds unsupported claims
CONTRADICTED - response contradicts or fabricates information

Your answer (one word only):
"""

# Maps each verdict to a [0, 1] validation confidence.
VERDICT_CONFIDENCE = {
    "SUPPORTED": 1.0,
    "PARTIALLY_SUPPORTED": 0.6,
    "CONTRADICTED": 0.0,
}

_ERROR_RESULT = {
    "verdict": "ERROR",
    "is_valid": False,
    "should_flag": False,
    "validation_confidence": 0.0,
}

PROMPT = ChatPromptTemplate.from_messages([("human", VALIDATOR_PROMPT)])


def _build_validator_chain() -> Runnable:
    """Build the validator chain (second Groq model call, temperature 0.0)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set; cross-validation requires a Groq API key."
        )
    llm = ChatGroq(
        model=GROQ_MODEL,
        temperature=VALIDATOR_TEMPERATURE,
        api_key=api_key,
    )
    chain = PROMPT | llm | StrOutputParser()
    return chain.with_config(run_name="sentinel-rag-validation")


def _parse_verdict(text: str) -> str:
    """Extract the verdict keyword from the model's raw output.

    Order matters: ``PARTIALLY_SUPPORTED`` contains ``SUPPORTED``, so we test the
    more specific verdicts first. Returns "ERROR" if nothing recognizable is found.
    """
    t = (text or "").strip().upper()
    if "CONTRADICTED" in t:
        return "CONTRADICTED"
    if "PARTIALLY_SUPPORTED" in t or "PARTIALLY SUPPORTED" in t or "PARTIALLY" in t:
        return "PARTIALLY_SUPPORTED"
    if "SUPPORTED" in t:
        return "SUPPORTED"
    return "ERROR"


def cross_validate(response: str, context: list, query: str) -> dict:
    """Independently fact-check ``response`` against ``context`` with a 2nd model.

    Args:
        response: The drafted clinical answer to validate.
        context: The retrieved guideline chunks the answer should be grounded in.
        query: The original question (reserved for future query-aware checks;
            kept for a stable call signature).

    Returns:
        dict with keys:
          - verdict (str): SUPPORTED | PARTIALLY_SUPPORTED | CONTRADICTED | ERROR
          - is_valid (bool): True only when verdict == SUPPORTED
          - should_flag (bool): True when verdict == CONTRADICTED
          - validation_confidence (float): 1.0 / 0.6 / 0.0 by verdict
        On any API/parse error, returns an ERROR result (is_valid False) so the
        caller degrades gracefully rather than crashing.
    """
    # Nothing to validate against / nothing to validate.
    if not response or not response.strip():
        return dict(_ERROR_RESULT)
    if not context or all(not c or not c.strip() for c in context):
        return dict(_ERROR_RESULT)

    context_block = CONTEXT_SEPARATOR.join(
        c.strip() for c in context if c and c.strip()
    )

    try:
        start = time.perf_counter()
        chain = _build_validator_chain()
        raw = chain.invoke({"context": context_block, "response": response})
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        verdict = _parse_verdict(raw)
        logger.info("Cross-validation verdict=%s (response_time_ms=%d)",
                    verdict, elapsed_ms)

        if verdict == "ERROR":
            return dict(_ERROR_RESULT)

        return {
            "verdict": verdict,
            "is_valid": verdict == "SUPPORTED",
            "should_flag": verdict == "CONTRADICTED",
            "validation_confidence": VERDICT_CONFIDENCE[verdict],
        }
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        logger.error("Cross-validation failed: %s", exc)
        return dict(_ERROR_RESULT)
