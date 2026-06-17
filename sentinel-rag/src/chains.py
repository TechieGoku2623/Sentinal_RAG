"""LLM chains and prompts for Sentinel-RAG.

This module wires the language model to the clinical RAG prompt and exposes a
single ``generate_response`` entry point used by the agent.

==============================================================================
WHY GROQ + LLAMA 3.1 8B INSTANT INSTEAD OF GPT-4
==============================================================================
The model choice here is driven by the same privacy/safety posture as the rest
of Sentinel-RAG (see retriever.py):

1. Open-source weights / self-hostable. Llama 3.1 is openly licensed. Today we
   call it via Groq's hosted API for convenience and speed, but the *exact same
   model* can be run on-premise (vLLM, Ollama, TGI) with zero code changes
   beyond the client. With GPT-4 there is no such escape hatch — you are
   permanently locked to a closed endpoint you cannot bring inside a hospital
   network. For clinical data this matters: it preserves a path to a fully
   air-gapped deployment.

2. HIPAA-friendlier data handling. A self-hostable open model means PHI-adjacent
   prompts never have to leave the institution's trust boundary. Even using
   Groq's API, the model itself is portable, so the architecture is not built
   on a vendor that can change terms or retain data in ways outside our control.

3. Inference speed. Groq's LPU hardware serves Llama 3.1 8B at roughly ~500
   tokens/second — dramatically faster than typical GPT-4 latency. Sentinel-RAG
   is a *self-reflective* agent: a single user question may trigger multiple LLM
   passes (draft -> reflect -> re-retrieve -> redraft). Cheap, fast inference is
   what makes that reflection loop practical in an interactive clinical UI
   instead of painfully slow.

4. Cost. An 8B open model on Groq is a fraction of GPT-4 pricing, which keeps
   the multi-pass reflection design economically viable at scale.

Trade-off acknowledged: an 8B model is less capable than GPT-4 on raw reasoning.
Sentinel-RAG compensates with strict grounding (retrieval) + the deterministic
confidence/reflection layer (reflection.py) rather than relying on a single
large model's unverified output — which is the safer architecture for clinical
use regardless of model size.
"""

from __future__ import annotations

import logging
import os
from typing import List

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq

from src import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment / configuration
# ---------------------------------------------------------------------------
# Load variables from .env (GROQ_API_KEY, LangSmith config) into the process
# environment. Safe to call at import time; it is a no-op if already loaded.
load_dotenv()

# --- LangSmith tracing -----------------------------------------------------
# Simply having these environment variables set causes LangChain to emit traces
# automatically for every chain/LLM invocation — no extra instrumentation code
# is needed. We re-assert them here so the behavior is explicit and works even
# if the process didn't inherit them from the shell.
#
# Tracing clinical prompts/responses is valuable for safety review: every
# generation (and its retrieved context) becomes inspectable in LangSmith.
if os.getenv("LANGCHAIN_TRACING_V2"):
    os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
if os.getenv("LANGCHAIN_PROJECT"):
    os.environ["LANGCHAIN_PROJECT"] = os.getenv(
        "LANGCHAIN_PROJECT", config.LANGCHAIN_PROJECT_DEFAULT
    )

# --- Model configuration (see src/config.py) -------------------------------
# Low temperature: clinical guidance must be deterministic and faithful to the
# source, not "creative". 0.1 keeps a sliver of fluency while strongly favoring
# the most-grounded continuation.
GROQ_MODEL = config.LLM_MODEL
GROQ_TEMPERATURE = config.LLM_TEMPERATURE

# Sentinel value returned (not raised) when there is no context to ground an
# answer. The agent/UI detects this prefix and shows a safe "no guidelines"
# message instead of letting the model answer from memory.
INSUFFICIENT_CONTEXT = (
    "INSUFFICIENT_CONTEXT: No relevant guidelines found. Please add clinical "
    "guidelines to the knowledge base."
)

# Separator used when concatenating retrieved chunks into one context block.
CONTEXT_SEPARATOR = "\n\n---\n\n"


# ---------------------------------------------------------------------------
# Clinical RAG prompt
# ---------------------------------------------------------------------------
# This system prompt is the behavioral contract. Every instruction here is a
# guardrail against the specific ways an LLM can be unsafe in a clinical RAG
# setting: answering beyond evidence, hiding uncertainty, or inventing citations.
CLINICAL_SYSTEM_PROMPT = """You are Sentinel-RAG, a clinical protocol validator.

Your role is to answer clinical questions STRICTLY using the provided guideline \
context. You support clinicians; you do not replace their judgment.

Follow these rules without exception:
1. ONLY answer based on the provided context below. Do not use outside or prior \
knowledge.
2. If the context does not contain enough information to answer safely, STATE \
THIS EXPLICITLY (e.g. "The provided guidelines do not address this."). Do NOT \
guess or extrapolate beyond what the context states.
3. NEVER fabricate dosages, thresholds, contraindications, or recommendations \
that are not present in the context.
4. When possible, CITE the specific guideline section, heading, or phrasing you \
relied on so the clinician can verify it.
5. Use clear, precise medical language. Be concise but include relevant \
conditions, contraindications, and monitoring the context mentions.
6. If the context is ambiguous or appears to conflict, surface that ambiguity \
rather than resolving it silently.

Your answer will be independently checked for grounding, so faithfulness to the \
context matters more than sounding confident."""

