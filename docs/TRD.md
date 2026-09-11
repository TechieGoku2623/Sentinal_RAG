# Technical Requirements Document (TRD)

## Sentinel-RAG — Clinical Protocol Guardian

| Field         | Value                                            |
| ------------- | ------------------------------------------------ |
| Document type | Technical Requirements Document (TRD)            |
| Companion     | See `docs/PRD.md`, `docs/APP_FLOW.md`, `docs/ARCHITECTURE.md`, `docs/CLINICAL_SAFETY.md` |
| Runtime       | Python 3.11                                       |
| Entry points  | `app.py` (Streamlit UI), `python -m src.ingest`, `scripts/run_eval.py` |

This document specifies *how* Sentinel-RAG is built: components, data model,
algorithms, configuration, interfaces, and operational requirements. It is the
engineering counterpart to the PRD.

---

## 1. System Architecture

Sentinel-RAG is a **cyclic LangGraph state machine** rather than a linear chain,
because clinical safety requires the ability to loop back for more evidence or
escalate to a human.

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

### 1.1 Component map

| Module                     | Responsibility                                                            |
| -------------------------- | ------------------------------------------------------------------------ |
| `src/agent.py`             | LangGraph state machine: nodes, routing, `run_agent` entry point.        |
| `src/retriever.py`         | All ChromaDB ops: parent/child collections, ingest, retrieval.           |
| `src/chains.py`            | Groq LLM client + strict clinical RAG prompt + generation.               |
| `src/reflection.py`        | Deterministic four-factor confidence scoring (core innovation).          |
| `src/validator.py`         | Second-model cross-validation (independent fact-checker).                 |
| `src/recency_scorer.py`    | Temporal recency scoring + outdated-source warnings.                      |
| `src/feedback_logger.py`   | Interaction + human-rating logging (reward-model dataset).               |
| `src/ingest.py`            | TXT/PDF loading + parent-child chunking pipeline.                         |
| `src/data_sources/`        | External fetchers: `pubmed.py`, `openfda.py` (recency-aware metadata).    |
| `src/config.py`            | Single source of truth for every tunable constant.                       |
| `app.py`                   | Streamlit UI (Validate Protocol + Query History tabs).                   |
| `scripts/run_eval.py`      | Reproducible 50-question evaluation harness.                             |
| `scripts/generate_demo_data.py` | Runs 5 sample queries → demo output.                                |

---

## 2. Technology Stack

| Technology              | Role                        | Rationale                                                                 |
| ----------------------- | --------------------------- | ------------------------------------------------------------------------ |
| **LangGraph**           | Agentic state machine       | Models the draft → reflect → retry **cycle** explicitly; a linear chain can't loop. |
| **Groq · Llama 3.1 8B** (`llama-3.1-8b-instant`) | LLM generation + validation | Open weights / self-hostable (path to air-gapped on-prem), HIPAA-friendlier, ~500 tok/s — makes the multi-pass loop practical. |
| **ChromaDB** (local)    | Vector store                | Runs on-prem; clinical data never leaves the machine; no third-party BAA.  |
| **all-MiniLM-L6-v2**    | Embeddings (384-dim, CPU)   | Small, fast, CPU-only — preserves the offline privacy posture.            |
| **LangChain**           | Prompt + chain orchestration| Clean templating/composition with first-class tracing hooks.             |
| **LangSmith**           | Observability / tracing     | Every generation (and its context) becomes inspectable for audit.        |
| **Streamlit**           | Clinician-facing UI         | Fast path to a clean healthcare UI with upload + dataframes.             |
| **pytest + pytest-mock**| Testing                     | Mocks Chroma/Groq so the suite runs with **no API keys / no network**.   |
| **Docker / compose**    | Deployment                  | Reproducible, portable, one-command spin-up.                             |

---

## 3. Data Model

### 3.1 Chunk schema (ingestion → ChromaDB)

Produced by `ingest.chunk_with_parent_links`; a flat list of dicts:

```
{
  "text": str,                       # chunk text
  "id": str,                         # "parent_<doc>_<i>" or "child_<doc>_<i>_<j>"
  "parent_id": str,                  # child → its parent; parent → self
  "chunk_type": "parent" | "child",
  "doc_name": str,                   # ID-safe document name
  "source": str,                     # provenance label (filename / "PubMed:..." )
  "publication_year": int            # 0 = unknown (treated as outdated)
}
```

### 3.2 ChromaDB collections (parent-child)

Two persistent collections under `./chroma_db`, cosine distance, local
`SentenceTransformerEmbeddingFunction` (all-MiniLM-L6-v2):

