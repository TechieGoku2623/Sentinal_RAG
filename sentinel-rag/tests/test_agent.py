"""Unit tests for Sentinel-RAG.

These tests are fully self-contained: ChromaDB and the Groq API are mocked, so
the suite runs with NO API keys and NO network/vector-store access. Run with:

    pytest
"""

from __future__ import annotations

import importlib

import pytest

from src import config, reflection
from src.ingest import chunk_text, chunk_with_parent_links
from src.reflection import extract_key_terms, score_confidence


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------
def test_high_confidence_response() -> None:
    """A specific, grounded answer that reuses source vocabulary scores high."""
    docs = [
        "Metformin is the recommended first-line therapy for type 2 diabetes. "
        "Initiate metformin at 500 mg once daily with the evening meal and "
        "titrate gradually. Metformin is contraindicated when eGFR is below 30."
    ]
    response = (
        "Metformin is the recommended first-line therapy for type 2 diabetes. "
        "The guideline advises initiating metformin at 500 mg once daily with "
        "the evening meal and titrating gradually. Metformin is contraindicated "
        "when eGFR falls below 30, due to the risk of lactic acidosis."
    )

    score = score_confidence(response, docs, "first-line therapy for diabetes?")

    assert score >= 0.85, f"expected high confidence, got {score}"


def test_low_confidence_empty_docs() -> None:
    """With no retrieved context, coverage is 0 so confidence stays low."""
    response = (
        "The recommended first-line therapy is metformin, titrated slowly over "
        "several weeks while monitoring renal function carefully each visit."
    )

    score = score_confidence(response, [], "first-line therapy?")

    # No grounding possible -> must fall below the medium threshold.
    assert score < 0.75, f"expected low confidence with empty docs, got {score}"


def test_uncertainty_lowers_score() -> None:
    """An explicit hedge must reduce the score versus an unhedged answer."""
    docs = [
        "Metformin is first-line therapy for type 2 diabetes and should be "
        "titrated from 500 mg daily with monitoring of renal function."
    ]
    grounded = (
        "Metformin is first-line therapy for type 2 diabetes and should be "
        "titrated from 500 mg daily with monitoring of renal function."
    )
    hedged = (
        "I'm not sure, but metformin may be first-line therapy for type 2 "
        "diabetes and should be titrated from 500 mg daily with monitoring."
    )

    confident_score = score_confidence(grounded, docs, "first-line?")
    hedged_score = score_confidence(hedged, docs, "first-line?")

    assert hedged_score < confident_score
    # The hedge zeroes the uncertainty factor (weight 0.30). The drop is close
    # to 0.30, slightly offset because the longer hedged text scores marginally
    # higher on the specificity factor. A >= 0.25 gap proves the penalty fires.
    assert confident_score - hedged_score >= 0.25


def test_extract_key_terms_filters_stopwords() -> None:
    """Stop words and tiny tokens are removed; meaningful terms remain."""
    text = "The patient should be given metformin and the dose is titrated."

    terms = extract_key_terms(text)

    # Stop words must be gone.
    for stop in ("the", "and", "is", "be"):
        assert stop not in terms
    # Meaningful clinical terms must survive.
    assert "metformin" in terms
    assert "patient" in terms
    assert "titrated" in terms
    # Respects the cap.
    assert len(terms) <= reflection.MAX_KEY_TERMS


# ---------------------------------------------------------------------------
# Reflection routing (LangGraph node)
# ---------------------------------------------------------------------------
_SUPPORTED = {
    "verdict": "SUPPORTED",
    "is_valid": True,
    "should_flag": False,
    "validation_confidence": 1.0,
}


def test_reflect_routes_to_output_high_confidence(mocker) -> None:
    """High confidence routes straight to output without flagging."""
    import src.agent as agent_module

    mocker.patch.object(agent_module, "score_confidence", return_value=0.92)
    mocker.patch.object(agent_module, "score_query_alignment", return_value=0.8)
    mocker.patch.object(agent_module, "cross_validate", return_value=_SUPPORTED)

    state = {
        "query": "first-line therapy?",
        "retrieved_docs": ["some guideline text"],
        "response": "a grounded clinical answer",
        "confidence": 0.0,
        "flagged": False,
        "retry_count": 0,
        "route": "",
        "timestamp": "",
    }

    new_state = agent_module.reflect_node(state)

    assert new_state["route"] == "output"
    assert new_state["flagged"] is False
    assert new_state["confidence"] == 0.92


