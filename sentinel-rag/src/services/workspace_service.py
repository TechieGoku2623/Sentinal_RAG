"""Workspace / organization layer for SaaS-style multi-tenancy (prototype).

Manages workspaces, subscription plans, and usage quotas. Production replaces
session-based workspace selection with Clerk org JWT claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from src import config
from src.db.models import DocumentRegistry, Interaction, Organization, UsageCounter
from src.db.session import get_session
from src.services.audit_service import get_platform_stats, log_audit_event


@dataclass(frozen=True)
class PlanDefinition:
    id: str
    name: str
    queries_per_month: int
    max_documents: int
    max_seats: int
    price_label: str


PLANS: dict[str, PlanDefinition] = {
    "starter": PlanDefinition(
        id="starter",
        name="Starter",
        queries_per_month=500,
        max_documents=10,
        max_seats=3,
        price_label="Free",
    ),
    "professional": PlanDefinition(
        id="professional",
        name="Professional",
        queries_per_month=5000,
        max_documents=100,
        max_seats=15,
        price_label="$299/mo",
    ),
    "enterprise": PlanDefinition(
        id="enterprise",
        name="Enterprise",
        queries_per_month=999_999,
        max_documents=999_999,
        max_seats=999,
        price_label="Custom",
    ),
}


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def ensure_default_workspace() -> str:
    """Create default org if none exists. Returns tenant_id."""
    with get_session() as session:
        org = session.query(Organization).filter_by(tenant_id=config.DEFAULT_TENANT_ID).first()
        if org:
            return org.tenant_id
        org = Organization(
            tenant_id=config.DEFAULT_TENANT_ID,
            name="Default Clinical Workspace",
            plan_id="starter",
            owner_email="admin@workspace.local",
            onboarding_complete=False,
        )
        session.add(org)
        session.flush()
        tenant_id = org.tenant_id
    log_audit_event(
        "workspace_created",
        f"Default workspace {tenant_id}",
        actor="system",
        tenant_id=tenant_id,
    )
    return tenant_id


def list_workspaces() -> list[dict[str, Any]]:
    ensure_default_workspace()
    with get_session() as session:
        rows = session.query(Organization).order_by(Organization.created_at).all()
        return [
            {
                "tenant_id": r.tenant_id,
                "name": r.name,
                "plan_id": r.plan_id,
                "owner_email": r.owner_email,
            }
            for r in rows
        ]


def create_workspace(name: str, owner_email: str, plan_id: str = "starter") -> dict[str, Any]:
    slug = name.lower().strip().replace(" ", "-")[:48] or "workspace"
    tenant_id = f"{slug}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    plan_id = plan_id if plan_id in PLANS else "starter"
    with get_session() as session:
        org = Organization(
            tenant_id=tenant_id,
            name=name.strip(),
            plan_id=plan_id,
            owner_email=owner_email.strip(),
        )
        session.add(org)
        session.flush()
        result = {
            "tenant_id": org.tenant_id,
            "name": org.name,
            "plan_id": org.plan_id,
            "owner_email": org.owner_email,
        }
    log_audit_event(
        "workspace_created",
        f"Workspace {result['tenant_id']}: {result['name']}",
        actor=owner_email,
        tenant_id=result["tenant_id"],
    )
    return result


def get_workspace(tenant_id: str) -> Organization | None:
    with get_session() as session:
        return session.query(Organization).filter_by(tenant_id=tenant_id).first()


def get_plan(tenant_id: str) -> PlanDefinition:
    with get_session() as session:
        org = session.query(Organization).filter_by(tenant_id=tenant_id).first()
        plan_id = org.plan_id if org else "starter"
    return PLANS.get(plan_id, PLANS["starter"])


def get_usage(tenant_id: str) -> dict[str, Any]:
    """Return current-month usage vs plan limits."""
    plan = get_plan(tenant_id)
    month = _month_key()
    with get_session() as session:
        counter = (
            session.query(UsageCounter)
            .filter_by(tenant_id=tenant_id, month=month)
            .first()
        )
        queries_used = counter.query_count if counter else 0
        doc_count = (
            session.query(func.count(DocumentRegistry.id))
            .filter_by(tenant_id=tenant_id)
            .scalar()
            or 0
        )

    stats = get_platform_stats(tenant_id)
    return {
        "tenant_id": tenant_id,
        "plan": plan.id,
        "plan_name": plan.name,
        "price_label": plan.price_label,
        "queries_used": queries_used,
        "queries_limit": plan.queries_per_month,
        "queries_remaining": max(0, plan.queries_per_month - queries_used),
        "usage_pct": min(1.0, queries_used / plan.queries_per_month) if plan.queries_per_month else 0,
        "documents_used": doc_count,
        "max_documents": plan.max_documents,
        "max_seats": plan.max_seats,
        "total_sessions": stats.get("total_interactions", 0),
        "flag_rate": stats.get("flag_rate", 0.0),
        "avg_confidence": stats.get("avg_confidence", 0.0),
        "month": month,
    }


def check_query_quota(tenant_id: str) -> tuple[bool, str]:
    usage = get_usage(tenant_id)
    if usage["queries_used"] >= usage["queries_limit"]:
        return False, (
            f"Monthly query limit reached ({usage['queries_limit']} on "
            f"{usage['plan_name']} plan). Upgrade to continue."
        )
    return True, ""


def increment_query_usage(tenant_id: str) -> None:
    month = _month_key()
    with get_session() as session:
        counter = (
            session.query(UsageCounter)
            .filter_by(tenant_id=tenant_id, month=month)
            .first()
        )
        if counter:
            counter.query_count += 1
        else:
            session.add(UsageCounter(tenant_id=tenant_id, month=month, query_count=1))


def update_workspace_plan(tenant_id: str, plan_id: str) -> bool:
    if plan_id not in PLANS:
        return False
    with get_session() as session:
        org = session.query(Organization).filter_by(tenant_id=tenant_id).first()
        if not org:
            return False
        org.plan_id = plan_id
    log_audit_event(
        "plan_changed",
        f"{tenant_id} → {plan_id}",
        actor="admin",
        tenant_id=tenant_id,
    )
    return True


def is_onboarding_complete(tenant_id: str) -> bool:
    with get_session() as session:
        org = session.query(Organization).filter_by(tenant_id=tenant_id).first()
        return bool(org and org.onboarding_complete)


def set_onboarding_complete(tenant_id: str, complete: bool = True) -> None:
    with get_session() as session:
        org = session.query(Organization).filter_by(tenant_id=tenant_id).first()
        if org:
            org.onboarding_complete = complete


def check_document_quota(tenant_id: str) -> tuple[bool, str]:
    usage = get_usage(tenant_id)
    if usage["documents_used"] >= usage["max_documents"]:
        return False, (
            f"Document limit reached ({usage['max_documents']} on "
            f"{usage['plan_name']} plan). Upgrade or remove documents to continue."
        )
    return True, ""