| Collection                          | Chunk size            | Purpose                                  |
| ----------------------------------- | --------------------- | ---------------------------------------- |
| `clinical_guidelines_child`         | 100 words / 20 overlap| Precise retrieval targets (queried).     |
| `clinical_guidelines_parent`        | 500 words / 50 overlap| Rich generation context (resolved via `parent_id`). |

Stored metadata per record: `source`, `publication_year`, `doc_name`,
`chunk_type`, and (children only) `parent_id`.

**Retrieval algorithm:** query the **child** collection (top-k), collect distinct
`parent_id`s in best-match order, fetch the corresponding **parent** chunks (rich
context), de-duplicate, and return text + metadata. Falls back to child records if
parent linkage is missing.

### 3.3 `AgentState` (LangGraph shared state)

```
AgentState = {
  query:               str
  retrieved_docs:      List[str]
  retrieved_metadata:  List[dict]      # provenance per doc
  response:            str
  confidence:          float           # [0,1]
  flagged:             bool
  retry_count:         int
  route:               str             # "output" | "retrieve" | "flag"
  timestamp:           str             # ISO-8601 run start
  messages:            List[dict]      # conversational memory (last 3 turns)
  conversation_id:     str             # uuid per run
  validation_verdict:  str             # SUPPORTED|PARTIALLY_SUPPORTED|CONTRADICTED|ERROR
}
```

### 3.4 Feedback log (`data/feedback/confidence_log.csv`)

Append-only CSV; one row per interaction. Columns (order is the on-disk schema):

```
timestamp, conversation_id, query, response_preview, confidence_score,
validation_verdict, flagged, retry_count, retrieved_doc_count,
response_time_ms, human_rating
```

`human_rating` is empty until the user rates (1–5). This `(features, rating)`
table is the supervised dataset for a future learned reward model.

### 3.5 Query history (`query_history.csv`)

UI-side history written by `app.py`: `timestamp, query, confidence, flagged,
retry_count`.

---

## 4. Core Algorithms

### 4.1 Deterministic confidence scoring (`reflection.score_confidence`)

A weighted sum of four transparent factors, each in `[0,1]`:

```
confidence = 0.40·coverage + 0.30·no_uncertainty + 0.20·specificity + 0.10·no_contradiction
```

| Factor              | Weight | Computation                                                              |
| ------------------- | :----: | ----------------------------------------------------------------------- |
| **Context coverage**| 0.40   | `matched_doc_terms / total_doc_terms` (capped 1.0) — does the answer reuse the source's vocabulary? |
| **No uncertainty**  | 0.30   | `1.0` if no hedging phrase present, else `0.0` (binary).                 |
| **Specificity**     | 0.20   | `min(word_count / 50, 1.0)`.                                            |
| **No contradiction**| 0.10   | `0.0` if a negated word matches a source key term, else `1.0`.          |

- `extract_key_terms`: lowercase → tokenize (`\b\w+\b`) → drop stop words,
  sub-3-char tokens, bare digits → rank by frequency (ties by first appearance) →
  top 30. **Deterministic** for reproducibility.
- Hedging phrases (case-insensitive substrings): `"i don't know"`,
  `"i'm not sure"`, `"insufficient context"`, `"cannot determine"`, `"unclear"`,
  `"not mentioned"`, `"not found"`, `"no information"`, …
- Empty answer ⇒ `0.0`. Empty doc terms ⇒ coverage `0.0`, no-contradiction `1.0`.

### 4.2 Routing policy (`reflect_node`, thresholds in `config.py`)

```
confidence ≥ 0.85 (HIGH)                          → output   (trust & return)
0.75 (MED) ≤ confidence < 0.85 AND retries < 2    → retrieve (expanded, retry)
confidence < 0.75  OR  retries ≥ 2 (MAX_RETRIES)  → flag     (human review)
```

Penalties/overrides applied in `reflect_node` before routing:
- Validator `PARTIALLY_SUPPORTED` ⇒ `confidence -= 0.15` (`PARTIAL_SUPPORT_PENALTY`).
- Validator `CONTRADICTED` ⇒ **force flag** regardless of score.
- Any source older than `AGING_YEARS` (5) ⇒ `confidence -= 0.10`
  (`OUTDATED_SOURCE_PENALTY`) **and** append the outdated warning to the response.

The retry cap (`MAX_RETRIES = 2`) guarantees termination.

### 4.3 Two-model cross-validation (`validator.cross_validate`)

