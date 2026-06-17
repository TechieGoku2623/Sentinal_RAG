# Sentinel-RAG — Architecture Deep Dive

This document explains *how* Sentinel-RAG is built and *why* each design choice
was made. It is written for engineers and reviewers who want to understand —
and trust — the internals of the clinical safety layer.

- [1. Why a LangGraph state machine instead of a simple chain](#1-why-a-langgraph-state-machine-instead-of-a-simple-chain)
- [2. The confidence scoring algorithm](#2-the-confidence-scoring-algorithm)
- [3. ChromaDB schema and embedding strategy](#3-chromadb-schema-and-embedding-strategy)
- [4. How LangSmith traces are structured](#4-how-langsmith-traces-are-structured)
- [5. Clinical safety design decisions](#5-clinical-safety-design-decisions)

---

## 1. Why a LangGraph state machine instead of a simple chain

A conventional RAG pipeline is a **directed line**:

```
   retrieve ──► generate ──► return
```

It executes once and returns whatever the model produced. There is no way for a
node to look at a result and decide to *go back*. That is precisely the
capability clinical safety requires: the ability to say "this answer isn't good
enough — gather more evidence and try again," or "stop, escalate to a human."

Sentinel-RAG is therefore modeled as a **cyclic state machine** (a graph), where
a shared `AgentState` flows between nodes and a routing function can send
execution backward:

```
                 ┌───────────────────────────────────────────┐
                 │           route == "retrieve"              │
                 ▼                                            │
        ┌─────────────┐    ┌─────────────┐    ┌───────────────┴───┐
 START ─► retrieve    ├───►│  generate   ├───►│      reflect      │
        └─────────────┘    └─────────────┘    └─────────┬─────────┘
                                                         │ conditional edge
                                          route=="output"│ / "flag"
                                                         ▼
                                                   ┌──────────┐
                                                   │  output  ├──► END
                                                   └──────────┘
```

**Shared state (`AgentState`):**

```
AgentState = {
    query:               str
    retrieved_docs:      List[str]
    retrieved_metadata:  List[dict]      # source, publication_year, doc_name
    response:            str
    confidence:          float           # [0, 1]
    flagged:             bool
    retry_count:         int
    route:               str             # "output" | "retrieve" | "flag"
    timestamp:           str
    messages:            List[dict]      # conversational memory (last 3 turns)
    conversation_id:     str
    validation_verdict:  str             # SUPPORTED | PARTIALLY_SUPPORTED | CONTRADICTED
}
```

**Why this matters:**

| Need                                   | Simple chain | LangGraph state machine |
| -------------------------------------- | :----------: | :---------------------: |
| Loop back to gather more context       |      ❌       |           ✅            |
| Branch on a runtime confidence score   |      ❌       |           ✅            |
| Bounded retries (guaranteed to halt)   |      ❌       |           ✅            |
| Inspectable per-node state for tracing |   partial    |           ✅            |

The retry budget (`MAX_RETRIES = 2`) guarantees termination: a hard question
deterministically ends in a human-review flag rather than an infinite loop.

---

## 2. The confidence scoring algorithm

The reflection layer (`src/reflection.py`) computes a **deterministic** grounding
score — it is *not* a second LLM judging the first. Determinism is a feature:
every score is reproducible and explainable, which is essential for auditing a
clinical safety control.

```
score_confidence(response, retrieved_docs, query)
│
├─ Factor 1 — Context Coverage ............ weight 0.40
│     matched_doc_terms / total_doc_terms  (capped at 1.0)
│     "Does the answer reuse the source's vocabulary?"
│
├─ Factor 2 — No Uncertainty Signals ...... weight 0.30
│     1.0 if NO hedging phrase present, else 0.0
│     phrases: "i don't know", "i'm not sure", "insufficient context",
│              "cannot determine", "unclear", "not mentioned",
│              "not found", "no information"
│
├─ Factor 3 — Specificity ................. weight 0.20
│     min(word_count / 50, 1.0)
│     "Is it substantive, or a vague one-liner?"
│
└─ Factor 4 — No Contradiction ............ weight 0.10
      1.0 unless a negated word matches a source key term
      "Does the answer invert the source?"

confidence = 0.40·F1 + 0.30·F2 + 0.20·F3 + 0.10·F4      ∈ [0, 1]
```

**Weighting rationale (a clinical-safety prior):**

```
 grounding (F1)  ████████████████   0.40   ← #1 failure mode: answering from
 hedging   (F2)  ████████████       0.30      parametric memory, not the source
 length    (F3)  ████████           0.20
 contra'n  (F4)  ████               0.10   ← heuristic guard, smallest weight
```

**Routing thresholds (`src/agent.py`):**

```
 confidence ≥ 0.85                        → OUTPUT   (trust & return)
 0.75 ≤ confidence < 0.85 AND retries < 2 → RETRIEVE (widen context, retry)
 confidence < 0.75  OR  retries exhausted → FLAG     (human review)
```

`extract_key_terms()` builds the source vocabulary: lowercase → tokenize →
drop stop words, sub-3-char tokens, and bare digits → rank by frequency
(ties broken by first appearance for determinism) → top 30 terms.

---

## 3. ChromaDB schema and embedding strategy

Sentinel-RAG uses **two local, persistent collections** in a parent-child
retrieval pattern — small chunks for precise search, large chunks for rich
generation context.

```
PersistentClient(path="./chroma_db")
├── collection: "clinical_guidelines_child"
│   ├── chunk size: 100 words / 20 overlap
│   ├── embedding: all-MiniLM-L6-v2 (384-dim, local CPU)
│   ├── distance: cosine
│   └── metadata: source, publication_year, doc_name, parent_id, chunk_type
│
└── collection: "clinical_guidelines_parent"
    ├── chunk size: 500 words / 50 overlap
    ├── same embedding function
    └── metadata: source, publication_year, doc_name, chunk_type
```

**Retrieval flow:**

```
query
  │  embed + search CHILD collection (top-5 normal, top-10 expanded)
  ▼
child hits with parent_id metadata
  │  resolve distinct parent_ids in best-match order
  ▼
fetch PARENT chunks (rich context) + provenance metadata
  ▼
return to generate / reflect nodes
```

**Ingestion pipeline (`src/ingest.py`):**

```
  data/guidelines/*.txt|*.pdf  (or UI upload)
        │  load (PyPDF2 for PDF, UTF-8 for TXT)
        ▼
  raw text
        │  chunk_with_parent_links()
        ▼
  PARENT chunks (500w) ──► each split into CHILD chunks (100w)
        │  ingest_guidelines() → upsert both collections
        ▼
  ChromaDB parent + child collections
```

**Design choices:**

- **Parent-child decoupling.** Small chunks retrieve precisely; large chunks
  preserve conditions, contraindications, and monitoring context the model needs
  for safe answers.
- **`upsert` + stable IDs** (`parent_<doc>_<i>`, `child_<doc>_<i>_<j>`) make
  re-ingestion idempotent.
- **Provenance on every chunk** enables temporal recency scoring and dated
  citations in the UI.
- **Cosine distance** is the standard match for normalized MiniLM embeddings.
- **Local + CPU embeddings.** No vector or document leaves the machine.

**Retrieval breadth** is dynamic: normal passes fetch `top-5` child chunks; a
reflection retry fetches `top-10` (`expanded=True`).

---

## 3b. Defense-in-depth gates (beyond lexical scoring)

After `score_confidence`, the reflect node applies two additional gates before
routing:

| Gate | Module | Effect |
| ---- | ------ | ------ |
| Cross-validation | `validator.py` | Second LLM pass labels answer SUPPORTED / PARTIALLY_SUPPORTED / CONTRADICTED; CONTRADICTED forces flag |
| Recency | `recency_scorer.py` | Sources >5 years old trigger confidence penalty + clinician warning |

See `docs/TRD.md` for exact penalty values and routing thresholds.

---

## 4. How LangSmith traces are structured

Setting `LANGCHAIN_TRACING_V2=true` (plus an API key + project) makes LangChain
emit a trace automatically for every chain invocation — no extra code. The
generation chain is tagged `run_name="sentinel-rag-generation"` for easy
filtering.

```
Trace: run_agent(query)
└── (per pass through the graph)
    └── sentinel-rag-generation                 ← ChatPromptTemplate | ChatGroq | StrOutputParser
        ├── inputs:  { query, context }          ← retrieved chunks joined with "---"
        ├── prompt:  clinical system + user msg
        ├── model:   llama-3.1-8b-instant @ temp 0.1
        └── output:  draft answer
```

On a self-correction loop you will see **multiple** `sentinel-rag-generation`
runs under a single user query — one per retry — which makes the reflection
behavior visible and debuggable. Because traces capture the exact context and
output for each generation, they double as an **audit log** of what evidence
produced which answer.

---

## 5. Clinical safety design decisions

These are deliberate, defensible choices — see `docs/CLINICAL_SAFETY.md` for the
full rationale.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Decision                          │ Safety rationale                      │
├───────────────────────────────────┼───────────────────────────────────────┤
│ Deterministic scorer, not an LLM  │ Auditable & reproducible; avoids       │
│   judge                           │ stacking hallucination risk.           │
│ "Answer only from context" prompt │ Blocks parametric-memory answers.      │
│ INSUFFICIENT_CONTEXT on empty KB  │ Never answers with no evidence.        │
│ Bounded retries → guaranteed halt │ Hard questions end in review, not loops│
│ Flag is a *success* outcome       │ "Please review" is safe; silent wrong  │
│                                   │ answers are not.                       │
│ Local-only data + CPU embeddings  │ PHI-adjacent text never leaves the box │
│ temperature = 0.1                 │ Faithful, low-variance clinical output │
│ Source citations in every output  │ Clinician can verify against the text  │
└───────────────────────────────────┴───────────────────────────────────────┘
```

**The end-to-end safety invariant:** an answer is never returned as
authoritative unless it is *measurably grounded* in the retrieved guidelines —
otherwise it is explicitly flagged for human review. The system may be unsure,
but it is never *silently, confidently wrong*.
