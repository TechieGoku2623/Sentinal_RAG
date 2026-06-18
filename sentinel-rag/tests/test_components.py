"""Component tests for Sentinel-RAG.

These complement tests/test_agent.py and exercise the retriever, chains, agent
graph, and ingest loaders — all with ChromaDB and the Groq API mocked, so the
suite runs with no API keys and no network. They also keep meaningful code
coverage across the src package.
"""

from __future__ import annotations

import os

import pytest

import src.agent as agent_module
import src.chains as chains_module
import src.feedback_logger as feedback_module
import src.ingest as ingest_module
import src.recency_scorer as recency
import src.retriever as retriever_module
import src.validator as validator_module
from src.data_sources import pubmed as pubmed_module
from src.services.retrieval_cache import clear_retrieval_cache


@pytest.fixture(autouse=True)
def _no_disk_feedback(mocker):
    """Stop run_agent tests from writing the real feedback CSV to disk."""
    mocker.patch.object(agent_module, "log_interaction", return_value="ts-test")


@pytest.fixture(autouse=True)
def _isolated_retrieval_cache():
    clear_retrieval_cache()
    yield
    clear_retrieval_cache()
from src.chains import INSUFFICIENT_CONTEXT, generate_response
from src.ingest import load_pdf_file, load_txt_file
from src.validator import cross_validate
from src.retriever import (
    get_collection_count,
    ingest_guidelines,
    retrieve_guidelines,
)


# ---------------------------------------------------------------------------
# Retriever (ChromaDB mocked)
# ---------------------------------------------------------------------------
class _FakeCollection:
    """Minimal stand-in for a ChromaDB collection used by retriever tests."""

    def __init__(self, count=0, docs=None, metadatas=None, store=None):
        self._count = count
        self._docs = docs or []
        self._metas = metadatas or []
        self._store = store or {}  # id -> document, backs .get(ids=...)
        self.upserted = None

    def count(self):
        return self._count

    def query(self, query_texts, n_results, include=None):
        return {
            "documents": [self._docs[:n_results]],
            "metadatas": [self._metas[:n_results]],
        }

    def get(self, ids, include=None):
        return {
            "ids": list(ids),
            "documents": [self._store.get(i, "") for i in ids],
            "metadatas": [{} for _ in ids],
        }

    def upsert(self, documents, ids, metadatas=None):
        self.upserted = {"documents": documents, "ids": ids, "metadatas": metadatas}
        self._count = len(documents)


def test_retrieve_returns_empty_when_collection_empty(mocker) -> None:
    mocker.patch.object(retriever_module, "get_child_collection",
                        return_value=_FakeCollection(count=0))
    assert retrieve_guidelines("any query") == []


def test_retrieve_resolves_parents_from_children(mocker) -> None:
    # Two child hits map to two distinct parents (with a duplicate parent_id).
    child = _FakeCollection(
        count=10,
        docs=["child a", "child a2", "child b"],
        metadatas=[
            {"parent_id": "p1"},
            {"parent_id": "p1"},
            {"parent_id": "p2"},
        ],
    )
    parent = _FakeCollection(store={"p1": "PARENT ONE", "p2": "PARENT TWO"})
    mocker.patch.object(retriever_module, "get_child_collection", return_value=child)
    mocker.patch.object(retriever_module, "get_parent_collection", return_value=parent)

    # n_results clamps to child.count(); distinct parents returned in order.
    result = retrieve_guidelines("q", expanded=False)
    assert result == ["PARENT ONE", "PARENT TWO"]


def test_retrieve_falls_back_to_child_docs_without_parent_meta(mocker) -> None:
    child = _FakeCollection(count=2, docs=["c0", "c1"], metadatas=[{}, {}])
    mocker.patch.object(retriever_module, "get_child_collection", return_value=child)
    assert retrieve_guidelines("q") == ["c0", "c1"]