Independent Groq/Llama 3.1 call at **temperature 0.0** acting as a fact-checker.
Returns one of `SUPPORTED` (1.0) / `PARTIALLY_SUPPORTED` (0.6) / `CONTRADICTED`
(0.0) / `ERROR`. Verdict parsing tests the most specific keywords first. Degrades
to `ERROR` (non-fatal) on API/parse failure.

### 4.4 Recency scoring (`recency_scorer`)

Maps `publication_year` → score band; unknown year ⇒ treated as outdated (0.20):

```
≤1y → 1.00 Very recent   ≤3y → 0.85 Recent   ≤5y → 0.65 Acceptable
≤10y → 0.40 Aging        >10y → 0.20 Outdated
```

`should_warn_outdated` returns true if **any** source is older than `AGING_YEARS`.
`recency_label` → UI `(icon, label)`: ✅ Current (≤3y) / ⚠️ Aging (≤9y) / 🔴
Outdated. `CURRENT_YEAR` is pinned in config for deterministic scoring/tests.

### 4.5 Generation prompt contract (`chains.py`)

Strict clinical system prompt: answer **only** from provided context; state
uncertainty explicitly; never fabricate dosages/thresholds/contraindications;
cite the relied-upon section; surface ambiguity. Temperature `0.1`. Empty context
⇒ returns the `INSUFFICIENT_CONTEXT` sentinel (no parametric-memory answer).
Generation retries once on transient API error, then returns a safe error string.

---

## 5. Configuration (`src/config.py`)

| Constant                                | Value                       | Meaning                                   |
| --------------------------------------- | --------------------------- | ----------------------------------------- |
| `LLM_MODEL`                             | `llama-3.1-8b-instant`      | Generation + validation model.            |
| `LLM_TEMPERATURE` / `VALIDATOR_TEMPERATURE` | `0.1` / `0.0`           | Faithful generation / deterministic check.|
| `EMBEDDING_MODEL`                       | `all-MiniLM-L6-v2`          | Local CPU embeddings.                      |
| `HIGH_CONFIDENCE` / `MED_CONFIDENCE`    | `0.85` / `0.75`             | Routing thresholds.                       |
| `MAX_RETRIES`                           | `2`                         | Hard cap on re-retrieval loops.           |
| `PARTIAL_SUPPORT_PENALTY` / `OUTDATED_SOURCE_PENALTY` | `0.15` / `0.10` | Confidence penalties.                     |
| `MAX_HISTORY_MESSAGES` / `HISTORY_WINDOW` | `6` / `3`                 | Memory cap / turns surfaced into prompt.   |
| `CHILD_CHUNK_SIZE` / `CHILD_OVERLAP`    | `100` / `20`                | Child chunking.                           |
| `PARENT_CHUNK_SIZE` / `PARENT_OVERLAP`  | `500` / `50`                | Parent chunking.                          |
| `DEFAULT_RESULTS` / `EXPANDED_RESULTS`  | `5` / `10`                  | Normal vs retry retrieval breadth.        |
| `CURRENT_YEAR`                          | `2025`                      | Pinned reference year.                     |
| `RECENT_YEARS` / `AGING_YEARS`          | `3` / `5`                   | Recency bands.                            |
| `PUBMED_RATE_LIMIT_SECONDS`             | `0.34`                      | NCBI ≤3 req/s compliance.                  |
| `HTTP_TIMEOUT_SECONDS` / `HTTP_MAX_RETRIES` | `15` / `1`              | External HTTP behavior.                   |
| `CHROMA_PATH`                           | `./chroma_db`               | Local persistence dir.                     |
| `FEEDBACK_FILE`                         | `data/feedback/confidence_log.csv` | Reward-model dataset.              |

### 5.1 Environment variables (`.env`)

| Variable                | Required | Purpose                                   |
| ----------------------- | :------: | ----------------------------------------- |
| `GROQ_API_KEY`          | Yes      | Generation + validation LLM calls.        |
| `LANGCHAIN_API_KEY`     | No       | LangSmith tracing.                        |
| `LANGCHAIN_TRACING_V2`  | No       | `true` to enable tracing.                 |
| `LANGCHAIN_PROJECT`     | No       | Trace project (default `sentinel-rag-clinical`). |

---

## 6. Interfaces

### 6.1 Primary internal API (`agent.run_agent`)

```python
run_agent(query: str, messages: List[dict] = None) -> dict
```

Returns: `response` (formatted), `confidence`, `flagged`, `retry_count`,
`messages` (trimmed history), `conversation_id`, `validation_verdict`, `sources`
(provenance list), `response_time_ms`, `log_timestamp`, `query`.

