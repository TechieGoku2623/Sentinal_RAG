"""Generate demo output for Sentinel-RAG.

Runs a fixed set of sample clinical queries through the full self-reflective
agent and prints each result with its confidence score, retry count, and
routing outcome. Intended to produce the "Sample Output" shown in the README
and to give a quick, concrete demonstration of the agent's behavior.

Prerequisites:
    1. Install dependencies:      pip install -r requirements.txt
    2. Add your keys to .env:     GROQ_API_KEY=...   (LangSmith optional)
    3. Ingest the sample data:    python -m src.ingest

Then run:
    python scripts/generate_demo_data.py

The 5 sample queries are chosen to exercise all three routing outcomes:
  * high-confidence answers that are returned directly,
  * a borderline answer that triggers a self-correcting re-query, and
  * an out-of-scope question that gets flagged for clinical review.
"""

from __future__ import annotations

import os
import sys

# Allow running as `python scripts/generate_demo_data.py` from the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import run_agent  # noqa: E402  (after sys.path tweak)

SAMPLE_QUERIES = [
    "What is the first-line treatment for Type 2 diabetes?",
    "What are metformin contraindications?",
    "What is the HbA1c target for elderly patients?",
    "Can metformin be used with kidney disease?",
    "What happens if a patient misses a dose?",
]

LINE = "=" * 70
THIN = "-" * 70


def _status(confidence: float, flagged: bool, retry_count: int) -> str:
    if flagged:
        return "FLAGGED FOR REVIEW"
    if retry_count > 0:
        return f"RETURNED (after {retry_count} re-query)"
    return "RETURNED"


def main() -> None:
    print(LINE)
    print(" SENTINEL-RAG — DEMO RUN")
    print(" Self-reflective clinical protocol agent")
    print(LINE)

    flagged_count = 0
    requery_count = 0

    for idx, query in enumerate(SAMPLE_QUERIES, start=1):
        result = run_agent(query)

        confidence = float(result.get("confidence", 0.0))
        flagged = bool(result.get("flagged", False))
        retry_count = int(result.get("retry_count", 0))
        response = result.get("response", "")

        flagged_count += int(flagged)
        requery_count += int(retry_count > 0)

        print(f"\n[{idx}/{len(SAMPLE_QUERIES)}] Q: {query}")
        print(THIN)
        print(f"Confidence: {confidence:5.0%}  |  Retries: {retry_count}  |  "
              f"Status: {_status(confidence, flagged, retry_count)}")
        print(THIN)
        print(response)

    print("\n" + LINE)
    print(f" SUMMARY: {len(SAMPLE_QUERIES)} queries  |  "
          f"{requery_count} self-corrected  |  "
          f"{flagged_count} flagged for review")
    print(LINE)


if __name__ == "__main__":
    main()