def test_retrieve_handles_errors(mocker) -> None:
    mocker.patch.object(retriever_module, "get_child_collection",
                        side_effect=RuntimeError("boom"))
    # Should swallow the error and return [].
    assert retrieve_guidelines("q") == []


def test_ingest_guidelines_routes_to_both_collections(mocker) -> None:
    parent_col = _FakeCollection()
    child_col = _FakeCollection()
    mocker.patch.object(retriever_module, "get_parent_collection",
                        return_value=parent_col)
    mocker.patch.object(retriever_module, "get_child_collection",
                        return_value=child_col)

    ingest_guidelines([
        {"text": "parent text", "id": "parent_doc_0", "parent_id": "parent_doc_0",
         "chunk_type": "parent", "doc_name": "doc"},
        {"text": "child text", "id": "child_doc_0_0", "parent_id": "parent_doc_0",
         "chunk_type": "child", "doc_name": "doc"},
    ])

    assert parent_col.upserted["ids"] == ["parent_doc_0"]
    assert parent_col.upserted["documents"] == ["parent text"]
    assert child_col.upserted["ids"] == ["child_doc_0_0"]
    # Children carry parent_id metadata so retrieval can resolve back to parent.
    assert child_col.upserted["metadatas"][0]["parent_id"] == "parent_doc_0"


def test_ingest_guidelines_empty_is_noop(mocker) -> None:
    parent_col = _FakeCollection()
    mocker.patch.object(retriever_module, "get_parent_collection",
                        return_value=parent_col)
    ingest_guidelines([])
    assert parent_col.upserted is None


def test_get_collection_count(mocker) -> None:
    mocker.patch.object(retriever_module, "get_parent_collection",
                        return_value=_FakeCollection(count=3))
    mocker.patch.object(retriever_module, "get_child_collection",
                        return_value=_FakeCollection(count=12))
    assert get_collection_count() == {"parent": 3, "child": 12}


def test_get_collection_count_error_returns_zero(mocker) -> None:
    mocker.patch.object(retriever_module, "get_parent_collection",
                        side_effect=RuntimeError("no db"))
    assert get_collection_count() == {"parent": 0, "child": 0}


# ---------------------------------------------------------------------------
# Chains (Groq mocked)
# ---------------------------------------------------------------------------
def test_generate_response_empty_context_refuses() -> None:
    assert generate_response("q", []) == INSUFFICIENT_CONTEXT
    assert generate_response("q", ["   "]) == INSUFFICIENT_CONTEXT


def test_generate_response_success(mocker) -> None:
    fake_chain = mocker.Mock()
    fake_chain.invoke.return_value = "  a grounded answer  "
    mocker.patch.object(chains_module, "_build_chain", return_value=fake_chain)

    out = generate_response("what is first-line therapy?", ["some guideline"])

    assert out == "a grounded answer"
    fake_chain.invoke.assert_called_once()


def test_generate_response_api_error(mocker) -> None:
    mocker.patch.object(chains_module, "_build_chain",
                        side_effect=RuntimeError("groq down"))
    out = generate_response("q", ["ctx"])
    assert out.startswith("ERROR:")


# ---------------------------------------------------------------------------
# Agent graph (all node functions exercised via run_agent)
# ---------------------------------------------------------------------------
_SUPPORTED = {
    "verdict": "SUPPORTED",
    "is_valid": True,
    "should_flag": False,
    "validation_confidence": 1.0,
}


def _records(*texts, year=2024, source="Test Guideline"):
    """Helper: build retrieve_with_metadata-style records (recent by default)."""
    return [
        {"text": t, "metadata": {"source": source, "publication_year": year,
                                 "doc_name": "doc", "chunk_type": "parent"}}
        for t in texts
    ]


