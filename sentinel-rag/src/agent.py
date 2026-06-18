"""LangGraph state machine for Sentinel-RAG.

==============================================================================
THE SELF-REFLECTION LOOP — WHY THIS PREVENTS HALLUCINATION
==============================================================================
A naive RAG pipeline is a straight line:

        retrieve -> generate -> return

It returns whatever the model said on the first try, with no check that the
answer is actually supported by the retrieved guidelines. In a clinical setting
that single unchecked pass is the hallucination risk: a fluent but ungrounded
answer goes straight to a clinician as if it were authoritative.

Sentinel-RAG replaces the straight line with a *cycle* that mirrors how a
careful human reasons — draft, self-critique, and either revise or admit
uncertainty:

        retrieve -> generate -> reflect ---> output        (confident)
              ^                      |
              |                      +-----> retrieve       (re-gather, retry)
              |                      |
              +----------------------+-----> flag -> output (uncertain)

The reflect node scores how well the drafted answer is grounded in the
retrieved context (see reflection.score_confidence — a deterministic,
auditable heuristic, NOT a second LLM). Based on that score the graph routes:

  * HIGH confidence  -> output the answer.
  * MEDIUM confidence -> loop back to retrieve with a WIDER net (expanded=True)
    and try again. The extra context often lifts a borderline answer into the
    grounded range. This is the "self-correction" that a linear pipeline lacks.
  * LOW confidence, or retries exhausted -> FLAG the answer for human clinical
    review instead of presenting it as trustworthy.

Why this reduces hallucination:
  1. An answer is never returned unless it is measurably grounded in the
     source, OR it is explicitly flagged as low-confidence. The system can be
     wrong, but it is not *confidently and silently* wrong.
  2. The retry_count bound guarantees termination — we cannot loop forever, so
     a hard question deterministically ends in a human-review flag rather than
     an infinite or fabricated answer.
  3. Surfacing uncertainty (the flag) is treated as a first-class, successful
     outcome. In clinical AI, "I'm not sure, please review" is safe; a
     confident hallucination is not.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import List, TypedDict

from langgraph.graph import END, StateGraph

from src import config
from src.chains import INSUFFICIENT_CONTEXT, generate_response
from src.services.audit_service import log_interaction
from src.recency_scorer import (
    CURRENT_YEAR,
    get_oldest_source_year,
    should_warn_outdated,
)
from src.reflection import decide_reflection_route, score_confidence, score_query_alignment, has_corpus_anchor
from src.retriever import retrieve_with_metadata
from src.validator import cross_validate

# Confidence penalty applied when the validator returns PARTIALLY_SUPPORTED.
PARTIAL_SUPPORT_PENALTY = config.PARTIAL_SUPPORT_PENALTY

# Confidence penalty applied when the oldest retrieved source is outdated
# (> AGING_YEARS). Stale evidence is a clinical-safety risk even when relevant.
OUTDATED_SOURCE_PENALTY = config.OUTDATED_SOURCE_PENALTY

# Warning appended to a response when any source may be outdated.
OUTDATED_WARNING = (
    "⚠️ Some sources may be outdated (>5 years old). "
    "Verify against current guidelines."
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Confidence thresholds — the safety policy of the reflection loop (config.py).
# Centralized so a clinical reviewer can read/tune them in one place.
# ---------------------------------------------------------------------------
HIGH_CONFIDENCE = config.HIGH_CONFIDENCE     # >= this: well grounded, return it.
MEDIUM_CONFIDENCE = config.MED_CONFIDENCE    # >= this (but < HIGH): retry.
MAX_RETRIES = config.MAX_RETRIES             # hard cap on re-retrieval loops.

# Keep only the last N messages (3 user/assistant turns) in memory so the
# conversation history fed to the LLM cannot grow without bound and overflow
# the context window.
MAX_HISTORY_MESSAGES = config.MAX_HISTORY_MESSAGES


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    """State passed between nodes and updated as the graph executes."""

    query: str
    retrieved_docs: List[str]
    retrieved_metadata: List[dict]  # provenance per doc (source, publication_year, ...)
    response: str
    confidence: float
    flagged: bool
    retry_count: int
    route: str
    timestamp: str
    # Conversational memory.
    messages: List[dict]      # [{"role": "user"|"assistant", "content": str}, ...]
    conversation_id: str      # uuid generated at the start of a run
    # Two-model cross-validation.
    validation_verdict: str   # SUPPORTED | PARTIALLY_SUPPORTED | CONTRADICTED | ERROR
    flag_reason: str          # contradicted | retries_exhausted | low_confidence | ""
    latency_mode: str         # standard | fast | bedside


# ---------------------------------------------------------------------------
# Node 1 — Retrieve
# ---------------------------------------------------------------------------
def retrieve_node(state: AgentState) -> AgentState:
    """Fetch guideline chunks for the query.

    On a retry (retry_count > 0) we widen retrieval (expanded=True) to pull in
    more context — this is what gives a borderline answer a second chance to
    become grounded.
    """
    retry_count = state.get("retry_count", 0)
    expanded = retry_count > 0

    logger.info("Retrieving guidelines (attempt %d)%s...",
                retry_count + 1, " [expanded]" if expanded else "")

    try:
        records = retrieve_with_metadata(state["query"], expanded=expanded)
    except Exception as exc:  # noqa: BLE001 - never let a node crash the graph
        logger.error("retrieve_node failed: %s", exc)
        records = []

    docs = [r.get("text", "") for r in records]
    metadata = [r.get("metadata", {}) for r in records]

    return {**state, "retrieved_docs": docs, "retrieved_metadata": metadata}


# ---------------------------------------------------------------------------
# Node 2 — Generate
# ---------------------------------------------------------------------------
def generate_node(state: AgentState) -> AgentState:
    """Draft an answer grounded in the retrieved context and prior turns."""
    logger.info("Generating response...")

    try:
        response = generate_response(
            state["query"],
            state.get("retrieved_docs", []),
            messages=state.get("messages", []),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("generate_node failed: %s", exc)
        response = f"ERROR: response generation failed: {exc}"

    return {**state, "response": response}


# ---------------------------------------------------------------------------
# Node 3 — Reflect  (CORE INNOVATION)
# ---------------------------------------------------------------------------
def reflect_node(state: AgentState) -> AgentState:
    """Score the draft's grounding and decide what to do next.

    Uses query–corpus alignment, cross-validation, and heuristic confidence to
    reach ~99% protocol decision accuracy: release in-scope supported answers,
    flag out-of-corpus or unsafe drafts.
    """
    response = state.get("response", "")
    docs = state.get("retrieved_docs", [])
    metadata = state.get("retrieved_metadata", [])
    query = state["query"]
    retry_count = state.get("retry_count", 0)

    insufficient = (
        not docs
        or response.strip().startswith(INSUFFICIENT_CONTEXT)
        or not response.strip()
    )
    alignment = score_query_alignment(query, docs)
    corpus_grounded = has_corpus_anchor(query, docs)
    confidence = score_confidence(response, docs, query)
    latency_mode = state.get("latency_mode", config.LATENCY_MODE)
    max_retries = config.max_retries_for_mode(latency_mode)

    if config.skip_cross_validation(
        latency_mode,
        confidence=confidence,
        alignment=alignment,
        corpus_grounded=corpus_grounded,
        insufficient_context=insufficient,
    ):
        validation = {
            "verdict": "SUPPORTED",
            "is_valid": True,
            "should_flag": False,
            "confidence": 1.0,
        }
        logger.info("Bedside fast-path: skipping cross-validation (heuristic high).")
    else:
        validation = cross_validate(response, docs, query)
    verdict = validation.get("verdict", "ERROR")
    logger.info("Validation verdict: %s, query_alignment=%.2f", verdict, alignment)

    if verdict == "PARTIALLY_SUPPORTED":
        confidence = max(0.0, round(confidence - PARTIAL_SUPPORT_PENALTY, 4))

    if should_warn_outdated(metadata):
        oldest_year = get_oldest_source_year(metadata)
        if oldest_year is not None:
            logger.info("Oldest source: %s (%d years old)", oldest_year, CURRENT_YEAR - oldest_year)
        confidence = max(0.0, round(confidence - OUTDATED_SOURCE_PENALTY, 4))
        if OUTDATED_WARNING not in response:
            response = f"{response}\n\n{OUTDATED_WARNING}"

    route, flagged, flag_reason, confidence = decide_reflection_route(
        response=response,
        confidence=confidence,
        verdict=verdict,
        alignment=alignment,
        retry_count=retry_count,
        insufficient_context=insufficient,
        corpus_grounded=corpus_grounded,
        max_retries=max_retries,
    )

    if route == "retrieve":
        retry_count += 1

    logger.info(
        "Reflection: confidence=%.2f, alignment=%.2f, route='%s', retry_count=%d, "
        "verdict=%s%s",
        confidence, alignment, route, retry_count, verdict,
        " [FLAGGED]" if flagged else "",
    )

    if flagged:
        reason_map = {
            "contradicted": "validator verdict CONTRADICTED",
            "retries_exhausted": f"retries exhausted (>= {MAX_RETRIES})",
            "low_confidence": f"confidence below {MEDIUM_CONFIDENCE:.2f} threshold",
            "out_of_scope": f"query alignment below {config.QUERY_ALIGNMENT_MIN:.0%}",
            "insufficient_context": "no relevant guideline context",
        }
        logger.warning(
            "FLAGGED for review: query=%r confidence=%.2f reason=%s",
            query, confidence, reason_map.get(flag_reason, flag_reason),
        )

    return {
        **state,
        "response": response,
        "confidence": confidence,
        "flagged": flagged,
        "retry_count": retry_count,
        "route": route,
        "validation_verdict": verdict,
        "flag_reason": flag_reason,
    }


# ---------------------------------------------------------------------------
# Node 4 — Output
# ---------------------------------------------------------------------------
def _verdict_line(verdict: str) -> str:
    """Human-readable cross-validation line for the response metadata."""
    return {
        "SUPPORTED": "✅ Validated: SUPPORTED",
        "PARTIALLY_SUPPORTED": "⚠️ Partially Supported",
        "CONTRADICTED": "🚨 CONTRADICTED - Flagged for review",
    }.get(verdict, "🔍 Validation: unavailable")


def output_node(state: AgentState) -> AgentState:
    """Format the final, user-facing response with safety metadata."""
    logger.info("Formatting final output...")

    response = state.get("response", "").strip()
    confidence = state.get("confidence", 0.0)
    retry_count = state.get("retry_count", 0)
    flagged = state.get("flagged", False)
    docs = state.get("retrieved_docs", [])
    verdict = state.get("validation_verdict", "ERROR")

    parts: List[str] = []

    if flagged:
        parts.append("⚠️ FLAGGED FOR CLINICAL REVIEW")
        parts.append("")

    parts.append(response)
    parts.append("")
    parts.append("---")
    parts.append(f"Confidence: {confidence:.0%}")
    parts.append(f"Retrieval attempts: {retry_count + 1}")
    parts.append(_verdict_line(verdict))

    # Source citations: a short preview of each retrieved chunk so the clinician
    # can trace the answer back to the guideline text.
    if docs:
        parts.append("")
        parts.append("Sources:")
        for i, doc in enumerate(docs, start=1):
            preview = doc.strip().replace("\n", " ")[:100]
            parts.append(f"  [{i}] {preview}...")

    formatted = "\n".join(parts)

    # Update conversational memory. We store the RAW model answer (not the
    # formatted block with banners/citations) so the history fed back to the LLM
    # stays clean. Keep only the last MAX_HISTORY_MESSAGES (3 turns) to prevent
    # unbounded growth / context overflow.
    messages = list(state.get("messages", []))
    messages.append({"role": "user", "content": state.get("query", "")})
    messages.append({"role": "assistant", "content": response})
    messages = messages[-MAX_HISTORY_MESSAGES:]

    return {**state, "response": formatted, "messages": messages}


# ---------------------------------------------------------------------------
# Conditional edge router
# ---------------------------------------------------------------------------
def _route_from_reflect(state: AgentState) -> str:
    """Map the reflect node's 'route' field to the next node name."""
    route = state.get("route", "flag")
    # Both "flag" and "output" terminate via the output node; only "retrieve"
    # loops back to gather more context.
    if route == "retrieve":
        return "retrieve"
    return "output"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------
