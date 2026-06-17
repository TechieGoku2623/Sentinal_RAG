"""Shared text helpers for API and UI (no Streamlit dependency)."""

from __future__ import annotations

import textwrap


def normalize_prose(text: str) -> str:
    """Prepare assistant text for markdown (avoid accidental code blocks)."""
    cleaned = textwrap.dedent(text or "").strip()
    if not cleaned:
        return "No response produced."
    return "\n".join(
        line[4:] if line.startswith("    ") and line.strip() else line
        for line in cleaned.splitlines()
    )


def format_review_banner(
    flagged: bool,
    confidence: float,
    verdict: str,
    flag_reason: str,
    retry_count: int,
    high: float,
    medium: float,
) -> tuple[str, str]:
    """Return (title, body) for the post-validation status banner."""
    pct = min(max(confidence, 0.0), 1.0)
    pct_str = f"{pct:.0%}"
    high_str = f"{high:.0%}"
    medium_str = f"{medium:.0%}"
    attempts = retry_count + 1

    if flagged:
        if flag_reason == "contradicted" or verdict == "CONTRADICTED":
            return (
                "Flagged for clinical review",
                f"Cross-validation **contradicted** this draft (grounding score {pct_str}, "
                f"verdict: Contradicted). The lexical score alone is not sufficient — "
                "do not act without verification by a qualified clinician.",
            )
        if flag_reason == "retries_exhausted":
            return (
                "Flagged for clinical review",
                f"Grounding did not reach the {high_str} release threshold after "
                f"{attempts} retrieval attempt(s) (score {pct_str}). "
                "Verify against source guidelines before clinical use.",
            )
        if flag_reason == "error":
            return (
                "Flagged for clinical review",
                "The validation pipeline encountered an error. Do not use this output — "
                "review manually or retry the query.",
            )
        if flag_reason == "out_of_scope":
            return (
                "Flagged for clinical review",
                "This question appears **outside the indexed guideline corpus** "
                f"(query–source alignment below {medium:.0%}). Do not use this answer — "
                "ingest relevant protocols or verify manually with current guidelines.",
            )
        if flag_reason == "insufficient_context":
            return (
                "Flagged for clinical review",
                "No relevant guideline context was retrieved for this question. "
                "Upload or ingest the appropriate protocol before clinical use.",
            )
        if pct >= high:
            return (
                "Flagged for clinical review",
                f"Grounding score is {pct_str}, but the safety pipeline escalated this "
                f"response (reason: {flag_reason or 'policy'}). Verify before clinical use.",
            )
        return (
            "Flagged for clinical review",
            f"Grounding confidence {pct_str} is below the {medium_str} safety threshold. "
            "Do not act without verification by a qualified clinician.",
        )

    if verdict == "PARTIALLY_SUPPORTED":
        return (
            "Moderate confidence",
            "Cross-validation found **partial support** — review source citations "
            "before relying on this response.",
        )
    if pct >= high:
        return (
            "High confidence",
            "Answer is well grounded in the retrieved guideline passages.",
        )
    if pct >= medium:
        return (
            "Moderate confidence",
            "Review source citations before relying on this response.",
        )
    return (
        "Low confidence",
        "Response is weakly supported by the available guidelines.",
    )


def extract_clinical_answer(formatted: str, messages: list | None = None) -> str:
    """Return the raw clinical answer without metadata banners or footers."""
    if messages:
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and str(msg.get("content", "")).strip():
                return normalize_prose(str(msg["content"]))

    text = (formatted or "").strip()
    if not text:
        return "No response produced."

    if "\n---\n" in text:
        text = text.split("\n---\n", 1)[0].strip()

    if text.startswith("⚠️ FLAGGED FOR CLINICAL REVIEW"):
        parts = text.split("\n\n", 1)
        text = parts[1].strip() if len(parts) > 1 else ""

    return normalize_prose(text)