def test_run_agent_high_confidence_outputs(mocker) -> None:
    mocker.patch.object(agent_module, "retrieve_with_metadata",
                        return_value=_records("Metformin is first-line therapy."))
    mocker.patch.object(agent_module, "generate_response",
                        return_value="Metformin is first-line therapy.")
    mocker.patch.object(agent_module, "score_confidence", return_value=0.95)
    mocker.patch.object(agent_module, "score_query_alignment", return_value=0.8)
    mocker.patch.object(agent_module, "cross_validate", return_value=_SUPPORTED)

    result = agent_module.run_agent("first-line therapy?")

    assert result["confidence"] == 0.95
    assert result["flagged"] is False
    assert result["retry_count"] == 0
    assert "Confidence: 95%" in result["response"]
    assert "Sources:" in result["response"]


def test_run_agent_flags_low_confidence(mocker) -> None:
    mocker.patch.object(agent_module, "retrieve_with_metadata",
                        return_value=_records("unrelated text"))
    mocker.patch.object(agent_module, "generate_response",
                        return_value="I'm not sure about this.")
    mocker.patch.object(agent_module, "score_confidence", return_value=0.40)
    mocker.patch.object(agent_module, "score_query_alignment", return_value=0.1)
    mocker.patch.object(agent_module, "cross_validate", return_value=_SUPPORTED)

    result = agent_module.run_agent("ambiguous?")

    assert result["flagged"] is True
    assert "FLAGGED FOR CLINICAL REVIEW" in result["response"]


def test_run_agent_self_corrects_then_outputs(mocker) -> None:
    mocker.patch.object(agent_module, "retrieve_with_metadata",
                        return_value=_records("some guideline text"))
    mocker.patch.object(agent_module, "generate_response",
                        return_value="a borderline then grounded answer")
    # First pass medium after partial-support penalty (0.90 - 0.15 = 0.75), second high.
    mocker.patch.object(agent_module, "score_confidence",
                        side_effect=[0.90, 0.90])
    mocker.patch.object(agent_module, "score_query_alignment", return_value=0.8)
    mocker.patch.object(agent_module, "cross_validate", side_effect=[
        {
            "verdict": "PARTIALLY_SUPPORTED",
            "is_valid": False,
            "should_flag": False,
            "validation_confidence": 0.6,
        },
        _SUPPORTED,
    ])

    result = agent_module.run_agent("borderline question?")

    assert result["retry_count"] == 1
    assert result["flagged"] is False
    assert result["confidence"] == 0.90


def test_run_agent_appends_messages(mocker) -> None:
    mocker.patch.object(agent_module, "retrieve_with_metadata",
                        return_value=_records("guideline"))
    mocker.patch.object(agent_module, "generate_response", return_value="the answer")
    mocker.patch.object(agent_module, "score_confidence", return_value=0.95)
    mocker.patch.object(agent_module, "cross_validate", return_value=_SUPPORTED)

    result = agent_module.run_agent("my question", [])

    msgs = result["messages"]
    assert msgs[-2] == {"role": "user", "content": "my question"}
    assert msgs[-1] == {"role": "assistant", "content": "the answer"}
    assert "conversation_id" in result


def test_run_agent_trims_history_to_six(mocker) -> None:
    mocker.patch.object(agent_module, "retrieve_with_metadata",
                        return_value=_records("guideline"))
    mocker.patch.object(agent_module, "generate_response", return_value="answer")
    mocker.patch.object(agent_module, "score_confidence", return_value=0.95)
    mocker.patch.object(agent_module, "cross_validate", return_value=_SUPPORTED)

    prior = [{"role": "user", "content": f"q{i}"} for i in range(10)]
    result = agent_module.run_agent("newest", prior)

    assert len(result["messages"]) <= agent_module.MAX_HISTORY_MESSAGES


