# Application Flow

## Sentinel-RAG — Clinical Protocol Guardian

This document describes the end-to-end flows through Sentinel-RAG: how data enters
the system, what happens when a clinician asks a question, and how the
self-reflection loop decides to return, retry, or flag. It complements
`docs/PRD.md` (the *what/why*) and `docs/TRD.md` (the *how*).

---

## 1. High-Level Map

```
        ┌──────────────────────── CLINICIAN (Streamlit UI) ───────────────────────┐
        │                                                                          │
        │   Upload guidelines      Ask a protocol question      Rate / review      │
        └─────────┬───────────────────────┬──────────────────────────┬────────────┘
                  │                        │                          │
                  ▼                        ▼                          ▼
          [ INGEST FLOW ]          [ QUERY / AGENT FLOW ]      [ FEEDBACK + HISTORY ]
          parent-child chunks      retrieve→generate→          confidence_log.csv
          → ChromaDB               reflect→(retry?)→output      query_history.csv
```

---

## 2. Ingestion Flow (building the knowledge base)

Two entry points: the **sidebar uploader** (`app.py`) and the **CLI**
(`python -m src.ingest`).

```
 .txt / .pdf guideline file
        │  load_txt_file / load_pdf_file        (PyPDF2 for PDF; encrypted PDFs skipped)
        ▼
   raw document text
        │  chunk_with_parent_links(text, doc_name, source, publication_year)
        ▼
   PARENT chunks (500 words / 50 overlap)
        │  each parent further split →
        ▼
   CHILD chunks (100 words / 20 overlap)   each carries parent_id + provenance
        │  ingest_guidelines(items)  →  upsert (idempotent, stable IDs)
        ▼
   ChromaDB:
     clinical_guidelines_parent   (rich context for generation)
     clinical_guidelines_child    (precise retrieval targets)
```

**Notes**
- Provenance (`source`, `publication_year`, `doc_name`) is attached to every
  chunk. Local uploads default to the current reference year unless a real year is
  supplied (e.g. PubMed sources).
- Re-ingesting the same document **updates in place** (upsert + stable IDs) — no
  duplicates.
- The sidebar shows live counts: `N parent chunks | M child chunks`.

---

## 3. Query / Agent Flow (the core path)

When the clinician clicks **Validate Protocol**, `app.py` calls
`agent.run_agent(query, messages)`, which invokes the compiled LangGraph state
machine.

```
 run_agent(query, messages)
   │  init AgentState (uuid, timestamp, history)
   ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 1. RETRIEVE  (retrieve_node)                                                  │
 │    - top-5 child chunks (top-10 if this is a retry / expanded)                │
 │    - resolve distinct parent_ids → fetch parent chunks + metadata            │
 │    - empty KB → returns no docs                                               │
 └───────────────┬─────────────────────────────────────────────────────────────┘
                 ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 2. GENERATE  (generate_node → chains.generate_response)                       │
 │    - strict clinical prompt, temperature 0.1, only-from-context              │
 │    - includes last 3 turns of conversation history                          │
 │    - NO context → INSUFFICIENT_CONTEXT sentinel (refuses to answer)         │
 └───────────────┬─────────────────────────────────────────────────────────────┘
                 ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 3. REFLECT  (reflect_node) — CORE INNOVATION                                  │
 │    a. score_confidence(): 0.40·coverage + 0.30·no-hedge + 0.20·specificity   │
 │                           + 0.10·no-contradiction                           │
 │    b. cross_validate() second model → SUPPORTED / PARTIALLY / CONTRADICTED   │
 │         · PARTIALLY_SUPPORTED → confidence − 0.15                            │
 │         · CONTRADICTED        → force FLAG                                   │
 │    c. recency: any source > 5y old → confidence − 0.10 + append warning      │
 │    d. ROUTE decision (below)                                                 │
 └───────────────┬─────────────────────────────────────────────────────────────┘
                 ▼
        ┌─────────────────── route decision ───────────────────┐
        │                                                       │
   confidence ≥ 0.85                 0.75 ≤ conf < 0.85          conf < 0.75
   → OUTPUT                          AND retries < 2             OR retries ≥ 2
        │                            → RETRIEVE (loop back,      OR CONTRADICTED
        │                              expanded=True, retry++)   → FLAG
        │                                   │                         │
        │                                   └──────────┐              │
        ▼                                              ▼              ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 4. OUTPUT  (output_node)                                                      │
 │    - prepend "⚠️ FLAGGED FOR CLINICAL REVIEW" banner if flagged              │
 │    - append: Confidence %, Retrieval attempts, validation verdict line       │
 │    - append source citation previews                                         │
 │    - update conversation memory (last 3 turns)                              │
 └───────────────┬─────────────────────────────────────────────────────────────┘
                 ▼
              END → result dict → logged → rendered in UI
```

### 3.1 The three outcomes