def test_reflect_routes_to_flag_after_max_retries(mocker) -> None:
    """PARTIALLY_SUPPORTED with low confidence after retries must flag."""
    import src.agent as agent_module

    mocker.patch.object(agent_module, "score_confidence", return_value=0.78)
    mocker.patch.object(agent_module, "score_query_alignment", return_value=0.8)
    mocker.patch.object(agent_module, "cross_validate", return_value={
        "verdict": "PARTIALLY_SUPPORTED",
        "is_valid": False,
        "should_flag": False,
        "validation_confidence": 0.6,
    })

    state = {
        "query": "ambiguous question?",
        "retrieved_docs": ["some guideline text"],
        "response": "a borderline answer",
        "confidence": 0.0,
        "flagged": False,
        "retry_count": agent_module.MAX_RETRIES,  # 2
        "route": "",
        "timestamp": "",
    }

    new_state = agent_module.reflect_node(state)

    assert new_state["route"] == "flag"
    assert new_state["flagged"] is True


def test_reflect_contradicted_overrides_high_confidence(mocker) -> None:
    """A CONTRADICTED verdict must flag even when the lexical score is high."""
    import src.agent as agent_module

    mocker.patch.object(agent_module, "score_confidence", return_value=0.95)
    mocker.patch.object(agent_module, "score_query_alignment", return_value=0.9)
    mocker.patch.object(agent_module, "cross_validate", return_value={
        "verdict": "CONTRADICTED",
        "is_valid": False,
        "should_flag": True,
        "validation_confidence": 0.0,
    })

    state = {
        "query": "q?",
        "retrieved_docs": ["guideline text"],
        "response": "a fluent but contradicting answer",
        "confidence": 0.0,
        "flagged": False,
        "retry_count": 0,
        "route": "",
        "timestamp": "",
    }

    new_state = agent_module.reflect_node(state)

    assert new_state["route"] == "flag"
    assert new_state["flagged"] is True
    assert new_state["validation_verdict"] == "CONTRADICTED"


def test_reflect_partial_support_reduces_confidence(mocker) -> None:
    """PARTIALLY_SUPPORTED lowers confidence by the configured penalty."""
    import src.agent as agent_module

    mocker.patch.object(agent_module, "score_confidence", return_value=0.90)
    mocker.patch.object(agent_module, "score_query_alignment", return_value=0.8)
    mocker.patch.object(agent_module, "cross_validate", return_value={
        "verdict": "PARTIALLY_SUPPORTED",
        "is_valid": False,
        "should_flag": False,
        "validation_confidence": 0.6,
    })

    state = {
        "query": "q?",
        "retrieved_docs": ["guideline text"],
        "response": "mostly right but adds a claim",
        "confidence": 0.0,
        "flagged": False,
        "retry_count": 0,
        "route": "",
        "timestamp": "",
    }

    new_state = agent_module.reflect_node(state)

    # 0.90 - 0.15 = 0.75 — still routes to output when SUPPORTED would boost;
    # with PARTIAL, 0.75 is at medium threshold; verify penalty applied.
    assert abs(new_state["confidence"] - 0.75) < 1e-6


def test_decide_route_supported_in_corpus_releases(mocker) -> None:
    from src.reflection import decide_reflection_route

    route, flagged, reason, conf = decide_reflection_route(
        response="Metformin is first-line.",
        confidence=0.62,
        verdict="SUPPORTED",
        alignment=0.8,
        retry_count=2,
        corpus_grounded=True,
    )
    assert route == "output"
    assert flagged is False
    assert conf >= 0.85


def test_decide_route_corpus_grounded_releases_at_medium(mocker) -> None:
    from src.reflection import decide_reflection_route

    route, flagged, reason, conf = decide_reflection_route(
        response="Metformin is first-line.",
        confidence=0.78,
        verdict="ERROR",
        alignment=0.8,
        retry_count=0,
        corpus_grounded=True,
    )
    assert route == "output"
    assert flagged is False
    assert conf >= 0.85


