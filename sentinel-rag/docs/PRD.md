# Product Requirements Document (PRD)

<div align="center">

## Sentinel-RAG · Clinical Protocol Guardian

*Enterprise-grade self-reflective RAG for guideline-grounded clinical protocol validation*

</div>

---

| Field            | Value                                              |
| ---------------- | -------------------------------------------------- |
| Product          | Sentinel-RAG — Clinical Protocol Guardian          |
| Document type    | Product Requirements Document (PRD)                |
| Status           | Draft / Living document                            |
| Owner            | Devasai Pranatheswar                               |
| Stage            | Research prototype (NOT a medical device)          |

> ⚠️ **Scope disclaimer:** Sentinel-RAG is a research prototype for demonstration
> only. It is **not** a medical device, has not been clinically validated, and
> must **not** be used for actual clinical decision-making. Every output requires
> review by a qualified clinician.

---

## 1. Overview

Sentinel-RAG answers clinical protocol questions strictly from a user-provided
corpus of guideline documents — and refuses to be confidently wrong. Unlike a
standard retrieve-then-answer RAG pipeline, it runs a **self-reflection loop**:
after drafting an answer, the agent grades how well that answer is grounded in
the retrieved source text and then either (a) returns it, (b) re-retrieves with a
wider net and tries again, or (c) flags it for human clinical review.

