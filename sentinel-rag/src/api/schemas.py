"""Pydantic request/response models for the Sentinel-RAG API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    chroma_parent_chunks: int = 0
    chroma_child_chunks: int = 0


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    messages: List[dict] = Field(default_factory=list)
    tenant_id: str = "default"


class QueryResponse(BaseModel):
    response: str
    confidence: float
    flagged: bool
    retry_count: int
    validation_verdict: str
    flag_reason: str = ""
    conversation_id: str
    response_time_ms: int
    log_timestamp: str
    sources: List[dict] = Field(default_factory=list)
    messages: List[dict] = Field(default_factory=list)


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    owner_email: str = Field(..., min_length=3)
    plan_id: str = "starter"


class WorkspacePlanUpdateRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)


class FeedbackRequest(BaseModel):
    log_timestamp: str
    rating: int = Field(..., ge=1, le=5)


class PubMedIngestRequest(BaseModel):
    query: str = Field(..., min_length=1)
    max_results: int = Field(default=10, ge=1, le=50)
    tenant_id: str = "default"


class OpenFDAIngestRequest(BaseModel):
    drug_name: str = Field(..., min_length=1)
    tenant_id: str = "default"


class MetricsResponse(BaseModel):
    total_interactions: int
    avg_confidence: float
    flag_rate: float
    avg_human_rating: float
    total_rated: int
    total_audit_events: int
    total_documents: int
    eval_keyword_match_rate: Optional[float] = None
    eval_avg_confidence: Optional[float] = None


class RecollectionReviewRequest(BaseModel):
    topic_id: int
    self_rating: int = Field(..., ge=1, le=5)
    recalled_correctly: bool = False
    learner_level: str = "trainee"
    tenant_id: str = "default"
