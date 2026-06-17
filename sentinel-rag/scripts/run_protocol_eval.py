"""Quick protocol-accuracy check using the full eval question set."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import config  # noqa: E402
from src.agent import run_agent  # noqa: E402
from src.reflection import has_corpus_anchor  # noqa: E402
from src.retriever import retrieve_with_metadata  # noqa: E402

KEYWORD_MATCH_THRESHOLD = 0.6
QUESTIONS_PATH = os.path.join("data", "eval", "eval_questions.json")


def main() -> None:
    with open(QUESTIONS_PATH, encoding="utf-8") as fh:
        questions = json.load(fh)

    in_corpus_cats = set(config.CORPUS_CATEGORIES)
    correct = 0
    failures = []

    for q in questions:
        keywords = q.get("expected_answer_keywords", [])
        result = run_agent(q["question"])

        answer = ""
        for msg in reversed(result.get("messages", [])):
            if msg.get("role") == "assistant":
                answer = msg.get("content", "")
                break
        if not answer:
            answer = result.get("response", "")

        found = [kw for kw in keywords if kw.lower() in answer.lower()]
        hit_rate = (len(found) / len(keywords)) if keywords else 0.0
        matched = hit_rate >= KEYWORD_MATCH_THRESHOLD

        docs = [r["text"] for r in retrieve_with_metadata(q["question"])]
        in_scope = (
            q.get("category") in in_corpus_cats
            or has_corpus_anchor(q["question"], docs)
        )
        flagged = bool(result.get("flagged"))

        ok = (in_scope and matched and not flagged) or (not in_scope and flagged)
        correct += int(ok)
        if not ok:
            failures.append(
                {
                    "id": q["id"],
                    "category": q.get("category"),
                    "in_scope": in_scope,
                    "matched": matched,
                    "flagged": flagged,
                    "confidence": result.get("confidence"),
                    "verdict": result.get("validation_verdict"),
                }
            )

    accuracy = correct / len(questions) if questions else 0.0
    print(f"\nProtocol accuracy: {correct}/{len(questions)} = {accuracy * 100:.1f}%")
    print(f"Target: {config.PROTOCOL_ACCURACY_TARGET * 100:.0f}%")
    if failures:
        print("\nFailures:")
        for row in failures:
            print(row)


if __name__ == "__main__":
    main()