The core product belief: **in clinical AI, a fluent but ungrounded answer is not
a UX problem — it is a patient-safety event.** Surfacing uncertainty ("please
review this") is treated as a successful outcome; a silent, confident
hallucination is a failure.

---

## 2. Problem Statement

- **Healthcare AI cannot afford a confident hallucination.** A fluent but
  ungrounded answer about a dose, contraindication, or protocol step can directly
  cause patient harm.
- **Standard RAG fails silently.** Conventional pipelines return whatever the
  model produces on the first pass, with no check that the answer is actually
  supported by the retrieved guidelines. Model confidence is unrelated to
  correctness.
- **Safety controls must be auditable.** In a regulated, high-stakes domain, a
  safety layer that cannot be explained after the fact is itself a liability.

---

## 3. Goals & Non-Goals

### 3.1 Goals

1. Answer clinical questions **strictly from ingested guideline documents**, never
   from the model's parametric memory.
2. **Self-audit every answer** for grounding before it is shown, and quantify it
   as a confidence score.
3. **Escalate uncertainty** to a human clinician instead of presenting an
   unverified answer as authoritative.
4. Keep the safety layer **deterministic, transparent, and auditable**.
5. Provide **provenance and currency** for every answer (source citations + age
   of evidence).
6. Preserve a **privacy-first / on-prem-capable** posture (local vector store,
   local embeddings, self-hostable model).
7. Provide a **reproducible evaluation harness** so claims can be checked, not
   trusted.

### 3.2 Non-Goals

- Not a diagnostic, prescribing, triage, or treatment-decision tool.
- No patient-specific reasoning (no EHR/labs/comorbidity context in v1).
- No autonomous clinical action — a human reviews every output.
- Not a general-purpose chatbot; answers are constrained to ingested guidelines.
- No multi-modal understanding of charts, nomograms, or dosing tables in v1.

---

## 4. Target Users & Personas

| Persona                     | Need                                                                 |
| --------------------------- | ------------------------------------------------------------------- |
| **Clinician / reviewer**    | Quickly check what an internal guideline says, with a trust signal and a citation back to the source. |
| **Clinical informaticist**  | Ingest an institution's guideline corpus and audit how the agent grounds and flags answers. |
| **ML / safety engineer**    | Inspect the deterministic scorer, traces, and the feedback dataset; tune thresholds. |
| **Researcher / evaluator**  | Run the evaluation harness to measure grounding, flag rate, and validation agreement. |

---

## 5. User Stories

1. As a clinician, I can **ask a protocol question** and get an answer drawn only
   from our loaded guidelines, with a **confidence score** and a **clear warning**
   when the answer needs review.
2. As a clinician, I can **upload guideline documents** (PDF/TXT) and see how many
   chunks are now searchable.
3. As a clinician, I can **see the source passages** an answer relied on, with the
   **publication year and currency status** of each source.
4. As a clinician, I can **ask follow-up questions** that keep the conversation
   context.
5. As a clinician, I can **rate a response** (helpful / partial / not helpful) to
   improve the system over time.
6. As a reviewer, I can **see a query history** of past questions, their
   confidence, and whether they were flagged.
7. As an evaluator, I can **run a 50-question harness** and get a reproducible
   report (keyword match, avg confidence, flag rate, latency, validation
   agreement).

---

## 6. Functional Requirements

### 6.1 Knowledge base management
- **FR-1** Ingest `.txt` and `.pdf` guideline documents.
- **FR-2** Split documents using **parent-child chunking** (small chunks for
  precise retrieval, large chunks for rich generation context).
- **FR-3** Re-ingestion must be **idempotent** (stable IDs / upsert).
- **FR-4** Store **provenance** (`source`, `publication_year`, `doc_name`) on every
  chunk.
- **FR-5** Surface the **current chunk counts** (parent / child) in the UI.

### 6.2 Query & answer
- **FR-6** Retrieve the most relevant guideline passages for a query.
- **FR-7** Generate an answer **only** from retrieved context, under a strict
  clinical system prompt (no outside knowledge, no fabricated values, explicit
  uncertainty, cite the source).
- **FR-8** If the knowledge base is empty / irrelevant, return a **no-context
  refusal** instead of an ungrounded guess.
- **FR-9** Support **multi-turn conversation** with a bounded history window.

### 6.3 Self-reflection & safety (core)
- **FR-10** Compute a **deterministic grounding confidence** in `[0,1]` from four
  transparent factors (coverage, no-hedging, specificity, no-contradiction).
- **FR-11** Route by confidence: **return** if high, **re-retrieve & retry** if
  borderline (bounded), **flag** if low or retries exhausted.
- **FR-12** Run an **independent second-model fact-check** (SUPPORTED /
  PARTIALLY_SUPPORTED / CONTRADICTED) as a defense-in-depth gate; a CONTRADICTED
  verdict forces a flag.
- **FR-13** Apply a **recency penalty + warning** when any source is older than the
  aging threshold.
- **FR-14** Guarantee termination via a **hard retry cap**.

### 6.4 Output & provenance
- **FR-15** Present the answer with **confidence %, retrieval attempts, validation
  verdict, and a status banner**.
- **FR-16** Show a **flagged-for-review banner** when escalated.
- **FR-17** Show **dated source citations** with currency status
  (Current / Aging / Outdated).

### 6.5 Feedback & history
- **FR-18** Log every interaction's features to a CSV (reward-model dataset).
- **FR-19** Let the user attach a **1–5 helpfulness rating** to an interaction.
- **FR-20** Show **feedback aggregates** (interactions, avg confidence, flag rate,
  avg rating, total rated).
- **FR-21** Persist and display a **query history** with flagged rows highlighted
  and a CSV download.

### 6.6 Observability & evaluation
- **FR-22** Emit **LangSmith traces** for every generation when tracing is
  configured.
- **FR-23** Provide a **reproducible evaluation harness** over a 50-question
  dataset producing a JSON + printed report.

---

## 7. Non-Functional Requirements

| Category            | Requirement                                                                                  |
| ------------------- | -------------------------------------------------------------------------------------------- |
| **Safety**          | No answer is presented as authoritative unless measurably grounded; otherwise it is flagged. |
| **Auditability**    | The confidence scorer is deterministic and explainable; every score is reproducible.         |
| **Privacy**         | Local vector store + local CPU embeddings; source data never leaves the machine by default.   |
| **Portability**     | Self-hostable open-weights LLM; one-command Docker spin-up.                                   |
| **Reliability**     | No node may crash the graph; API calls degrade gracefully (retry once, then safe error).      |
| **Performance**     | Fast inference (Groq LPU) makes the multi-pass reflection loop practical in an interactive UI.|
| **Reproducibility** | Index rebuildable from source docs; deterministic scoring; pinned dependencies.               |
| **Testability**     | Unit/component tests run with **no API keys and no network** (mocked Chroma/Groq).            |

---

## 8. Safety Policy (Product-Level)

| Decision                              | Safety rationale                                          |
| ------------------------------------- | -------------------------------------------------------- |
| Deterministic scorer, not an LLM judge| Auditable & reproducible; avoids stacking hallucination risk. |
| "Answer only from context" prompt     | Blocks parametric-memory answers.                        |
| No-context refusal on empty KB        | Never answers with no evidence.                          |
| Bounded retries → guaranteed halt     | Hard questions end in review, not infinite loops.        |
| Flag is a *success* outcome           | "Please review" is safe; silent wrong answers are not.   |
| Second-model cross-validation         | Catches semantic inversions the lexical scorer misses.   |
| Recency de-rating + warning           | Grounded-but-stale evidence is treated as a risk.        |
| Local-only data + CPU embeddings      | PHI-adjacent text never leaves the box.                  |
| Source citations in every output      | Clinician can verify against the original text.          |

---

## 9. Success Metrics

Produced by the reproducible harness (`scripts/run_eval.py`) over the 50-question
dataset — **not** self-reported.

- **Keyword match rate** — answers contain expected clinical terms.
- **Average confidence** — mean grounding score across the set.
- **Flag rate** — fraction escalated to human review (correctly flagging
  unsupported questions is a *feature*, not a defect).
- **Average response time** — end-to-end latency per query.
- **Two-model validation agreement** — how often the validator agrees the answer
  is supported.
- **Adoption / engagement (UI):** total interactions logged, total rated, average
  human rating.

> **Honesty note:** no accuracy number is asserted until measured. Out of the box
> the bundled corpus is a single fictional diabetes guideline, so only diabetes
> questions are well-grounded; the rest are correctly flagged.

---

## 10. Assumptions & Dependencies

- A valid `GROQ_API_KEY` is available for generation + validation (LangSmith key
  optional for tracing).
- Ingested guidelines are the source of truth; quality of answers is bounded by
  quality/currency of the corpus ("garbage in, garbage out").
- Local files are assumed current-year unless a real publication year is provided.
- Runs on Python 3.11; ChromaDB persists to a local `./chroma_db` directory.

---

## 11. Out of Scope / Known Limitations

- The grounding scorer is a **heuristic**, not truth; vocabulary overlap can be
  fooled by answers that reuse terms while misstating relationships.
- The contradiction check is **shallow regex negation**, not true NLI.
- **No patient-specific reasoning**; static guideline text only.
- **English / text-only**; PDF extraction can mangle tables, charts, and
  nomograms.
- Retrieval recall is not guaranteed; a missed passage should be flagged but may
  reduce answerability.

---

## 12. Future Roadmap

- **Learned reward model** trained on clinician-labeled (grounded/hallucinated)
  pairs, keeping the deterministic factors as an explainable fallback.
- **NLI-based contradiction detection** to replace the regex negation check.
- **Async / parallel** retrieval and reflection passes to cut median latency.
- **Managed/hybrid vector backend** (behind a BAA) for multi-institution scale,
  with local ChromaDB as the privacy-first default.
- **FHIR integration** for patient-context-aware protocol validation.
- **Multi-agent ensemble verification** (citation checker + contradiction
  detector) requiring consensus before high-confidence output.