# The human message is assembled in Python (see _build_user_block) so the
# conversation-history section can be included conditionally. The system prompt
# above carries the full safety guardrails; the user block carries the
# structured task (history + retrieved context + current question).
PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CLINICAL_SYSTEM_PROMPT),
        ("human", "{user_block}"),
    ]
)

# How many of the most recent messages to surface as conversation history.
HISTORY_WINDOW = config.HISTORY_WINDOW


def _format_history(messages: List[dict]) -> str:
    """Format the last ``HISTORY_WINDOW`` messages as a plain history string.

    Each message is ``{"role": "user"|"assistant", "content": str}``. Returns
    an empty string when there is no usable history.
    """
    if not messages:
        return ""
    recent = [m for m in messages if m.get("content", "").strip()][-HISTORY_WINDOW:]
    lines = []
    for m in recent:
        speaker = "User" if m.get("role") == "user" else "Assistant"
        lines.append(f"{speaker}: {m.get('content', '').strip()}")
    return "\n".join(lines)


def _build_user_block(query: str, context_block: str, messages: List[dict]) -> str:
    """Assemble the structured human-message body, including history if present."""
    history = _format_history(messages)
    history_section = (
        f"CONVERSATION HISTORY:\n{history}\n\n" if history else ""
    )
    return (
        "You are Sentinel-RAG, a clinical protocol validator.\n"
        "Only answer from provided context.\n"
        "Never guess beyond what context states.\n\n"
        f"{history_section}"
        f"RETRIEVED CLINICAL GUIDELINES:\n{context_block}\n\n"
        f"CURRENT QUESTION:\n{query}\n\n"
        "Validated Response:"
    )


# ---------------------------------------------------------------------------
# LLM + chain construction
# ---------------------------------------------------------------------------
def _build_llm() -> ChatGroq:
    """Instantiate the Groq chat model.

    Reads GROQ_API_KEY from the environment (loaded from .env above). Raised
    lazily inside generate_response's try/except so a missing key produces a
    helpful message instead of an import-time crash.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "Groq API key (get one at https://console.groq.com)."
        )

    return ChatGroq(
        model=GROQ_MODEL,
        temperature=GROQ_TEMPERATURE,
        api_key=api_key,
    )


def _build_chain() -> Runnable:
    """Compose prompt -> Groq LLM -> string output.

    The ``run_name`` config tags every invocation in LangSmith as
    "sentinel-rag-generation" so generation traces are easy to find and review.
    """
    llm = _build_llm()
    chain = PROMPT | llm | StrOutputParser()
    return chain.with_config(run_name="sentinel-rag-generation")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_response(query: str, context: List[str],
                      messages: List[dict] = None) -> str:
    """Generate a grounded clinical answer for ``query`` from ``context``.

    Args:
        query: The clinician's question.
        context: Retrieved guideline chunks (most relevant first).
        messages: Optional prior conversation turns
            (``[{"role": ..., "content": ...}, ...]``). The last few are added
            to the prompt as CONVERSATION HISTORY so follow-up questions keep
            context. History never overrides the "answer only from context"
            rule — retrieved guidelines remain the sole source of truth.

    Returns:
        The model's answer (whitespace-stripped). If no context is provided,
        returns the INSUFFICIENT_CONTEXT sentinel so the caller can show a safe
        "no guidelines loaded" message instead of an ungrounded guess. On API
        errors, returns a descriptive error string rather than raising, so the
        UI/agent can degrade gracefully.
    """
    messages = messages or []

    # No context => refuse to answer from parametric memory. This is the most
    # important safety branch: an empty knowledge base must never produce a
    # confident-sounding clinical answer.
    if not context or all(not c or not c.strip() for c in context):
        logger.warning("generate_response called with empty context; refusing.")
        return INSUFFICIENT_CONTEXT

    context_block = CONTEXT_SEPARATOR.join(
        c.strip() for c in context if c and c.strip()
    )
    user_block = _build_user_block(query, context_block, messages)
    query_length = len(query)

    # Retry once on a transient API error (timeout / rate limit), then degrade
    # gracefully. A clinical UI must never surface a raw stack trace.
    last_exc: Exception | None = None
    for attempt in range(1 + config.HTTP_MAX_RETRIES):
        try:
            logger.info(
                "Generating response via Groq '%s' (query_length=%d, "
                "history_turns=%d, attempt=%d)",
                GROQ_MODEL, query_length, len(messages), attempt + 1,
            )
            chain = _build_chain()
            response = chain.invoke({"user_block": user_block}).strip()
            logger.info("Generation OK (query_length=%d, response_length=%d)",
                        query_length, len(response))
            return response
        except Exception as exc:  # noqa: BLE001 - degrade gracefully for the UI
            last_exc = exc
            logger.warning("Groq generation attempt %d failed: %s",
                           attempt + 1, exc)

    logger.error("Groq generation failed after %d attempt(s): %s",
                 1 + config.HTTP_MAX_RETRIES, last_exc)
    return (
        "ERROR: Failed to generate a response from the Groq API. "
        f"Details: {last_exc}"
    )