def test_generate_response_includes_history(mocker) -> None:
    captured = {}

    def _fake_invoke(payload):
        captured.update(payload)
        return "ok"

    fake_chain = mocker.Mock()
    fake_chain.invoke.side_effect = _fake_invoke
    mocker.patch.object(chains_module, "_build_chain", return_value=fake_chain)

    history = [
        {"role": "user", "content": "what is first-line therapy?"},
        {"role": "assistant", "content": "Metformin."},
    ]
    generate_response("any contraindications?", ["ctx"], messages=history)

    block = captured["user_block"]
    assert "CONVERSATION HISTORY:" in block
    assert "Metformin." in block
    assert "any contraindications?" in block


def test_format_history_empty() -> None:
    assert chains_module._format_history([]) == ""


def test_run_agent_handles_exception(mocker) -> None:
    mocker.patch.object(agent_module, "retrieve_with_metadata",
                        side_effect=RuntimeError("kaboom"))
    # retrieve_node swallows the error -> docs empty -> INSUFFICIENT_CONTEXT
    # path; the run should still complete and return a dict.
    result = agent_module.run_agent("q")
    assert {"response", "confidence", "flagged", "retry_count", "messages"} <= set(
        result.keys()
    )


# ---------------------------------------------------------------------------
# Cross-validation (second Groq model mocked)
# ---------------------------------------------------------------------------
def test_parse_verdict_precedence() -> None:
    # PARTIALLY_SUPPORTED contains "SUPPORTED"; must not be misread.
    assert validator_module._parse_verdict("PARTIALLY_SUPPORTED") == \
        "PARTIALLY_SUPPORTED"
    assert validator_module._parse_verdict("SUPPORTED") == "SUPPORTED"
    assert validator_module._parse_verdict("CONTRADICTED") == "CONTRADICTED"
    assert validator_module._parse_verdict("garbage") == "ERROR"


@pytest.mark.parametrize("raw,verdict,is_valid,should_flag,conf", [
    ("SUPPORTED", "SUPPORTED", True, False, 1.0),
    ("PARTIALLY_SUPPORTED", "PARTIALLY_SUPPORTED", False, False, 0.6),
    ("CONTRADICTED", "CONTRADICTED", False, True, 0.0),
])
def test_cross_validate_verdicts(mocker, raw, verdict, is_valid, should_flag,
                                 conf) -> None:
    fake_chain = mocker.Mock()
    fake_chain.invoke.return_value = raw
    mocker.patch.object(validator_module, "_build_validator_chain",
                        return_value=fake_chain)

    result = cross_validate("an answer", ["a source document"], "q")

    assert result["verdict"] == verdict
    assert result["is_valid"] is is_valid
    assert result["should_flag"] is should_flag
    assert result["validation_confidence"] == conf


def test_cross_validate_empty_context_returns_error() -> None:
    result = cross_validate("an answer", [], "q")
    assert result["verdict"] == "ERROR"
    assert result["is_valid"] is False


def test_cross_validate_api_error(mocker) -> None:
    mocker.patch.object(validator_module, "_build_validator_chain",
                        side_effect=RuntimeError("groq down"))
    result = cross_validate("an answer", ["source"], "q")
    assert result["verdict"] == "ERROR"
    assert result["is_valid"] is False


# ---------------------------------------------------------------------------
# Ingest loaders
# ---------------------------------------------------------------------------
def test_load_txt_file(tmp_path) -> None:
    p = tmp_path / "guide.txt"
    p.write_text("Metformin is first-line therapy.", encoding="utf-8")
    assert "Metformin" in load_txt_file(str(p))


def test_sample_guideline_loads() -> None:
    sample = os.path.join("data", "guidelines", "sample_diabetes_guideline.txt")
    if os.path.exists(sample):
        text = load_txt_file(sample)
        assert "FICTIONAL" in text.upper()


def test_load_pdf_file_mocked(mocker) -> None:
    fake_page = mocker.Mock()
    fake_page.extract_text.return_value = "Metformin guideline text."
    fake_reader = mocker.Mock()
    fake_reader.is_encrypted = False
    fake_reader.pages = [fake_page, fake_page]
    mocker.patch.object(ingest_module, "PdfReader", return_value=fake_reader)

    text = load_pdf_file("anything.pdf")

    assert "Metformin guideline text." in text


