"""Sentinel-RAG REST API — end-to-end platform layer.

Run locally:
    uvicorn src.api.main:app --reload --port 8000

Endpoints cover clinical query, feedback, knowledge ingest, audit, and metrics.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.api.deps import require_api_key
from src.api.schemas import (
    FeedbackRequest,
    HealthResponse,
    MetricsResponse,
    OpenFDAIngestRequest,
    PubMedIngestRequest,
    QueryRequest,
    QueryResponse,
    RecollectionReviewRequest,
    WorkspaceCreateRequest,
    WorkspacePlanUpdateRequest,
)
from src.db.session import init_db
from src.retriever import get_collection_count
from src.services.audit_service import (
    get_platform_stats,
    list_audit_events,
    list_interactions,
    log_human_feedback,
)
from src.services.knowledge_service import (
    get_knowledge_overview,
    ingest_openfda,
    ingest_pubmed,
    ingest_uploaded_file,
    remove_document,
)
from src.services.query_service import QuotaExceededError, execute_query
from src.services.recollection_service import (
    get_due_topics,
    get_recollection_summary,
    get_recent_topics,
    get_study_queue,
    record_study_attempt,
)
from src.services.workspace_service import (
    create_workspace,
    get_usage,
    list_workspaces,
    update_workspace_plan,
)
from src.text_utils import extract_clinical_answer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Sentinel-RAG API started.")
    yield


app = FastAPI(
    title="Sentinel-RAG API",
    description="Clinical Protocol Guardian — self-reflective RAG with audit and governance.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = os.getenv("CORS_ORIGINS", config.CORS_ORIGINS).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    counts = get_collection_count()
    return HealthResponse(
        status="ok",
        chroma_parent_chunks=counts.get("parent", 0),
        chroma_child_chunks=counts.get("child", 0),
    )


@app.get("/v1/metrics", response_model=MetricsResponse)
def metrics(
    tenant_id: str = "default",
    _: str = Depends(require_api_key),
) -> MetricsResponse:
    stats = get_platform_stats(tenant_id)
    eval_path = Path("data/eval/eval_results.json")
    if eval_path.exists():
        try:
            eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
            stats["eval_keyword_match_rate"] = eval_data.get("keyword_match_rate")
            stats["eval_avg_confidence"] = eval_data.get("avg_confidence")
        except Exception:  # noqa: BLE001
            pass
    return MetricsResponse(**stats)


@app.post("/v1/query", response_model=QueryResponse)
def query_clinical(
    body: QueryRequest,
    _: str = Depends(require_api_key),
) -> QueryResponse:
    try:
        result = execute_query(body.query, body.messages, tenant_id=body.tenant_id)
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    answer = extract_clinical_answer(
        result.get("response", ""),
        result.get("messages", []),
    )
    return QueryResponse(
        response=answer,
        confidence=float(result.get("confidence", 0.0)),
        flagged=bool(result.get("flagged", False)),
        retry_count=int(result.get("retry_count", 0)),
        validation_verdict=str(result.get("validation_verdict", "ERROR")),
        flag_reason=str(result.get("flag_reason", "")),
        conversation_id=str(result.get("conversation_id", "")),
        response_time_ms=int(result.get("response_time_ms", 0)),
        log_timestamp=str(result.get("log_timestamp", "")),
        sources=result.get("sources") or [],
        messages=result.get("messages") or [],
    )


@app.get("/v1/workspace")
def list_workspaces_api(_: str = Depends(require_api_key)) -> dict:
    return {"items": list_workspaces()}


@app.post("/v1/workspace")
def create_workspace_api(
    body: WorkspaceCreateRequest,
    _: str = Depends(require_api_key),
) -> dict:
    ws = create_workspace(body.name, body.owner_email, body.plan_id)
    return {"ok": True, **ws}


@app.get("/v1/workspace/{tenant_id}/usage")
def workspace_usage(
    tenant_id: str,
    _: str = Depends(require_api_key),
) -> dict:
    return get_usage(tenant_id)


@app.patch("/v1/workspace/{tenant_id}/plan")
def workspace_plan(
    tenant_id: str,
    body: WorkspacePlanUpdateRequest,
    _: str = Depends(require_api_key),
) -> dict:
    if not update_workspace_plan(tenant_id, body.plan_id):
        raise HTTPException(status_code=404, detail="Workspace or plan not found.")
    return {"ok": True, "tenant_id": tenant_id, "plan_id": body.plan_id}


@app.post("/v1/feedback")
def submit_feedback(
    body: FeedbackRequest,
    _: str = Depends(require_api_key),
) -> dict:
    ok = log_human_feedback(body.log_timestamp, body.rating)
    if not ok:
        raise HTTPException(status_code=404, detail="Interaction not found.")
    return {"ok": True}


@app.get("/v1/audit/interactions")
def audit_interactions(
    limit: int = 50,
    tenant_id: str = "default",
    _: str = Depends(require_api_key),
) -> dict:
    return {"items": list_interactions(limit=limit, tenant_id=tenant_id)}


@app.get("/v1/audit/events")
def audit_events(
    limit: int = 50,
    tenant_id: str = "default",
    _: str = Depends(require_api_key),
) -> dict:
    return {"items": list_audit_events(limit=limit, tenant_id=tenant_id)}


@app.get("/v1/knowledge")
def knowledge_overview(
    tenant_id: str = "default",
    _: str = Depends(require_api_key),
) -> dict:
    return get_knowledge_overview(tenant_id)


@app.post("/v1/knowledge/upload")
async def knowledge_upload(
    file: UploadFile = File(...),
    tenant_id: str = "default",
    _: str = Depends(require_api_key),
) -> dict:
    content = await file.read()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required.")
    try:
        meta = ingest_uploaded_file(file.filename, content, tenant_id=tenant_id, actor="api")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **meta}


@app.post("/v1/knowledge/pubmed")
def knowledge_pubmed(
    body: PubMedIngestRequest,
    _: str = Depends(require_api_key),
) -> dict:
    return ingest_pubmed(
        body.query,
        max_results=body.max_results,
        tenant_id=body.tenant_id,
        actor="api",
    )


@app.post("/v1/knowledge/openfda")
def knowledge_openfda(
    body: OpenFDAIngestRequest,
    _: str = Depends(require_api_key),
) -> dict:
    return ingest_openfda(body.drug_name, tenant_id=body.tenant_id, actor="api")


@app.delete("/v1/knowledge/{doc_name}")
def knowledge_delete(
    doc_name: str,
    tenant_id: str = "default",
    _: str = Depends(require_api_key),
) -> dict:
    try:
        deleted = remove_document(doc_name, tenant_id=tenant_id, actor="api")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, **deleted}


@app.get("/v1/recollection/summary")
def recollection_summary(
    learner_level: str = "trainee",
    tenant_id: str = "default",
    _: str = Depends(require_api_key),
) -> dict:
    return get_recollection_summary(learner_level, tenant_id)


@app.get("/v1/recollection/queue")
def recollection_queue(
    learner_level: str = "trainee",
    limit: int = 8,
    tenant_id: str = "default",
    _: str = Depends(require_api_key),
) -> dict:
    return {
        "due": get_due_topics(learner_level, limit=limit, tenant_id=tenant_id),
        "queue": get_study_queue(learner_level, limit=limit, tenant_id=tenant_id),
        "recent": get_recent_topics(learner_level, limit=limit, tenant_id=tenant_id),
    }


@app.post("/v1/recollection/review")
def recollection_review(
    body: RecollectionReviewRequest,
    _: str = Depends(require_api_key),
) -> dict:
    ok = record_study_attempt(
        body.topic_id,
        body.self_rating,
        body.recalled_correctly,
        learner_level=body.learner_level,
        tenant_id=body.tenant_id,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Topic not found.")
    return {"ok": True}
