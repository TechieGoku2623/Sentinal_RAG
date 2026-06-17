"""Self-reflection / confidence scoring for Sentinel-RAG.

==============================================================================
THE CORE INNOVATION: WHY SELF-REFLECTION MATTERS IN CLINICAL AI
==============================================================================
A standard RAG pipeline retrieves documents, stuffs them into a prompt, and
returns whatever the LLM generates. In most domains a confidently-wrong answer
is an annoyance. In a *clinical* setting it is a safety event: a fluent,
authoritative-sounding hallucination about a drug dose, contraindication, or
protocol step can directly cause patient harm.

Sentinel-RAG's defense is to never trust a single forward pass. After the LLM
drafts an answer, this module scores how well that answer is actually grounded
in the retrieved guideline text. The agent (LangGraph state machine) uses that
score to decide whether to:

  * return the answer (high confidence),
  * re-retrieve with a wider net and try again (medium confidence), or
  * refuse / escalate to a human and explicitly flag low confidence.

Crucially, the scorer is *deterministic and transparent* — it is NOT another
LLM judging the first LLM. Using a second model as the only safety check would
just stack one hallucination risk on top of another and would be impossible to
audit. Instead we use explicit, inspectable heuristics so that every confidence
score can be explained ("this answer scored low because it shares almost no
vocabulary with the retrieved guideline, and it contains the phrase 'I'm not
sure'"). In a regulated, high-stakes domain, explainability of the safety layer
is as important as the safety layer itself.

The final confidence is a weighted blend of four factors. The weights encode a
clinical-safety prior: *grounding in the source* matters most, hedging language
matters next, and surface features (length, contradiction checks) act as
secondary guards.

    Factor 1 — Context Coverage ....... 0.40  (is the answer grounded?)
    Factor 2 — No Uncertainty Signals . 0.30  (did the model hedge?)
    Factor 3 — Specificity ............ 0.20  (is it substantive, not vague?)
    Factor 4 — No Contradiction ....... 0.10  (does it fight the source?)
                                        -----
                                        1.00
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

from src import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Factor weights — tunable safety policy.
# These are intentionally module-level constants so the trade-offs are visible
# and reviewable in one place (e.g. for a clinical safety sign-off).
# ---------------------------------------------------------------------------
WEIGHT_COVERAGE = 0.40
WEIGHT_NO_UNCERTAINTY = 0.30
WEIGHT_SPECIFICITY = 0.20
WEIGHT_NO_CONTRADICTION = 0.10

# Number of words that counts as a "fully specific" answer for Factor 3.
SPECIFICITY_TARGET_WORDS = 30

# Maximum number of key terms we extract from a body of text.
MAX_KEY_TERMS = 30

# Hedging / low-confidence phrases. If the model itself signals doubt, we must
# NOT report high confidence — surfacing the model's own uncertainty to the
# clinician is the entire point. These are matched case-insensitively as
# substrings.
UNCERTAINTY_PHRASES = [
    "i don't know",
    "i dont know",
    "i'm not sure",
    "im not sure",
    "insufficient context",
    "cannot determine",
    "unclear",
    "not mentioned",
    "not found",
    "no information",
]

# A compact English stop-word list. Kept inline (no nltk download) so the
# scorer has zero network dependencies — important for the on-prem/offline
# privacy posture described in retriever.py.
# Extra generic clinical phrasing excluded from query–corpus alignment scoring.
ALIGNMENT_GENERIC_TERMS = {
    "patient", "patients", "treatment", "therapy", "recommended", "dose", "drug",
    "medication", "give", "example", "common", "side", "effect", "risk",
    "combining", "target", "adults", "general", "blood", "pressure", "first",
    "line", "name", "help", "lower", "changes", "lifestyle", "associated",
    "affect", "defines", "managed", "held", "around", "procedures", "perform",
    "assessed", "frequently", "often", "measured", "starting", "maximum",
    "daily", "alongside", "appropriate", "multiple", "older", "pregnant",
    "reverses", "routes", "administered", "dangerous", "avoided", "certain",
    "classes", "supplements", "recognition", "stable", "contraindicated",
    "pregnancy", "blocker", "blockers", "inhibitors", "inhibitor", "beta",
    "ace", "potassium", "lab", "value", "monitored", "monitor", "safety",
    "taking", "patients",
}

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "having", "do", "does", "did", "doing", "of", "this",
    "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
    "them", "his", "her", "its", "our", "their", "as", "so", "than", "too",
    "very", "can", "will", "just", "should", "now", "also", "may", "might",
    "such", "no", "not", "only", "own", "same", "what", "which", "who",
    "whom", "how", "why", "where", "there", "here", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "use", "used", "using",
}


# ---------------------------------------------------------------------------
# Key term extraction
# ---------------------------------------------------------------------------
def extract_key_terms(text: str) -> List[str]:
    """Extract up to ``MAX_KEY_TERMS`` meaningful terms from ``text``.

    Strategy:
      1. Lowercase and tokenize on word characters (drops punctuation/numbers
         noise while keeping alphanumerics).
      2. Drop stop words and very short tokens (< 3 chars), which are almost
         never clinically meaningful ("of", "to", "mg" is borderline but the
         length filter keeps signal high).
      3. Rank by frequency (more-repeated terms are more central to the text)
         while preserving first-seen order for ties — deterministic output.

    Returns the top 30 terms. Determinism matters: the same text must always
    yield the same key terms so confidence scores are reproducible/auditable.
    """
    if not text:
        return []

    # \b\w+\b keeps words; we lowercase for case-insensitive matching.
    tokens = re.findall(r"\b\w+\b", text.lower())

    counts: dict[str, int] = {}
    order: dict[str, int] = {}
    for idx, tok in enumerate(tokens):
        if tok in STOP_WORDS:
            continue
        if len(tok) < 3:
            continue
        # Skip pure numbers — a bare "10" is not a useful grounding term, and
        # numeric matching is handled implicitly when it's part of a word.
        if tok.isdigit():
            continue
        counts[tok] = counts.get(tok, 0) + 1
        if tok not in order:
            order[tok] = idx

    # Sort by frequency desc, then by first appearance asc (stable, no RNG).
    ranked = sorted(counts.keys(), key=lambda t: (-counts[t], order[t]))
    return ranked[:MAX_KEY_TERMS]


# ---------------------------------------------------------------------------
# Individual factor scorers (each returns a value in [0.0, 1.0])
# ---------------------------------------------------------------------------
def _score_context_coverage(response: str, doc_terms: List[str]) -> float:
    """Factor 1 (0.40): how much of the retrieved knowledge the answer uses.

    Clinical-safety reasoning:
        A grounded answer should *reuse the vocabulary of the source*. If the
        retrieved guideline talks about "anticoagulation", "INR", and
        "warfarin" but the answer shares almost none of those terms, the answer
        is probably drawing on the model's parametric memory rather than the
        approved protocol — exactly the hallucination mode we must catch. This
        is the single most important signal, hence the highest weight (0.40).

    Score = (# of doc key terms that appear in the response) / (total doc key
    terms), capped at 1.0. If there are no doc terms (empty retrieval), there is
    nothing to be grounded in, so coverage is 0.0.
    """
    if not doc_terms:
        return 0.0

    response_lower = response.lower()
    matched = sum(1 for term in doc_terms if term in response_lower)
    return min(matched / len(doc_terms), 1.0)


def _score_no_uncertainty(response: str) -> float:
    """Factor 2 (0.30): penalize the model's own hedging language.

    Clinical-safety reasoning:
        If the model writes "I'm not sure" or "this is not mentioned in the
        provided context", that is a gift — it is telling us it lacks grounding.
        We must NOT paper over that with a high confidence score. A hedged
        answer should score low so the agent routes it to re-retrieval or human
        review instead of presenting it as authoritative.

    Returns full score (1.0) only if NONE of the uncertainty phrases appear;
    otherwise 0.0. This is deliberately binary: any explicit hedge is a hard
    signal in a safety context.
    """
    response_lower = response.lower()
    for phrase in UNCERTAINTY_PHRASES:
        if phrase in response_lower:
            return 0.0
    return 1.0


def _score_specificity(response: str) -> float:
    """Factor 3 (0.20): reward substantive answers, suspect terse ones.

    Clinical-safety reasoning:
        A one-line answer to a nuanced protocol question ("Give 5mg.") usually
        omits the conditions, contraindications, and monitoring that make
        clinical guidance safe. Longer answers aren't automatically correct,
        but extreme brevity correlates with dropped caveats — so length is a
        weak (0.20) secondary signal, not a primary one.

    Score = min(word_count / 50, 1.0). 50+ words is treated as fully specific.
    """
    word_count = len(response.split())
    return min(word_count / SPECIFICITY_TARGET_WORDS, 1.0)


def _score_no_contradiction(response: str, doc_terms: List[str]) -> float:
    """Factor 4 (0.10): detect answers that negate the source material.

    Clinical-safety reasoning:
        The most dangerous error is an *inversion* — the guideline says a drug
        is contraindicated and the answer says to administer it (or vice
        versa). We approximate this by finding negated terms in the response
        ("not X", "no X", "without X", "avoid X", "contraindicated ... X") and
        checking whether the negated word is one of the source's key terms. If
        the answer is negating a concept that the source treats as central,
        that's a possible contradiction and we withhold this factor's score.

        This is a heuristic, not a proof — true entailment checking needs an NLI
        model — so it carries the smallest weight (0.10) and acts as a
        tie-breaking guard rather than a primary determinant.

    Returns 1.0 if no contradiction is detected, else 0.0.
    """
    if not doc_terms:
        # Nothing to contradict.
        return 1.0

    response_lower = response.lower()
    doc_term_set = set(doc_terms)

    # Capture the word that follows a negation cue.
    negation_pattern = re.compile(
        r"\b(?:not|no|without|avoid|never|cannot|don't|do not|"
        r"contraindicated(?:\s+\w+){0,3}?)\s+(\w+)"
    )

    for match in negation_pattern.finditer(response_lower):
        negated_term = match.group(1)
        # If we are negating a term that the source considers a key concept,
        # treat it as a potential contradiction with the guideline.
        if negated_term in doc_term_set:
            return 0.0

    return 1.0


# ---------------------------------------------------------------------------
# Public API: the blended confidence score
# ---------------------------------------------------------------------------
def score_confidence(response: str, retrieved_docs: List[str], query: str) -> float:
    """Compute a grounding-confidence score in [0.0, 1.0] for an answer.

    Args:
        response: The LLM-drafted answer to evaluate.
        retrieved_docs: The guideline chunks that were provided as context.
        query: The original user question (reserved for future query-aware
            scoring; kept in the signature so callers/agent wiring are stable).

    Returns:
        A float in [0.0, 1.0]. Higher = better grounded / safer to surface as
        an authoritative clinical answer. The LangGraph agent compares this
        against thresholds to decide return / re-retrieve / escalate.

    The score is a transparent weighted sum of four deterministic factors so
    that any score can be explained after the fact — essential for a clinical
    safety layer that may need to be audited.
    """
    # Guard: an empty answer cannot be trusted.
    if not response or not response.strip():
        return 0.0

    # Build the source vocabulary once from ALL retrieved chunks combined, so
    # coverage/contradiction are measured against the full retrieved context.
    combined_docs = " ".join(retrieved_docs) if retrieved_docs else ""
    doc_terms = extract_key_terms(combined_docs)

    coverage = _score_context_coverage(response, doc_terms)
    no_uncertainty = _score_no_uncertainty(response)
    specificity = _score_specificity(response)
    no_contradiction = _score_no_contradiction(response, doc_terms)

    confidence = (
        WEIGHT_COVERAGE * coverage
        + WEIGHT_NO_UNCERTAINTY * no_uncertainty
        + WEIGHT_SPECIFICITY * specificity
        + WEIGHT_NO_CONTRADICTION * no_contradiction
    )

    logger.debug(
        "Confidence factors: coverage=%.3f no_uncertainty=%.3f "
        "specificity=%.3f no_contradiction=%.3f -> %.4f",
        coverage, no_uncertainty, specificity, no_contradiction, confidence,
    )

    # Clamp defensively against floating-point drift; the weights sum to 1.0 so
    # the natural range is already [0, 1].
    return round(max(0.0, min(confidence, 1.0)), 4)


def has_corpus_anchor(query: str, retrieved_docs: List[str]) -> bool:
    """True when query and retrieved text share a known in-corpus anchor term."""
    if not query or not retrieved_docs:
        return False
    query_terms = set(extract_key_terms(query))
    combined = " ".join(retrieved_docs).lower()
    return any(
        term in config.CORPUS_ANCHOR_TERMS and term in combined
        for term in query_terms
    )


def score_query_alignment(query: str, retrieved_docs: List[str]) -> float:
    """Discriminative query–corpus alignment in [0.0, 1.0].

    Uses corpus anchor terms, out-of-scope signatures, and non-generic query
    vocabulary so semantic retrieval of diabetes chunks does not falsely align
    with unrelated clinical topics (hypertension, harm reduction, etc.).
    """
    if not query or not query.strip():
        return 1.0

    query_terms = extract_key_terms(query)
    if not query_terms:
        return 1.0

    combined = " ".join(retrieved_docs).lower() if retrieved_docs else ""
    if not combined.strip():
        return 0.0

    for term in query_terms:
        if term in config.OUT_OF_SCOPE_SIGNATURE_TERMS and term not in combined:
            return 0.0

    discriminative = [
        term for term in query_terms
        if term not in STOP_WORDS and term not in ALIGNMENT_GENERIC_TERMS
    ]
    if not discriminative:
        return 1.0 if has_corpus_anchor(query, retrieved_docs) else 0.0

    matched = sum(1 for term in discriminative if term in combined)
    alignment = matched / len(discriminative)

    if not has_corpus_anchor(query, retrieved_docs):
        if alignment < config.QUERY_ALIGNMENT_STRICT:
            return 0.0

    return round(alignment, 4)


def decide_reflection_route(
    *,
    response: str,
    confidence: float,
    verdict: str,
    alignment: float,
    retry_count: int,
    high: float | None = None,
    medium: float | None = None,
    max_retries: int | None = None,
    alignment_min: float | None = None,
    insufficient_context: bool = False,
    corpus_grounded: bool = False,
) -> Tuple[str, bool, str, float]:
    """Return (route, flagged, flag_reason, adjusted_confidence).

    Policy (evaluated in order):
      1. Insufficient context / empty retrieval → flag
      2. Query not aligned with retrieved corpus → flag (out of scope)
      3. Validator CONTRADICTED → flag
      4. SUPPORTED or corpus-grounded + aligned → release (boost confidence)
      5. Heuristic high confidence → release
      6. Medium confidence + retries remaining → re-retrieve
      7. Otherwise → flag
    """
    high = high if high is not None else config.HIGH_CONFIDENCE
    medium = medium if medium is not None else config.MED_CONFIDENCE
    max_retries = max_retries if max_retries is not None else config.MAX_RETRIES
    alignment_min = alignment_min if alignment_min is not None else config.QUERY_ALIGNMENT_MIN

    if insufficient_context:
        return "flag", True, "insufficient_context", confidence

    if alignment < alignment_min:
        return "flag", True, "out_of_scope", confidence

    if verdict == "CONTRADICTED":
        return "flag", True, "contradicted", confidence

    if alignment >= alignment_min and verdict != "CONTRADICTED":
        if verdict == "SUPPORTED" or (corpus_grounded and confidence >= medium):
            adjusted = max(confidence, high)
            return "output", False, "", adjusted

    if confidence >= high:
        return "output", False, "", confidence

    if confidence >= medium and retry_count < max_retries:
        return "retrieve", False, "", confidence

    if retry_count >= max_retries:
        return "flag", True, "retries_exhausted", confidence

    return "flag", True, "low_confidence", confidence