def test_load_pdf_file_handles_failure(mocker) -> None:
    mocker.patch.object(ingest_module, "PdfReader",
                        side_effect=RuntimeError("corrupt pdf"))
    assert load_pdf_file("bad.pdf") == ""


def test_ingest_all_guidelines_orchestration(tmp_path, mocker) -> None:
    # Point the pipeline at a temp dir with one .txt guideline.
    (tmp_path / "g.txt").write_text(
        "Metformin is first-line therapy. " * 200, encoding="utf-8"
    )
    mocker.patch.object(ingest_module, "GUIDELINES_DIR", str(tmp_path))
    spy = mocker.patch.object(ingest_module, "ingest_guidelines")

    ingest_module.ingest_all_guidelines()

    spy.assert_called_once()
    (items,) = spy.call_args.args
    chunk_types = {it["chunk_type"] for it in items}
    assert chunk_types == {"parent", "child"}
    # Parent/child IDs follow the documented naming scheme.
    assert any(it["id"].startswith("parent_g_") for it in items)
    assert any(it["id"].startswith("child_g_") for it in items)
    # Every child links back to a real parent id.
    parent_ids = {it["id"] for it in items if it["chunk_type"] == "parent"}
    assert all(
        it["parent_id"] in parent_ids
        for it in items if it["chunk_type"] == "child"
    )


def test_ingest_all_guidelines_missing_dir(mocker) -> None:
    mocker.patch.object(ingest_module, "GUIDELINES_DIR", "no_such_dir_xyz")
    spy = mocker.patch.object(ingest_module, "ingest_guidelines")
    ingest_module.ingest_all_guidelines()
    spy.assert_not_called()


# ---------------------------------------------------------------------------
# Recency scoring
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("year,expected", [
    (recency.CURRENT_YEAR, 1.0),        # 0 years -> very recent
    (recency.CURRENT_YEAR - 1, 1.0),    # 1 year
    (recency.CURRENT_YEAR - 3, 0.85),   # recent
    (recency.CURRENT_YEAR - 5, 0.65),   # acceptable
    (recency.CURRENT_YEAR - 8, 0.40),   # aging
    (recency.CURRENT_YEAR - 20, 0.20),  # outdated
    (0, 0.20),                          # unknown -> outdated
])
def test_calculate_recency_score_bands(year, expected) -> None:
    assert recency.calculate_recency_score(year) == expected


def test_get_oldest_source_year() -> None:
    meta = [
        {"publication_year": 2023},
        {"publication_year": 2015},
        {"publication_year": 2020},
    ]
    assert recency.get_oldest_source_year(meta) == 2015
    assert recency.get_oldest_source_year([]) is None
    assert recency.get_oldest_source_year([{"publication_year": "n/a"}]) is None


def test_should_warn_outdated() -> None:
    recent = [{"publication_year": recency.CURRENT_YEAR - 2}]
    old = [{"publication_year": recency.CURRENT_YEAR - 6}]
    assert recency.should_warn_outdated(recent) is False
    assert recency.should_warn_outdated(old) is True
    assert recency.should_warn_outdated([]) is False


def test_recency_label() -> None:
    assert recency.recency_label(recency.CURRENT_YEAR - 1)[0] == "✅"
    assert recency.recency_label(recency.CURRENT_YEAR - 7)[1] == "Aging"
    assert recency.recency_label(recency.CURRENT_YEAR - 12)[1] == "Outdated"
    assert recency.recency_label(0)[1] == "Unknown date"


