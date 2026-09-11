"""Sync eval_results.json metrics into README and landing page.

Run after:
    python scripts/run_eval.py

Usage:
    python scripts/sync_eval_metrics.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "eval" / "eval_results.json"
README = ROOT / "README.md"
LANDING_METRICS = ROOT / "landing" / "lib" / "metrics.ts"


def _load_summary() -> dict:
    with open(RESULTS, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["summary"]


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def update_readme(summary: dict) -> None:
    text = README.read_text(encoding="utf-8")
    replacements = [
        (r"\| Keyword match rate\s+\| _run the eval to populate_\s+\|",
         f"| Keyword match rate                  | {_fmt_pct(summary['keyword_match_rate']):<34} |"),
        (r"\| Average confidence\s+\| _run the eval to populate_\s+\|",
         f"| Average confidence                  | {_fmt_pct(summary['average_confidence']):<34} |"),
        (r"\| Flag rate\s+\| _run the eval to populate_\s+\|",
         f"| Flag rate                           | {_fmt_pct(summary['flag_rate']):<34} |"),
        (r"\| Average response time\s+\| _run the eval to populate_\s+\|",
         f"| Average response time               | {summary['avg_response_time_ms']:.0f}ms{' ' * (34 - len(f'{summary['avg_response_time_ms']:.0f}ms'))} |"),
        (r"\| Two-model validation agreement\s+\| _run the eval to populate_\s+\|",
         f"| Two-model validation agreement      | {_fmt_pct(summary['validation_agreement_rate']):<34} |"),
    ]
    for pattern, repl in replacements:
        text, n = re.subn(pattern, repl, text)
        if n == 0:
            print(f"Warning: pattern not found in README: {pattern[:40]}...")
    README.write_text(text, encoding="utf-8")
    print(f"Updated {README}")


def update_landing(summary: dict) -> None:
    kw = int(round(summary["keyword_match_rate"] * 100))
    conf = int(round(summary["average_confidence"] * 100))
    agree = int(round(summary["validation_agreement_rate"] * 100))
    block = f"""/** Eval metrics — synced from data/eval/eval_results.json via scripts/sync_eval_metrics.py */

export const METRICS = {{
  questions: {summary['questions_evaluated']},
  keywordMatch: "{_fmt_pct(summary['keyword_match_rate'])}",
  keywordMatchNum: {kw},
  avgConfidence: "{_fmt_pct(summary['average_confidence'])}",
  avgConfidenceNum: {conf},
  flagRate: "{_fmt_pct(summary['flag_rate'])}",
  avgLatency: "{summary['avg_response_time_ms']:.0f}ms",
  validationAgreement: "{_fmt_pct(summary['validation_agreement_rate'])}",
  validationAgreementNum: {agree},
  note: "Measured by scripts/run_eval.py on {summary.get('generated_at', 'eval run')[:10]} — diabetes-only corpus; unsupported categories correctly flagged.",
}} as const;
"""
    LANDING_METRICS.write_text(block, encoding="utf-8")
    print(f"Updated {LANDING_METRICS}")


def main() -> None:
    if not RESULTS.exists():
        raise SystemExit(f"No results at {RESULTS}. Run: python scripts/run_eval.py")
    summary = _load_summary()
    update_readme(summary)
    update_landing(summary)
    print("\n=== METRICS SYNCED ===")
    print(f"Keyword match rate: {_fmt_pct(summary['keyword_match_rate'])}")
    print(f"Average confidence: {_fmt_pct(summary['average_confidence'])}")
    print(f"Flag rate: {_fmt_pct(summary['flag_rate'])}")
    print(f"Avg response time: {summary['avg_response_time_ms']:.0f}ms")
    print(f"Validation agreement: {_fmt_pct(summary['validation_agreement_rate'])}")


if __name__ == "__main__":
    main()
