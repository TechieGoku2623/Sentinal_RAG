# Clinical Safety — Design Philosophy & Limitations

Sentinel-RAG is built around one conviction: **in clinical AI, being wrong
quietly is worse than admitting uncertainty.** This document explains the safety
problem, how the system addresses it, and — just as importantly — where it must
*not* be used.

> ⚠️ Sentinel-RAG is a research prototype. It is **not** a medical device, has
> not been clinically validated, and must **not** be used for real patient care.

---

## 1. The hallucination problem in healthcare

Large language models generate fluent, confident text regardless of whether
it's true. In most applications a hallucination is an inconvenience. In
healthcare it is a hazard:

- **Confidence ≠ correctness.** An LLM's tone is unrelated to whether its claim
  is supported. A fabricated dose or contraindication can read just as
  authoritatively as a correct one.
- **Plausible-but-wrong is the dangerous case.** Obvious nonsense gets caught.
  The real risk is an answer that *sounds* like a real guideline but subtly
  inverts a threshold, omits a contraindication, or invents an interaction.
- **Standard RAG doesn't fix this.** Retrieval improves grounding *on average*,
  but a vanilla pipeline still returns the first generation with no check that
  the answer actually reflects the retrieved text. Retrieval reduces the rate
  of hallucination; it does not *detect* it.

---

## 2. How Sentinel-RAG addresses it

Sentinel-RAG treats the model's first answer as a **draft to be verified**, not
a result to be trusted.

```
        draft ──► measure grounding ──► decide
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                     ▼
              return (grounded)    retry (borderline)    flag (uncertain)
```

The safety mechanisms, layered:

1. **Constrained generation.** The prompt forbids outside knowledge, requires
   explicit statements of uncertainty, bans fabricated values, and asks for
   guideline citations. Temperature is `0.1` for faithful, low-variance output.
2. **No-context refusal.** With an empty/irrelevant knowledge base the system
   returns `INSUFFICIENT_CONTEXT` instead of answering from memory.
3. **Deterministic grounding score.** A transparent, four-factor heuristic
   (coverage, no-hedging, specificity, no-contradiction) rates each draft. It is
   *not* a second LLM — so it is reproducible and auditable.
4. **Self-correction.** Borderline answers trigger a wider re-retrieval and a
   second attempt before any verdict is reached.
5. **Human-in-the-loop escalation.** Low-confidence or retry-exhausted answers
   are flagged for clinician review — a first-class, intended outcome.
6. **Traceability.** LangSmith records the context and output of every
   generation, providing an audit trail of evidence → answer.

**The invariant:** *no answer is presented as authoritative unless it is
measurably grounded in the source; otherwise it is flagged.*

---

## 3. Limitations — and when NOT to use it

Being honest about limits is part of safety.

**Known limitations**

- **The scorer is a heuristic, not truth.** Vocabulary overlap approximates
  grounding; it can be fooled by an answer that reuses source terms while
  misstating their relationship. The contradiction check is shallow (regex
  negation), not true natural-language inference.
- **Garbage in, garbage out.** The agent is only as good as the ingested
  guidelines. Outdated, wrong, or incomplete source documents yield confident,
  well-grounded — and wrong — answers.
- **Retrieval gaps.** If the relevant passage isn't retrieved, the answer can't
  be grounded; the system should flag this, but recall is not guaranteed.
- **No patient context.** It reasons over static guideline text, not an
  individual's history, labs, or comorbidities.
- **English / text-only.** PDF extraction can mangle tables and figures;
  non-text guidance (charts, dosing nomograms) is not understood.

**Do NOT use Sentinel-RAG for:**

- Real diagnosis, treatment, prescribing, or triage decisions.
- Any use without a qualified clinician reviewing every output.
- Situations requiring patient-specific reasoning or real-time data.
- Regulatory/billing decisions, or anything where an error harms a person.

**Appropriate uses:** education and demonstrations, prototyping retrieval over
guideline corpora, and research into self-reflective RAG and confidence
estimation.

---

## 4. Responsible AI framework applied

| Principle              | How Sentinel-RAG applies it                                                            |
| ---------------------- | -------------------------------------------------------------------------------------- |
| **Transparency**       | Confidence shown to the user; scorer is deterministic and explainable.                 |
| **Accountability**     | LangSmith traces give an audit trail of context → answer for every generation.         |
| **Human oversight**    | Uncertain answers are flagged and routed to a human; no autonomous clinical action.    |
| **Privacy**            | Local vector store + local CPU embeddings; data never leaves the machine by default.   |
| **Reliability/safety** | Bounded retries guarantee termination; no-context refusal prevents ungrounded answers. |
| **Fairness**           | Answers are constrained to the provided guidelines, reducing model-bias injection.     |
| **Honesty about scope**| Prominent, repeated disclaimers; documented limitations and out-of-scope uses.         |

---

## 5. Future safety improvements

- **Learned reward model.** Train a small classifier on clinician-labeled
  grounded/hallucinated answer pairs to replace or augment the heuristic, keeping
  the deterministic factors as an explainable fallback.
- **NLI-based contradiction detection.** Swap the regex negation check for a
  natural-language-inference model to catch true semantic inversions.
- **Calibration & thresholds.** Empirically calibrate confidence against
  expert judgments and tune thresholds to hit target false-flag / miss rates.
- **Citation verification.** Verify that each claim maps to a specific retrieved
  span; reject answers whose citations don't support them.
- **Adversarial & red-team evaluation.** Maintain a suite of known-hard and
  intentionally-misleading queries as a regression gate for every change.
- **Ensemble verification.** Require agreement among independent verifier agents
  before an answer earns a high-confidence label.

---

*Safety is never "done." If you find a failure mode, please open an issue using
the bug report template — adversarial examples are especially valuable.*