# ---------------------------------------------------------------------------
# Agent reflect_node — temporal recency gate
# ---------------------------------------------------------------------------
def test_reflect_node_outdated_warns_and_penalizes(mocker) -> None:
    mocker.patch.object(agent_module, "score_confidence", return_value=0.95)
    mocker.patch.object(agent_module, "score_query_alignment", return_value=0.8)
    mocker.patch.object(agent_module, "cross_validate", return_value=_SUPPORTED)

    state = {
        "query": "q",
        "response": "Some grounded answer.",
        "retrieved_docs": ["doc"],
        "retrieved_metadata": [{"publication_year": recency.CURRENT_YEAR - 10}],
        "retry_count": 0,
    }
    new_state = agent_module.reflect_node(state)

    # 0.95 - 0.10 outdated penalty = 0.85.
    assert abs(new_state["confidence"] - 0.85) < 1e-6
    assert "outdated" in new_state["response"].lower()


def test_reflect_node_recent_no_warning(mocker) -> None:
    mocker.patch.object(agent_module, "score_confidence", return_value=0.95)
    mocker.patch.object(agent_module, "score_query_alignment", return_value=0.8)
    mocker.patch.object(agent_module, "cross_validate", return_value=_SUPPORTED)

    state = {
        "query": "q",
        "response": "Some grounded answer.",
        "retrieved_docs": ["doc"],
        "retrieved_metadata": [{"publication_year": recency.CURRENT_YEAR - 1}],
        "retry_count": 0,
    }
    new_state = agent_module.reflect_node(state)

    assert new_state["confidence"] == 0.95
    assert "outdated" not in new_state["response"].lower()


# ---------------------------------------------------------------------------
# PubMed fetcher (network mocked)
# ---------------------------------------------------------------------------
_PUBMED_XML = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>38123456</PMID>
      <Article>
        <Journal><Title>J Clin Test</Title>
          <JournalIssue><PubDate><Year>2023</Year><Month>Jun</Month>
          <Day>15</Day></PubDate></JournalIssue>
        </Journal>
        <ArticleTitle>Metformin in type 2 diabetes</ArticleTitle>
        <Abstract><AbstractText>Metformin remains first-line.</AbstractText></Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


def test_fetch_pubmed_abstracts_parses_fields(mocker) -> None:
    def _fake_http_get(url, params):
        if "esearch" in url:
            return b'{"esearchresult": {"idlist": ["38123456"]}}'
        return _PUBMED_XML

    mocker.patch.object(pubmed_module, "_http_get", side_effect=_fake_http_get)

    records = pubmed_module.fetch_pubmed_abstracts("metformin diabetes")

    assert len(records) == 1
    rec = records[0]
    assert rec["pmid"] == "38123456"
    assert rec["publication_year"] == 2023
    assert rec["publication_date"] == "2023-06-15"
    assert rec["is_recent"] is True
    assert "Metformin" in rec["abstract"]
    assert rec["source"] == "PubMed:38123456"


def test_fetch_pubmed_abstracts_empty_query() -> None:
    assert pubmed_module.fetch_pubmed_abstracts("") == []


def test_fetch_pubmed_abstracts_network_error(mocker) -> None:
    mocker.patch.object(pubmed_module, "_http_get",
                        side_effect=RuntimeError("network down"))
    assert pubmed_module.fetch_pubmed_abstracts("anything") == []


# ---------------------------------------------------------------------------
# Feedback logger (reward-model dataset collection)
# ---------------------------------------------------------------------------
@pytest.fixture()
def feedback_path(tmp_path, mocker):
    """Redirect the feedback CSV to a temp file for isolated tests."""
    path = tmp_path / "confidence_log.csv"
    mocker.patch.object(feedback_module, "FEEDBACK_FILE", str(path))
    return path


def _sample_result():
    return {
        "response": "Metformin is first-line therapy for type 2 diabetes." * 5,
        "confidence": 0.91,
        "flagged": False,
        "retry_count": 1,
        "conversation_id": "conv-1",
        "validation_verdict": "SUPPORTED",
        "sources": [{"source": "ADA"}, {"source": "PubMed"}],
        "query": "first-line therapy?",
    }


