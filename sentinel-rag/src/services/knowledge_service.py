"""Knowledge-base ingest, external sources, and document lifecycle."""

from __future__ import annotations

import logging
import re
from typing import List

from src import config
from src.db.models import DocumentRegistry
from src.db.session import get_session
from src.ingest import (
    chunk_with_parent_links,
    ingest_pubmed_query,
    ingest_openfda_drug,
    load_pdf_bytes,
    load_txt_bytes,
)
from src.retriever import delete_document, get_collection_count, ingest_guidelines, list_documents
from src.services.audit_service import log_audit_event
from src.services.workspace_service import check_document_quota

logger = logging.getLogger(__name__)


def _sanitize_name(name: str) -> str:
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_") or "doc"


def _register_document(
    doc_name: str,
    source: str,
    source_type: str,
    publication_year: int,
    items: List[dict],
    tenant_id: str | None = None,
) -> dict:
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    n_parents = sum(1 for it in items if it["chunk_type"] == "parent")
    n_children = sum(1 for it in items if it["chunk_type"] == "child")

    with get_session() as session:
        existing = (
            session.query(DocumentRegistry)
            .filter_by(tenant_id=tenant, doc_name=doc_name)
            .first()
        )
        if existing:
            existing.source = source
            existing.source_type = source_type
            existing.publication_year = publication_year
            existing.parent_chunks = n_parents
            existing.child_chunks = n_children
        else:
            session.add(
                DocumentRegistry(
                    tenant_id=tenant,
                    doc_name=doc_name,
                    source=source,
                    source_type=source_type,
                    publication_year=publication_year,
                    parent_chunks=n_parents,
                    child_chunks=n_children,
                )
            )

    return {
        "doc_name": doc_name,
        "source": source,
        "source_type": source_type,
        "parent_chunks": n_parents,
        "child_chunks": n_children,
    }


def ingest_uploaded_file(
    filename: str,
    content: bytes,
    tenant_id: str | None = None,
    actor: str = "ui",
) -> dict:
    """Ingest PDF or TXT bytes into ChromaDB."""
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    ok, msg = check_document_quota(tenant)
    if not ok:
        raise ValueError(msg)

    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = load_pdf_bytes(content)
    elif lower.endswith(".txt"):
        text = load_txt_bytes(content)
    else:
        raise ValueError("Only .pdf and .txt files are supported.")

    if not text or not text.strip():
        raise ValueError(f"No extractable text in {filename}.")

    doc_name = _sanitize_name(filename)
    items = chunk_with_parent_links(text, doc_name, source=filename)
    if not items:
        raise ValueError(f"No chunks produced from {filename}.")

    ingest_guidelines(items)
    meta = _register_document(
        doc_name, filename, "local", config.CURRENT_YEAR, items, tenant_id
    )
    log_audit_event(
        "ingest_file",
        f"Ingested {meta['parent_chunks']} parent + {meta['child_chunks']} child from {filename}",
        actor=actor,
        tenant_id=tenant,
    )
    return meta


def ingest_pubmed(
    query: str,
    max_results: int = 10,
    tenant_id: str | None = None,
    actor: str = "api",
) -> dict:
    """Fetch PubMed abstracts and index them."""
    result = ingest_pubmed_query(query, max_results=max_results)
    if result.get("articles", 0) == 0:
        return result

    for doc in result.get("documents", []):
        _register_document(
            doc["doc_name"],
            doc["source"],
            "pubmed",
            doc.get("publication_year", 0),
            [{"chunk_type": "parent"}] * doc["parent_chunks"]
            + [{"chunk_type": "child"}] * doc["child_chunks"],
            tenant_id,
        )

    log_audit_event(
        "ingest_pubmed",
        f"Indexed {result['articles']} PubMed articles for query={query!r}",
        actor=actor,
        tenant_id=tenant_id,
    )
    return result


def ingest_openfda(
    drug_name: str,
    tenant_id: str | None = None,
    actor: str = "api",
) -> dict:
    """Fetch FDA drug label and index it."""
    result = ingest_openfda_drug(drug_name)
    if not result.get("found"):
        return result

    doc = result.get("document", {})
    if doc:
        _register_document(
            doc["doc_name"],
            doc["source"],
            "openfda",
            doc.get("publication_year", 0),
            [{"chunk_type": "parent"}] * doc["parent_chunks"]
            + [{"chunk_type": "child"}] * doc["child_chunks"],
            tenant_id,
        )

    log_audit_event(
        "ingest_openfda",
        f"Indexed OpenFDA label for drug={drug_name!r}",
        actor=actor,
        tenant_id=tenant_id,
    )
    return result


def remove_document(
    doc_name: str,
    tenant_id: str | None = None,
    actor: str = "admin",
) -> dict:
    """Delete a document from ChromaDB and the registry."""
    deleted = delete_document(doc_name)
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    with get_session() as session:
        session.query(DocumentRegistry).filter_by(
            tenant_id=tenant, doc_name=doc_name
        ).delete()

    log_audit_event(
        "delete_document",
        f"Removed doc_name={doc_name!r} ({deleted['parent']} parent, {deleted['child']} child)",
        actor=actor,
        tenant_id=tenant_id,
    )
    return deleted


def get_knowledge_overview(tenant_id: str | None = None) -> dict:
    tenant = tenant_id or config.DEFAULT_TENANT_ID
    counts = get_collection_count()
    try:
        with get_session() as session:
            docs = (
                session.query(DocumentRegistry)
                .filter(DocumentRegistry.tenant_id == tenant)
                .order_by(DocumentRegistry.created_at.desc())
                .all()
            )
            documents = [
                {
                    "doc_name": d.doc_name,
                    "source": d.source,
                    "source_type": d.source_type,
                    "publication_year": d.publication_year,
                    "parent_chunks": d.parent_chunks,
                    "child_chunks": d.child_chunks,
                }
                for d in docs
            ]
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load document registry: %s", exc)
        documents = list_documents()

    return {
        "collection_counts": counts,
        "documents": documents or list_documents(),
    }
