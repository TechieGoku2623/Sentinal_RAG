"""End-to-end platform architecture for Sentinel-RAG."""

# End-to-end platform guide

Sentinel-RAG is now a **three-tier clinical RAG platform**: clinician UI, REST API, and persistent audit storage — all sharing the same LangGraph agent, ChromaDB index, and safety pipeline.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Streamlit UI   │     │   FastAPI API   │     │  Next.js landing │
│  :8501          │     │   :8000         │     │  :3000           │
└────────┬────────┘     └────────┬────────┘     └────────┬─────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │  Service layer         │
                    │  query / knowledge /   │
                    │  audit                 │
                    └────────────┬───────────┘
                                 ▼
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ LangGraph agent │   │ ChromaDB        │   │ SQLite audit DB │
│ (Groq LLM)      │   │ parent/child    │   │ interactions +  │
│                 │   │                 │   │ document registry│
└─────────────────┘   └─────────────────┘   └─────────────────┘
         │                       ▲
         ▼                       │
┌─────────────────┐   ┌─────────────────┐
│ PubMed (NCBI)   │   │ OpenFDA labels  │
└─────────────────┘   └─────────────────┘
```

## Components added

| Layer | Technology | Purpose |
|-------|------------|---------|
| REST API | FastAPI + Uvicorn | Integrations, mobile, batch jobs |
| Audit DB | SQLAlchemy + SQLite | Interactions, audit events, doc registry |
| External ingest | PubMed + OpenFDA | Live evidence into ChromaDB |
| Admin UI | Streamlit tabs | KB delete, re-index, audit view |
| **Clinical recollection** | Spaced repetition + study queue | Trainee & experienced protocol memory |
| Auth | `X-API-Key` header | Optional API gate (`SENTINEL_API_KEY`) |

## Run the full stack

### 1. Install dependencies

```bash
pip install -r requirements.txt
python -m src.ingest
```

### 2. Start API + UI

```bash
# Terminal 1 — REST API
uvicorn src.api.main:app --reload --port 8000

# Terminal 2 — Clinician UI
streamlit run app.py

# Terminal 3 — Landing (optional)
cd landing && npm run dev
```

### 3. Docker Compose

```bash
docker compose up --build
```

- UI: http://localhost:8501  
- API: http://localhost:8000  
- API docs: http://localhost:8000/docs  

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + Chroma counts |
| GET | `/v1/metrics` | Platform + eval metrics |
| POST | `/v1/query` | Run clinical validation |
| POST | `/v1/feedback` | Clinician rating (1–5) |
| GET | `/v1/audit/interactions` | Query audit log |
| GET | `/v1/audit/events` | Ingest/delete/admin events |
| GET | `/v1/knowledge` | Document registry overview |
| POST | `/v1/knowledge/upload` | Upload PDF/TXT |
| POST | `/v1/knowledge/pubmed` | Ingest PubMed search |
| POST | `/v1/knowledge/openfda` | Ingest FDA drug label |
| DELETE | `/v1/knowledge/{doc_name}` | Remove document |
| GET | `/v1/recollection/summary` | Learning dashboard metrics |
| GET | `/v1/recollection/queue` | Due topics + study queue |
| POST | `/v1/recollection/review` | Log recall self-rating (spaced repetition) |

### Example: clinical query

```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is first-line therapy for type 2 diabetes?"}'
```

With API key enabled:

```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"query": "metformin contraindications"}'
```

### Example: PubMed ingest

```bash
curl -X POST http://localhost:8000/v1/knowledge/pubmed \
  -H "Content-Type: application/json" \
  -d '{"query": "metformin diabetes guidelines", "max_results": 5}'
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GROQ_API_KEY` | — | LLM generation + validation |
| `SENTINEL_API_KEY` | empty | API auth (empty = dev mode) |
| `DATABASE_URL` | `sqlite:///./data/sentinel.db` | Audit persistence |
| `CORS_ORIGINS` | localhost ports | API CORS |

## Production roadmap

Still recommended for regulated deployment:

1. **Postgres** instead of SQLite (`DATABASE_URL=postgresql://...`)
2. **SSO / OAuth** (Clerk, Auth0) replacing API-key-only auth
3. **Tenant-scoped Chroma** collections per organization
4. **Background workers** (Celery/RQ) for large ingest jobs
5. **Observability** — Prometheus metrics, OpenTelemetry traces
6. **Learned reward model** trained on `interactions` table + human ratings

See `docs/PRD.md` §12 and `docs/TRD.md` §13 for the full v2 roadmap.
