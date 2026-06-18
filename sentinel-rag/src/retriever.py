"""Vector store layer for Sentinel-RAG.

This module owns ALL ChromaDB operations: client/collection lifecycle,
embedding, ingestion, and retrieval of clinical guideline chunks.

------------------------------------------------------------------------------
WHY CHROMADB (LOCAL) INSTEAD OF PINECONE FOR THIS PROJECT
------------------------------------------------------------------------------
Sentinel-RAG indexes *clinical* guideline material, so data residency and
privacy are first-order concerns, not afterthoughts:

1. Data stays on-premise. ChromaDB's PersistentClient writes embeddings and
   documents to a local directory (./chroma_db). Nothing about the source
   guidelines ever leaves the machine/VPC. Pinecone is a managed SaaS vector
   DB: every vector and its metadata is transmitted to and stored on a
   third-party's infrastructure. For PHI-adjacent or institution-restricted
   clinical content, sending it to an external service creates a HIPAA Business
   Associate Agreement (BAA) obligation and a broader attack/audit surface.

2. No network egress, no third-party trust boundary. Local retrieval means we
   are not depending on an external provider's uptime, regional availability,
   or access controls for the knowledge base. This keeps the data-handling
   story simple for compliance review.

3. Cost and reproducibility. A local store has no per-vector or per-query
   billing, and the entire index can be rebuilt deterministically from the
   source documents in data/guidelines/ — useful for audits and CI.

4. Right-sized. A clinical-protocol corpus is typically thousands–hundreds of
   thousands of chunks, well within what an embedded, local vector store
   handles comfortably. We do not need Pinecone's distributed, multi-tenant
   scaling for this workload.

If this system ever needed horizontal scale or multi-region serving, a managed
vector DB could be revisited — but only behind an appropriate BAA and with the
privacy trade-offs above explicitly accepted.
"""

from __future__ import annotations

import logging
import time
from typing import List

import chromadb
from chromadb.utils import embedding_functions

from src import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (see src/config.py for the values + rationale)
# ---------------------------------------------------------------------------
# Local, on-disk persistence directory (gitignored). Relative so it works
# identically on a dev box and inside the Docker container.
CHROMA_PATH = config.CHROMA_PATH

# all-MiniLM-L6-v2 is a small (~80MB), fast, well-benchmarked sentence
# embedding model. It runs locally on CPU, which keeps the privacy guarantees
# above intact (no embedding API calls leave the machine).
EMBEDDING_MODEL = config.EMBEDDING_MODEL

# ---------------------------------------------------------------------------
# Parent-child collections.
#
# WHY TWO COLLECTIONS:
#   Small chunks find the right passage, large chunks provide the clinical
#   context needed for accurate generation. We retrieve against the CHILD
#   collection (small, precise) and then resolve each hit to its PARENT (large,
#   context-rich) for the generation step.
# ---------------------------------------------------------------------------
CHILD_COLLECTION_NAME = config.CHILD_COLLECTION_NAME
PARENT_COLLECTION_NAME = config.PARENT_COLLECTION_NAME

# Retrieval breadth (number of CHILD chunks to search). "Expanded" mode is used
# by the reflection loop to gather more context after a low-confidence pass.
TOP_K_NORMAL = config.DEFAULT_RESULTS
TOP_K_EXPANDED = config.EXPANDED_RESULTS


