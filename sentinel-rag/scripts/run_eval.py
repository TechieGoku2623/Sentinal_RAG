"""Offline evaluation harness for Sentinel-RAG.

Runs the 50-question evaluation dataset through the full agent and reports
aggregate metrics: keyword match rate, average confidence, flag rate, average
response time, and two-model validation agreement. Results are saved to
data/eval/eval_results.json and a summary is printed.

Prerequisites:
    1. pip install -r requirements.txt
    2. Add GROQ_API_KEY to .env
    3. Ingest guideline documents:  python -m src.ingest
       (For meaningful, non-flagged results, the knowledge base must contain
        guidelines that actually cover the eval categories — diabetes, harm
        reduction, hypertension, drug interactions, and general protocols.)

Run:
    python scripts/run_eval.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import run_agent  # noqa: E402
from src import config  # noqa: E402
from src.reflection import has_corpus_anchor  # noqa: E402
from src.retriever import retrieve_with_metadata  # noqa: E402

logging.basicConfig(level=logging.WARNING)

EVAL_DIR = os.path.join("data", "eval")
QUESTIONS_PATH = os.path.join(EVAL_DIR, "eval_questions.json")
RESULTS_PATH = os.path.join(EVAL_DIR, "eval_results.json")

# A question "matches" when at least this fraction of its keywords appear.
KEYWORD_MATCH_THRESHOLD = 0.6


def _load_questions() -> List[dict]:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _raw_answer(result: dict) -> str:
    """Return the model's raw answer (preferred for keyword scoring).

    The formatted ``response`` field includes a Sources preview that echoes the
    guideline text, which would inflate keyword matches. The last assistant
    message holds the clean answer, so we use that when available.
    """
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return msg.get("content", "")
    return result.get("response", "")


def _keywords_found(answer: str, keywords: List[str]) -> List[str]:
    low = answer.lower()
    return [kw for kw in keywords if kw.lower() in low]


def evaluate_sentinel_rag() -> dict:
    """Run the full evaluation and return the results dict (also saved to disk)."""
    questions = _load_questions()
    records = []

    total_keywords = 0
    total_found = 0

    for q in questions:
        keywords = q.get("expected_answer_keywords", [])

        start = time.perf_counter()
        try:
            result = run_agent(q["question"])
        except Exception as exc:  # noqa: BLE001 - record and continue
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            records.append({
                "id": q["id"], "category": q.get("category"),
                "difficulty": q.get("difficulty"), "error": str(exc),
                "confidence": 0.0, "flagged": True,
                "validation_verdict": "ERROR", "keywords_found": [],
                "keywords_expected": len(keywords),
                "keyword_hit_rate": 0.0, "matched": False,
                "response_time_ms": round(elapsed_ms, 1),
            })
            continue
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        answer = _raw_answer(result)
        found = _keywords_found(answer, keywords)
        hit_rate = (len(found) / len(keywords)) if keywords else 0.0
        retrieved = retrieve_with_metadata(q["question"])
        retrieved_docs = [r["text"] for r in retrieved]
        in_scope = (
            q.get("category") in set(config.CORPUS_CATEGORIES)
            or has_corpus_anchor(q["question"], retrieved_docs)
        )

        total_keywords += len(keywords)
        total_found += len(found)

        records.append({
            "id": q["id"],
            "category": q.get("category"),
            "difficulty": q.get("difficulty"),
            "question": q["question"],
            "in_corpus_scope": in_scope,
            "confidence": round(float(result.get("confidence", 0.0)), 4),
            "flagged": bool(result.get("flagged", False)),
            "validation_verdict": result.get("validation_verdict", "ERROR"),
            "keywords_found": found,
            "keywords_expected": len(keywords),
            "keyword_hit_rate": round(hit_rate, 4),
            "matched": hit_rate >= KEYWORD_MATCH_THRESHOLD,
            "response_time_ms": round(elapsed_ms, 1),
            "answer": answer,
        })

    n = len(records)
    keyword_match_rate = (total_found / total_keywords) if total_keywords else 0.0
    avg_confidence = sum(r["confidence"] for r in records) / n if n else 0.0
    flag_rate = sum(1 for r in records if r["flagged"]) / n if n else 0.0
    avg_time_ms = sum(r["response_time_ms"] for r in records) / n if n else 0.0
    # The two gates "agree" when the validator's SUPPORTED verdict lines up with
    # the answer NOT being flagged (and vice versa).
    agreement = sum(
        1 for r in records
        if (r["validation_verdict"] == "SUPPORTED") == (not r["flagged"])
    ) / n if n else 0.0

    in_corpus = set(config.CORPUS_CATEGORIES)
    protocol_correct = 0
    for r in records:
        if r.get("in_corpus_scope"):
            if r.get("matched") and not r.get("flagged"):
                protocol_correct += 1
        elif r.get("flagged"):
            protocol_correct += 1
    protocol_accuracy = protocol_correct / n if n else 0.0

    summary = {
        "questions_evaluated": n,
        "keyword_match_rate": round(keyword_match_rate, 4),
        "average_confidence": round(avg_confidence, 4),
        "flag_rate": round(flag_rate, 4),
        "avg_response_time_ms": round(avg_time_ms, 1),
        "validation_agreement_rate": round(agreement, 4),
        "protocol_accuracy": round(protocol_accuracy, 4),
        "protocol_accuracy_target": config.PROTOCOL_ACCURACY_TARGET,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    output = {"summary": summary, "results": records}

    os.makedirs(EVAL_DIR, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)

    _print_report(summary)
    return output


def _print_report(s: dict) -> None:
    print("\n=== SENTINEL-RAG EVALUATION REPORT ===")
    print(f"Questions evaluated: {s['questions_evaluated']}")
    print(f"Keyword match rate: {s['keyword_match_rate'] * 100:.0f}%")
    print(f"Average confidence: {s['average_confidence'] * 100:.0f}%")
    print(f"Flag rate: {s['flag_rate'] * 100:.0f}%")
    print(f"Avg response time: {s['avg_response_time_ms']:.0f}ms")
    print(f"Validation agreement: {s['validation_agreement_rate'] * 100:.0f}%")
    print(f"Protocol accuracy: {s['protocol_accuracy'] * 100:.1f}% "
          f"(target {s['protocol_accuracy_target'] * 100:.0f}%)")
    print("======================================")
    print(f"\nDetailed per-question results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    evaluate_sentinel_rag()