def test_decide_route_out_of_scope_flags(mocker) -> None:
    from src.reflection import decide_reflection_route

    route, flagged, reason, _ = decide_reflection_route(
        response="Naloxone reverses overdose.",
        confidence=0.9,
        verdict="SUPPORTED",
        alignment=0.0,
        retry_count=0,
    )
    assert route == "flag"
    assert flagged is True
    assert reason == "out_of_scope"


def test_query_alignment_naloxone_not_in_diabetes_guideline() -> None:
    from src.reflection import score_query_alignment

    docs = ["Metformin is first-line therapy for type 2 diabetes mellitus."]
    score = score_query_alignment(
        "What medication reverses an opioid overdose with naloxone?",
        docs,
    )
    assert score < config.QUERY_ALIGNMENT_MIN


def test_query_alignment_hypertension_not_in_diabetes_guideline() -> None:
    from src.reflection import score_query_alignment

    docs = ["Metformin is first-line therapy for type 2 diabetes mellitus."]
    score = score_query_alignment(
        "What are the first-line drug classes for hypertension?",
        docs,
    )
    assert score < config.QUERY_ALIGNMENT_MIN


def test_query_alignment_diabetes_question_in_corpus() -> None:
    from src.reflection import has_corpus_anchor, score_query_alignment

    docs = [
        "Metformin is first-line therapy for adults with type 2 diabetes mellitus.",
        "The general HbA1c target is less than 7.0 percent.",
    ]
    query = "What is the first-line treatment for Type 2 diabetes?"
    assert has_corpus_anchor(query, docs)
    assert score_query_alignment(query, docs) >= config.QUERY_ALIGNMENT_MIN


def test_query_alignment_metformin_contrast_in_corpus() -> None:
    from src.reflection import has_corpus_anchor, score_query_alignment

    docs = [
        "Metformin should be temporarily discontinued for iodinated contrast procedures.",
    ]
    query = "Why should metformin be held around iodinated contrast procedures?"
    assert has_corpus_anchor(query, docs)
    assert score_query_alignment(query, docs) >= config.QUERY_ALIGNMENT_MIN


# ---------------------------------------------------------------------------
# Chunking (parent-child)
# ---------------------------------------------------------------------------
def test_chunk_text_child_overlap() -> None:
    """Child mode: 100-word chunks overlapping by 20 words."""
    words = [f"w{i}" for i in range(260)]
    text = " ".join(words)

    chunks = chunk_text(text, mode="child")

    # 260 words at step 80 (100 - 20) -> multiple chunks.
    assert len(chunks) >= 3

    first = chunks[0].split()
    second = chunks[1].split()
    assert len(first) == 100
    # Last 20 words of chunk 1 equal the first 20 of chunk 2.
    assert first[-20:] == second[:20]


def test_chunk_text_parent_size() -> None:
    """Parent mode produces larger 500-word chunks."""
    words = [f"w{i}" for i in range(1200)]
    chunks = chunk_text(" ".join(words), mode="parent")
    assert len(chunks[0].split()) == 500


def test_chunk_text_invalid_mode() -> None:
    with pytest.raises(ValueError):
        chunk_text("some text", mode="grandparent")


def test_chunk_with_parent_links() -> None:
    """Every child links to a real parent; IDs follow the naming scheme."""
    words = [f"w{i}" for i in range(700)]
    items = chunk_with_parent_links(" ".join(words), "mydoc")

    parents = [it for it in items if it["chunk_type"] == "parent"]
    children = [it for it in items if it["chunk_type"] == "child"]

    assert parents and children
    assert parents[0]["id"].startswith("parent_mydoc_")
    assert children[0]["id"].startswith("child_mydoc_")

    parent_ids = {it["id"] for it in parents}
    assert all(c["parent_id"] in parent_ids for c in children)
    assert all(it["doc_name"] == "mydoc" for it in items)


# ---------------------------------------------------------------------------
# Sanity: agent module imports without API keys (Groq/Chroma not contacted)
# ---------------------------------------------------------------------------
def test_agent_module_imports_without_keys(mocker) -> None:
    """Importing the agent must not require Groq/Chroma connectivity."""
    # Re-import to ensure module-level code (build_agent) is safe to run.
    import src.agent as agent_module

    importlib.reload(agent_module)
    assert hasattr(agent_module, "run_agent")
    assert callable(agent_module.run_agent)