| Outcome     | Trigger                                              | What the clinician sees                                  |
| ----------- | --------------------------------------------------- | ------------------------------------------------------- |
| **Return**  | confidence ≥ 0.85                                    | Answer + green "high confidence" banner + citations.    |
| **Retry**   | 0.75 ≤ confidence < 0.85 and retries < 2            | (Internal) loops back to RETRIEVE with a wider net; the final returned answer reports the number of attempts. |
| **Flag**    | confidence < 0.75, retries exhausted, or CONTRADICTED | Answer + red "🚩 FLAGGED FOR CLINICAL REVIEW" banner.   |

The retry cap (`MAX_RETRIES = 2`) guarantees the loop always terminates — a hard
question deterministically ends in a human-review flag, never an infinite loop.

---

## 4. Worked Examples (from the demo run)

```
Q: "What is the first-line treatment for Type 2 diabetes?"
   → coverage high, no hedging, specific      → confidence 98% → RETURNED

Q: "Can metformin be used with kidney disease?"
   → first pass borderline (≈0.80)            → RETRIEVE expanded → redraft
   → confidence 88%                            → RETURNED (after 1 re-query)

Q: "What happens if a patient misses a dose?"   (not in the guidelines)
   → model hedges ("not mentioned")           → confidence 27% → FLAGGED FOR REVIEW
```

The wording varies per run (LLM), but the confidence/retry/flag behavior is driven
by the deterministic reflection layer.

---

## 5. UI Flow (Streamlit)

### 5.1 Layout
```
┌────────────────────────────────────────────────────────────────┐
│ SIDEBAR                          │  MAIN                         │
│  • About                         │  Title: 🏥 Sentinel-RAG       │
│  • Tech stack                    │  ┌──────────────┬──────────┐  │
│  • 📂 Add Guidelines (upload)    │  │ 🔍 Validate  │ 📊 History│  │
│  • 📚 chunk counts               │  └──────────────┴──────────┘  │
│  • 📊 Feedback stats             │                               │
│  • 🔍 LangSmith link (if on)     │                               │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 Validate Protocol tab — interaction sequence
1. (Optional) upload guideline files in the sidebar → ingested → counts update.
2. Enter a clinical query; prior turns render as a chat transcript.
3. Click **Validate Protocol** → spinner while `run_agent` runs.
4. Results render:
   - **Confidence gauge** (%) + progress bar.
   - **Validation badge**: ✅ Supported / ⚠️ Partially Supported / 🚨 Contradicted.
   - **Retry caption**: "Agent re-queried N time(s)…".
   - **Status banner**: green (≥0.85) / amber (≥0.75) / red (<0.75).
   - **Flag banner** (red) if escalated.
   - **Validated Response** text.
   - **📚 Source Guidelines Used** expander — dated citations with currency
     (✅ Current / ⚠️ Aging / 🔴 Outdated).
5. **Feedback widget**: 👍 (5) / 👌 (3) / 👎 (1) → writes `human_rating` to the
   interaction row (survives Streamlit rerun).
6. **Clear Conversation** resets multi-turn memory.

### 5.3 Query History tab
- Table of past queries (`timestamp, query, confidence, flagged, retry_count`),
  flagged rows highlighted red.
- **📥 Download History** as CSV.

---

## 6. Feedback & Continuous-Learning Flow

```
 every run ──► log_interaction()  ──► append row to data/feedback/confidence_log.csv
                                       (confidence, verdict, flag, retries,
                                        doc count, latency, response preview)
 user rates ─► log_human_feedback(ts, rating) ──► fills human_rating (1–5) on that row
                                       │
                                       ▼
                          (features, human_rating) pairs
                                       │
                                       ▼
                   future learned reward model (v2) supervised signal
```

The sidebar **📊 Feedback Stats** panel surfaces the dataset as it grows:
total interactions, avg confidence, flag rate, avg user rating, total rated.

---

## 7. Observability Flow (LangSmith)

When tracing is configured (`LANGCHAIN_TRACING_V2=true` + key + project):

```
 run_agent(query)
   └── per pass through the graph
        ├── sentinel-rag-generation   (prompt | Groq | parser)  inputs: query+context
        └── sentinel-rag-validation   (validator fact-check)    verdict
```

A self-correction shows **multiple** generation runs under a single query — making
the reflection loop visible and giving an evidence→answer audit trail.

---

## 8. Error / Degradation Paths

| Situation                       | Behavior                                                            |
| ------------------------------- | ------------------------------------------------------------------ |
| Empty / irrelevant KB           | `INSUFFICIENT_CONTEXT` — refuses to answer from memory.            |
| LLM API transient failure       | Retry once, then safe error string (no raw stack trace in UI).     |
| Validator failure               | Verdict = `ERROR`, routing proceeds on the heuristic score only.   |
| Any node exception              | Caught; `run_agent` returns a **flagged** ERROR result.            |
| Encrypted / unreadable PDF      | Skipped with a warning during ingest, run continues.              |
| Feedback / history write fails  | Best-effort; logged, never blocks the response.                   |

**End-to-end invariant:** no answer is presented as authoritative unless it is
measurably grounded in the retrieved guidelines — otherwise it is explicitly
flagged for human review.