def test_log_interaction_creates_file_with_header(feedback_path) -> None:
    ts = feedback_module.log_interaction(_sample_result(), 1234)

    assert ts  # row key returned
    assert feedback_path.exists()
    rows = feedback_module._read_all_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["timestamp"] == ts
    assert row["conversation_id"] == "conv-1"
    assert len(row["response_preview"]) <= 100
    assert row["confidence_score"] == "0.91"
    assert row["retrieved_doc_count"] == "2"
    assert row["response_time_ms"] == "1234"
    assert row["human_rating"] == ""  # unrated until feedback


def test_log_human_feedback_updates_row(feedback_path) -> None:
    ts = feedback_module.log_interaction(_sample_result(), 100)

    assert feedback_module.log_human_feedback(ts, 5) is True
    rows = feedback_module._read_all_rows()
    assert rows[0]["human_rating"] == "5"


def test_log_human_feedback_clamps_and_missing(feedback_path) -> None:
    ts = feedback_module.log_interaction(_sample_result(), 100)

    # Out-of-range rating is clamped to 1..5.
    assert feedback_module.log_human_feedback(ts, 9) is True
    assert feedback_module._read_all_rows()[0]["human_rating"] == "5"

    # Unknown timestamp -> no update.
    assert feedback_module.log_human_feedback("nope", 4) is False


def test_get_feedback_stats(feedback_path) -> None:
    # Empty before any logging.
    empty = feedback_module.get_feedback_stats()
    assert empty["total_interactions"] == 0

    r1 = _sample_result()
    r2 = {**_sample_result(), "confidence": 0.5, "flagged": True}
    ts1 = feedback_module.log_interaction(r1, 100)
    feedback_module.log_interaction(r2, 200)
    feedback_module.log_human_feedback(ts1, 4)

    stats = feedback_module.get_feedback_stats()
    assert stats["total_interactions"] == 2
    assert abs(stats["avg_confidence"] - 0.705) < 1e-6
    assert abs(stats["flag_rate"] - 0.5) < 1e-6
    assert stats["total_rated"] == 1
    assert stats["avg_human_rating"] == 4.0


def test_extract_clinical_answer_prefers_raw_message() -> None:
    from ui.theme import extract_clinical_answer

    formatted = (
        "⚠️ FLAGGED FOR CLINICAL REVIEW\n\n"
        "Stale formatted block\n---\nConfidence: 42%"
    )
    messages = [
        {"role": "user", "content": "question?"},
        {"role": "assistant", "content": "Metformin is first-line therapy."},
    ]
    assert extract_clinical_answer(formatted, messages) == (
        "Metformin is first-line therapy."
    )


def test_extract_clinical_answer_strips_metadata_and_indent() -> None:
    from ui.theme import extract_clinical_answer

    formatted = (
        "⚠️ FLAGGED FOR CLINICAL REVIEW\n\n"
        "    Indented clinical guidance.\n"
        "---\nConfidence: 10%"
    )
    assert extract_clinical_answer(formatted, None) == "Indented clinical guidance."


def test_flag_banner_accurate_when_contradicted_at_high_confidence() -> None:
    from ui.theme import format_review_banner

    title, body = format_review_banner(
        flagged=True,
        confidence=0.99,
        verdict="CONTRADICTED",
        flag_reason="contradicted",
        retry_count=0,
        high=0.85,
        medium=0.75,
    )
    assert title == "Flagged for clinical review"
    assert "99%" in body
    assert "contradicted" in body.lower()
    assert "not sufficiently grounded" not in body.lower()


def test_html_removes_nested_indentation() -> None:
    from ui.theme import _html

    rendered = _html(
        """
        <div class="outer">
            <div class="inner">72%</div>
        </div>
        """
    )
    for line in rendered.splitlines():
        assert not line.startswith("    "), line
    assert '<div class="inner">72%</div>' in rendered