# ---------------------------------------------------------------------------
# Collection / client lifecycle
# ---------------------------------------------------------------------------
def _get_collection(name: str) -> "chromadb.api.models.Collection.Collection":
    """Return a named collection, creating it if needed (local + idempotent)."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Embedding function runs locally — no external embedding API is contacted.
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding_fn,
        # Cosine distance is the standard choice for normalized MiniLM vectors.
        metadata={"hnsw:space": "cosine"},
    )


def get_child_collection() -> "chromadb.api.models.Collection.Collection":
    """Return the CHILD collection (small chunks, precise retrieval targets)."""
    return _get_collection(CHILD_COLLECTION_NAME)


def get_parent_collection() -> "chromadb.api.models.Collection.Collection":
    """Return the PARENT collection (large chunks, rich generation context)."""
    return _get_collection(PARENT_COLLECTION_NAME)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def retrieve_with_metadata(query: str, expanded: bool = False) -> List[dict]:
    """Retrieve PARENT chunks with their provenance metadata.

    Search the CHILD collection for the most relevant small chunks (precise
    retrieval), read each hit's ``parent_id``, then fetch the corresponding
    PARENT chunks (rich context) along with their stored metadata. The metadata
    (``source``, ``publication_year``, ``doc_name``) lets the agent apply
    temporal-recency scoring and surface dated source citations.

    Args:
        query: Natural-language clinical question.
        expanded: When True, search TOP_K_EXPANDED (10) child chunks instead of
            TOP_K_NORMAL (5) — used by the reflection loop on a retry.

    Returns:
        A list of records (most relevant first, de-duplicated by parent), each:
            {"text": str, "metadata": {"source", "publication_year",
             "doc_name", "chunk_type", ...}}.
        Returns an empty list if nothing is ingested or on error.
    """
    n_results = TOP_K_EXPANDED if expanded else TOP_K_NORMAL

    if not query or not query.strip():
        logger.warning("retrieve_with_metadata called with empty query.")
        return []

    start = time.perf_counter()
    try:
        from src.services.retrieval_cache import get_retrieval, set_retrieval

        cached = get_retrieval(query, expanded)
        if cached is not None:
            logger.info("Retrieval cache hit (query=%r, expanded=%s).", query[:60], expanded)
            return cached

        child = get_child_collection()

        # Nothing ingested yet — let the agent/UI show "no guidelines loaded".
        if child.count() == 0:
            logger.info("Retrieval skipped: collection empty (query=%r).", query)
            return []

        # Never request more results than exist, or Chroma will warn/clamp.
        n_results = min(n_results, child.count())

        results = child.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas"],
        )

        child_metas = (results.get("metadatas") or [[]])[0]
        child_docs = (results.get("documents") or [[]])[0]

        # Collect distinct parent ids in best-match order.
        parent_ids: List[str] = []
        for md in child_metas:
            pid = (md or {}).get("parent_id")
            if pid and pid not in parent_ids:
                parent_ids.append(pid)

        # No linkage metadata (e.g. legacy data) — fall back to child records.
        if not parent_ids:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.info("Retrieval (no parent links): query=%r num_results=%d "
                        "latency_ms=%d", query, len(child_docs), latency_ms)
            return [
                {"text": doc,
                 "metadata": child_metas[i] if i < len(child_metas) else {}}
                for i, doc in enumerate(child_docs)
            ]

        parent = get_parent_collection()
        fetched = parent.get(ids=parent_ids, include=["documents", "metadatas"])
        f_ids = fetched.get("ids", [])
        f_docs = fetched.get("documents", [])
        f_metas = fetched.get("metadatas", []) or [{} for _ in f_ids]
        id_to_doc = dict(zip(f_ids, f_docs))
        id_to_meta = dict(zip(f_ids, f_metas))

        # Preserve best-match order; fall back to the child record if a parent
        # is somehow missing, so we never drop relevant context silently.
        records: List[dict] = []
        for i, pid in enumerate(parent_ids):
            doc = id_to_doc.get(pid)
            if doc:
                records.append({"text": doc, "metadata": id_to_meta.get(pid, {})})
            elif i < len(child_docs):
                meta = child_metas[i] if i < len(child_metas) else {}
                records.append({"text": child_docs[i], "metadata": meta})

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info("Retrieval: query=%r num_results=%d latency_ms=%d",
                    query, len(records), latency_ms)
        set_retrieval(query, expanded, records)
        return records

    except Exception as exc:  # noqa: BLE001 - surface a helpful message
        logger.error(
            "Failed to retrieve guidelines from ChromaDB. Query=%r Error=%s. "
            "Hint: ensure documents have been ingested (run `python -m "
            "src.ingest`) and that the ./chroma_db directory is writable.",
            query,
            exc,
        )
        return []


def retrieve_guidelines(query: str, expanded: bool = False) -> List[str]:
    """Retrieve guideline PARENT chunk texts (most relevant first).

    Thin wrapper over ``retrieve_with_metadata`` for callers that only need the
    text (e.g. confidence scoring). Returns [] if nothing is ingested or on
    error.
    """
    return [r["text"] for r in retrieve_with_metadata(query, expanded=expanded)]


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
def _provenance(chunk: dict) -> dict:
    """Common provenance metadata stored on every chunk.

    ChromaDB metadata values must be scalars, so publication_year is coerced to
    int (defaulting to 0 = unknown, which recency scoring treats as outdated).
    """
    try:
        year = int(chunk.get("publication_year", 0) or 0)
    except (TypeError, ValueError):
        year = 0
    return {
        "source": str(chunk.get("source", "")),
        "publication_year": year,
        "doc_name": str(chunk.get("doc_name", "")),
    }


def _parent_metadata(chunk: dict) -> dict:
    """Metadata for a PARENT chunk: provenance + chunk_type."""
    md = _provenance(chunk)
    md["chunk_type"] = "parent"
    return md


def _child_metadata(chunk: dict) -> dict:
    """Metadata for a CHILD chunk: provenance + chunk_type + parent linkage."""
    md = _provenance(chunk)
    md["chunk_type"] = "child"
    md["parent_id"] = str(chunk.get("parent_id", ""))
    return md


def ingest_guidelines(chunks: List[dict]) -> None:
    """Upsert parent and child chunks into their respective collections.

    Args:
        chunks: A flat list of chunk dicts as produced by
            ``ingest.chunk_with_parent_links``. Each dict has:
            ``{"text", "id", "parent_id", "chunk_type", "doc_name"}``.
            Parents go to the parent collection; children go to the child
            collection with their ``parent_id`` stored as metadata so retrieval
            can resolve a child back to its parent. Uses upsert + stable IDs so
            re-ingestion is idempotent.
    """
    if not chunks:
        logger.warning("No documents to ingest (empty input).")
        return

    parents = [c for c in chunks if c.get("chunk_type") == "parent"]
    children = [c for c in chunks if c.get("chunk_type") == "child"]
    source = next((c.get("source", "") for c in chunks if c.get("source")), "")
    start = time.perf_counter()

    try:
        if parents:
            pcol = get_parent_collection()
            pcol.upsert(
                documents=[c["text"] for c in parents],
                ids=[c["id"] for c in parents],
                metadatas=[_parent_metadata(c) for c in parents],
            )
        if children:
            ccol = get_child_collection()
            ccol.upsert(
                documents=[c["text"] for c in children],
                ids=[c["id"] for c in children],
                metadatas=[_child_metadata(c) for c in children],
            )

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info("Ingestion: source=%r chunk_count=%d (%d parent + %d child) "
                    "latency_ms=%d", source, len(chunks), len(parents),
                    len(children), latency_ms)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to ingest documents into ChromaDB "
                     "(source=%r): %s", source, exc)
        raise


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------
def get_collection_count() -> dict:
    """Return chunk counts for both collections.

    Returns a dict ``{"parent": int, "child": int}``. Used by the Streamlit UI
    to show how many guideline chunks are loaded. Returns zeros on any error so
    the UI can render a safe default.
    """
    try:
        return {
            "parent": get_parent_collection().count(),
            "child": get_child_collection().count(),
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not read collection counts: %s", exc)
        return {"parent": 0, "child": 0}


def list_documents() -> List[dict]:
    """Summarize ingested documents from Chroma parent metadata."""
    try:
        parent = get_parent_collection()
        if parent.count() == 0:
            return []

        fetched = parent.get(include=["metadatas"])
        metas = fetched.get("metadatas") or []
        by_doc: dict[str, dict] = {}
        for md in metas:
            md = md or {}
            name = str(md.get("doc_name") or "unknown")
            if name not in by_doc:
                by_doc[name] = {
                    "doc_name": name,
                    "source": str(md.get("source") or ""),
                    "source_type": "chromadb",
                    "publication_year": int(md.get("publication_year") or 0),
                    "parent_chunks": 0,
                    "child_chunks": 0,
                }
            by_doc[name]["parent_chunks"] += 1

        child = get_child_collection()
        if child.count() > 0:
            child_metas = (child.get(include=["metadatas"]).get("metadatas")) or []
            for md in child_metas:
                md = md or {}
                name = str(md.get("doc_name") or "unknown")
                if name in by_doc:
                    by_doc[name]["child_chunks"] += 1

        return sorted(by_doc.values(), key=lambda d: d["doc_name"])
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not list documents: %s", exc)
        return []


def delete_document(doc_name: str) -> dict:
    """Remove all parent and child chunks for a document."""
    deleted = {"parent": 0, "child": 0, "doc_name": doc_name}
    try:
        for collection_fn, key in (
            (get_parent_collection, "parent"),
            (get_child_collection, "child"),
        ):
            col = collection_fn()
            hits = col.get(where={"doc_name": doc_name}, include=[])
            ids = hits.get("ids") or []
            if ids:
                col.delete(ids=ids)
                deleted[key] = len(ids)
        logger.info("Deleted document %r: %s", doc_name, deleted)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to delete document %r: %s", doc_name, exc)
        raise
    return deleted