### 6.2 Module functions

- `retriever.retrieve_with_metadata(query, expanded=False) -> List[dict]`
- `retriever.ingest_guidelines(chunks) -> None`
- `retriever.get_collection_count() -> {"parent": int, "child": int}`
- `chains.generate_response(query, context, messages=None) -> str`
- `reflection.score_confidence(response, retrieved_docs, query) -> float`
- `validator.cross_validate(response, context, query) -> dict`
- `feedback_logger.log_interaction(result, response_time_ms) -> str`
- `feedback_logger.log_human_feedback(timestamp, rating) -> bool`
- `feedback_logger.get_feedback_stats() -> dict`

### 6.3 UI (`app.py`)
- **Sidebar:** about, tech stack, guideline upload, chunk counts, feedback stats,
  LangSmith link.
- **Tab 1 — Validate Protocol:** query box, conversation transcript, results
  (confidence gauge, validation badge, status banner, flag banner, response,
  dated citations), feedback widget.
- **Tab 2 — Query History:** table (flagged rows highlighted) + CSV download.

---

## 7. Error Handling & Resilience

- **No graph node may crash the run.** Every node wraps its work in try/except and
  degrades to safe defaults; `run_agent` returns a flagged ERROR result on any
  unexpected failure.
- **Empty/irrelevant KB** ⇒ `INSUFFICIENT_CONTEXT` (never answer from memory).
- **LLM API failures** ⇒ retry once (`HTTP_MAX_RETRIES`), then a safe error string;
  validator failures degrade to `ERROR` verdict (non-blocking).
- **Encrypted/unreadable PDFs** are skipped with a warning, not fatal.
- **Feedback/history logging is best-effort** — it must never break a response.

---

## 8. Security & Privacy

- **Local-only data path:** ChromaDB `PersistentClient` + local CPU embeddings;
  no vector or document leaves the machine by default.
- **Self-hostable model:** Llama 3.1 can be moved on-prem (vLLM/Ollama/TGI) with
  no code change beyond the client — a path to air-gapped deployment.
- **Secrets** via `.env` (not committed); `GROQ_API_KEY` read at call time.
- **No PHI** is expected in the prototype; clinical disclaimers are prominent.

---

## 9. Observability

- **LangSmith:** setting `LANGCHAIN_TRACING_V2=true` + key + project auto-emits a
  trace per chain invocation. Generation tagged `sentinel-rag-generation`,
  validation tagged `sentinel-rag-validation`. A self-correction loop shows
  multiple generation runs under one query — traces double as an evidence→answer
  audit log.
- **Structured logging** at INFO across nodes (retrieval latency, confidence
  factors, validation verdict, flag reason).

---

## 10. Testing

- `tests/test_agent.py`, `tests/test_components.py`: mocked unit + component tests.
- **Run with no API keys and no network** (Chroma/Groq mocked via pytest-mock).
- CI: `.github/workflows/ci.yml`.

---

## 11. Evaluation Harness (`scripts/run_eval.py`)

- **Dataset:** `data/eval/eval_questions.json` — 50 questions across 5 categories
  (diabetes, harm reduction, hypertension, drug interactions, general protocols),
  each with expected keywords, a source (ADA/CDC/FDA), and difficulty.
- **Output:** runs every question through `run_agent`, records confidence, flag
  status, validation verdict, keyword hits, response time → `eval_results.json` +
  printed report (keyword match rate, avg confidence, flag rate, avg latency,
  validation agreement).

---

## 12. Deployment

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # add GROQ_API_KEY (+ optional LangSmith)
python -m src.ingest          # build the knowledge base
streamlit run app.py          # http://localhost:8501
```

- **Docker:** `python:3.11-slim` image (`Dockerfile`), Streamlit entrypoint;
  `docker-compose.yml` maps the port and mounts `chroma_db/` + `.env` volumes.
- Run ingestion as a module (`python -m src.ingest`) so package imports resolve.

---

## 13. Constraints & Technical Debt

- `docs/ARCHITECTURE.md` §3 describes an earlier **single-collection** schema; the
  current implementation uses the **parent-child** two-collection design described
  here (§3.2) — keep this TRD authoritative for the data model.
- The contradiction factor is regex-based, not NLI — a known approximation.
- Retrieval, generation, reflection, and validation run **synchronously**; async
  parallelization is a roadmap item.
- `score_confidence`/`cross_validate` accept `query` for forward-compatible
  query-aware scoring but do not yet use it.