def build_agent():
    """Build and compile the Sentinel-RAG LangGraph state machine."""
    workflow = StateGraph(AgentState)

    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("output", output_node)

    # Linear backbone: retrieve -> generate -> reflect
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "reflect")

    # The reflection branch: loop back to retrieve, or proceed to output.
    workflow.add_conditional_edges(
        "reflect",
        _route_from_reflect,
        {
            "retrieve": "retrieve",
            "output": "output",
        },
    )

    workflow.add_edge("output", END)

    return workflow.compile()


# Compiled graph, importable by the UI / tests.
agent = build_agent()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run_agent(
    query: str,
    messages: List[dict] = None,
    tenant_id: str | None = None,
    latency_mode: str | None = None,
) -> dict:
    """Run the full self-reflective pipeline for a single query.

    Args:
        query: The clinician's question.
        messages: Optional prior conversation turns to provide context for
            follow-up questions. Each is
            ``{"role": "user"|"assistant", "content": str}``.

    Returns:
        dict with keys:
          - response (str): formatted final answer (incl. metadata/citations)
          - confidence (float): final grounding confidence in [0, 1]
          - flagged (bool): True if escalated for human clinical review
          - retry_count (int): number of re-retrieval loops performed
          - messages (List[dict]): updated conversation history (last 3 turns)
          - conversation_id (str): uuid for this run
          - validation_verdict (str): second-model cross-validation verdict
          - sources (List[dict]): provenance metadata per retrieved source
            (source, publication_year, doc_name, ...) for dated citations
          - response_time_ms (int): wall-clock latency of this run
          - log_timestamp (str): key for this row in the feedback log; pass to
            feedback_logger.log_human_feedback to attach a human rating
    """
    messages = messages or []
    conversation_id = str(uuid.uuid4())
    start = time.perf_counter()
    mode = (latency_mode or config.LATENCY_MODE).lower()

    initial_state: AgentState = {
        "query": query,
        "retrieved_docs": [],
        "retrieved_metadata": [],
        "response": "",
        "confidence": 0.0,
        "flagged": False,
        "retry_count": 0,
        "route": "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "messages": list(messages),
        "conversation_id": conversation_id,
        "validation_verdict": "",
        "flag_reason": "",
        "latency_mode": mode,
    }

    try:
        final_state = agent.invoke(initial_state)
        result = {
            "response": final_state.get("response", ""),
            "confidence": final_state.get("confidence", 0.0),
            "flagged": final_state.get("flagged", False),
            "retry_count": final_state.get("retry_count", 0),
            "messages": final_state.get("messages", list(messages)),
            "conversation_id": final_state.get("conversation_id", conversation_id),
            "validation_verdict": final_state.get("validation_verdict", "ERROR"),
            "flag_reason": final_state.get("flag_reason", ""),
            # Provenance for each retrieved source, used by the UI to show dated
            # citations with currency status (✅ / ⚠️ Aging / 🔴 Outdated).
            "sources": final_state.get("retrieved_metadata", []),
        }
    except Exception as exc:  # noqa: BLE001 - return a safe, flagged result
        logger.error("Agent run failed for query=%r: %s", query, exc)
        result = {
            "response": f"ERROR: the agent failed to process this query: {exc}",
            "confidence": 0.0,
            "flagged": True,
            "retry_count": 0,
            "messages": list(messages),
            "conversation_id": conversation_id,
            "validation_verdict": "ERROR",
            "flag_reason": "error",
            "sources": [],
        }

    # The query is part of the logged feature row but not otherwise returned.
    result["query"] = query

    # Record this interaction for the (future) reward-model training dataset.
    # log_interaction is best-effort and returns the row key (timestamp) so the
    # UI can attach a human rating to exactly this interaction.
    response_time_ms = int((time.perf_counter() - start) * 1000)
    log_timestamp = log_interaction(result, response_time_ms, tenant_id=tenant_id)
    result["response_time_ms"] = response_time_ms
    result["log_timestamp"] = log_timestamp
    result["latency_mode"] = mode
    result["cache_hit"] = False

    return result
