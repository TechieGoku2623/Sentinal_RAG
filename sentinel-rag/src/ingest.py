"""Document ingestion pipeline for Sentinel-RAG.

Reads clinical guideline documents (.txt and .pdf) from ./data/guidelines/,
splits them into overlapping word chunks, and pushes them into the local
ChromaDB vector store via retriever.ingest_guidelines.

Run as a module to (re)build the knowledge base:

    python -m src.ingest
"""

from __future__ import annotations

import io
import logging
import os
import re
from typing import List

from PyPDF2 import PdfReader

from src import config
from src.data_sources.openfda import fetch_openfda_label
from src.data_sources.pubmed import fetch_pubmed_abstracts
from src.recency_scorer import CURRENT_YEAR
from src.retriever import ingest_guidelines

logger = logging.getLogger(__name__)

# Directory holding source guideline documents.
GUIDELINES_DIR = config.GUIDELINES_DIR

# Parent-child chunking parameters (see src/config.py).
#   Parent (large) chunks give the GENERATION model rich context.
#   Child (small) chunks give RETRIEVAL precise, focused targets.
PARENT_CHUNK_SIZE = config.PARENT_CHUNK_SIZE
PARENT_OVERLAP = config.PARENT_OVERLAP
CHILD_CHUNK_SIZE = config.CHILD_CHUNK_SIZE
CHILD_OVERLAP = config.CHILD_OVERLAP


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------
def load_txt_file(filepath: str) -> str:
    """Read a UTF-8 text file and return its contents.

    Uses errors="ignore" so a stray non-UTF-8 byte in a guideline export does
    not abort the whole ingest run.
    """
    with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def load_txt_bytes(content: bytes) -> str:
    """Read UTF-8 text from in-memory bytes (API uploads)."""
    return content.decode("utf-8", errors="ignore")


def load_pdf_bytes(content: bytes) -> str:
    """Extract text from PDF bytes (API uploads)."""
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                logger.warning("Skipping encrypted PDF upload.")
                return ""
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(p for p in pages if p)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read PDF bytes: %s", exc)
        return ""


def load_pdf_file(filepath: str) -> str:
    """Extract text from every page of a PDF using PyPDF2.

    Encrypted PDFs are handled gracefully: we attempt an empty-password
    decrypt, and if that fails we skip the file with a warning rather than
    crashing the ingest run.
    """
    try:
        reader = PdfReader(filepath)

        # Some guideline PDFs are encrypted with an empty owner password. Try a
        # blank-password decrypt before giving up.
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                logger.warning("Skipping encrypted PDF (could not decrypt): %s",
                               os.path.basename(filepath))
                return ""

        pages_text: List[str] = []
        for page in reader.pages:
            extracted = page.extract_text() or ""
            if extracted:
                pages_text.append(extracted)

        return "\n".join(pages_text)

    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read PDF %s: %s", os.path.basename(filepath), exc)
        return ""


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
# WHY PARENT-CHILD CHUNKING MATTERS:
#   Small chunks find the right passage, large chunks provide the clinical
#   context needed for accurate generation. A single chunk size forces a bad
#   trade-off: small chunks retrieve precisely but strip away the surrounding
#   conditions/contraindications the model needs to answer safely, while large
#   chunks carry context but dilute the embedding and hurt retrieval precision.
#   Parent-child decouples the two: we retrieve on small CHILD chunks for
#   precision, then hand the model the larger PARENT chunk for full context.
def _chunk_words(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split ``text`` into overlapping word windows of ``chunk_size``."""
    words = text.split()
    if not words:
        return []

    # Guard against a degenerate config that would cause an infinite loop.
    step = max(chunk_size - overlap, 1)

    chunks: List[str] = []
    for start in range(0, len(words), step):
        window = words[start:start + chunk_size]
        if not window:
            break
        chunks.append(" ".join(window))

        # If this window already reached the end, stop (avoids a trailing
        # duplicate chunk from the overlap step).
        if start + chunk_size >= len(words):
            break

    return chunks


def chunk_text(text: str, mode: str = "child") -> List[str]:
    """Split text into overlapping word-based chunks for the given mode.

    Args:
        text: The source text.
        mode: "child" (100 words / 20 overlap — precise retrieval targets) or
            "parent" (500 words / 50 overlap — rich generation context).

    Returns:
        A list of chunk strings.
    """
    if mode == "child":
        chunk_size, overlap = CHILD_CHUNK_SIZE, CHILD_OVERLAP
    elif mode == "parent":
        chunk_size, overlap = PARENT_CHUNK_SIZE, PARENT_OVERLAP
    else:
        raise ValueError(f"Unknown chunk mode: {mode!r} (use 'child' or 'parent')")

    return _chunk_words(text, chunk_size, overlap)


def _sanitize_doc_name(name: str) -> str:
    """Make a filesystem/ID-safe document name from a filename stem."""
    stem = os.path.splitext(name)[0]
    return re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_") or "doc"


def chunk_with_parent_links(
    text: str,
    doc_name: str,
    source: str = "Local Upload",
    publication_year: int = CURRENT_YEAR,
) -> List[dict]:
    """Build parent chunks and their child chunks with linkage + provenance.

    Each parent (500 words) is further split into children (100 words). Children
    carry their ``parent_id`` so retrieval on children can resolve back to the
    full parent context for generation. Every chunk also carries provenance
    (``source``, ``publication_year``) so the agent can apply temporal-recency
    scoring and warn on aging evidence.

    Args:
        text: The full document text.
        doc_name: Stable, ID-safe document name.
        source: Human-readable provenance label (e.g. "ADA Guidelines",
            "PubMed:38123456"). Defaults to "Local Upload".
        publication_year: Year the source was published. Defaults to the current
            reference year (local files are assumed current unless told
            otherwise); pass the real year for dated/external sources.

    Returns a flat list of dicts, each:
        {
            "text": str,
            "id": str,
            "parent_id": str,        # children -> their parent; parents -> self
            "chunk_type": "parent" | "child",
            "doc_name": str,
            "source": str,
            "publication_year": int,
        }
    """
    items: List[dict] = []
    parents = chunk_text(text, mode="parent")

    for i, parent_text in enumerate(parents):
        parent_id = f"parent_{doc_name}_{i}"
        items.append({
            "text": parent_text,
            "id": parent_id,
            "parent_id": parent_id,   # self-reference keeps the schema uniform
            "chunk_type": "parent",
            "doc_name": doc_name,
            "source": source,
            "publication_year": publication_year,
        })

        for j, child_text in enumerate(chunk_text(parent_text, mode="child")):
            items.append({
                "text": child_text,
                "id": f"child_{doc_name}_{i}_{j}",
                "parent_id": parent_id,
                "chunk_type": "child",
                "doc_name": doc_name,
                "source": source,
                "publication_year": publication_year,
            })

    return items


def _pubmed_record_to_text(record: dict) -> str:
    title = record.get("title", "")
    journal = record.get("journal", "")
    abstract = record.get("abstract", "")
    pmid = record.get("pmid", "")
    parts = [f"Title: {title}"]
    if journal:
        parts.append(f"Journal: {journal}")
    if abstract:
        parts.append(f"Abstract: {abstract}")
    if pmid:
        parts.append(f"PMID: {pmid}")
    return "\n\n".join(parts)


def ingest_pubmed_query(query: str, max_results: int = 10) -> dict:
    """Fetch PubMed articles and ingest them into ChromaDB."""
    records = fetch_pubmed_abstracts(query, max_results=max_results)
    if not records:
        return {"articles": 0, "documents": [], "message": "No PubMed results found."}

    documents = []
    total_items: List[dict] = []

    for record in records:
        text = _pubmed_record_to_text(record)
        if not text.strip():
            continue
        pmid = record.get("pmid") or "unknown"
        doc_name = f"pubmed_{pmid}"
        source = record.get("source") or f"PubMed:{pmid}"
        year = int(record.get("publication_year") or 0)
        items = chunk_with_parent_links(text, doc_name, source=source, publication_year=year)
        total_items.extend(items)
        documents.append({
            "doc_name": doc_name,
            "source": source,
            "publication_year": year,
            "parent_chunks": sum(1 for it in items if it["chunk_type"] == "parent"),
            "child_chunks": sum(1 for it in items if it["chunk_type"] == "child"),
        })

    if total_items:
        ingest_guidelines(total_items)

    return {
        "articles": len(documents),
        "documents": documents,
        "message": f"Ingested {len(documents)} PubMed article(s).",
    }


def ingest_openfda_drug(drug_name: str) -> dict:
    """Fetch an FDA drug label and ingest it into ChromaDB."""
    label = fetch_openfda_label(drug_name)
    if not label.get("found"):
        return {"found": False, "message": label.get("message", "Drug not found.")}

    text = "\n\n".join(
        part for part in [
            f"Drug: {label.get('drug_name', drug_name)}",
            f"Brand: {label.get('brand_name', '')}",
            f"Generic: {label.get('generic_name', '')}",
            f"Indications: {label.get('indications', '')}",
            f"Dosage: {label.get('dosage', '')}",
            f"Warnings: {label.get('warnings', '')}",
        ]
        if part.split(": ", 1)[-1].strip()
    )
    doc_name = f"openfda_{_sanitize_doc_name(drug_name)}"
    source = label.get("source") or f"OpenFDA:{drug_name}"
    year = int(label.get("publication_year") or 0)
    items = chunk_with_parent_links(text, doc_name, source=source, publication_year=year)
    if items:
        ingest_guidelines(items)

    return {
        "found": True,
        "message": f"Ingested FDA label for {drug_name}.",
        "document": {
            "doc_name": doc_name,
            "source": source,
            "publication_year": year,
            "parent_chunks": sum(1 for it in items if it["chunk_type"] == "parent"),
            "child_chunks": sum(1 for it in items if it["chunk_type"] == "child"),
        },
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def ingest_all_guidelines() -> None:
    """Ingest every .txt and .pdf file in the guidelines directory."""
    if not os.path.isdir(GUIDELINES_DIR):
        logger.error(
            "Guidelines directory not found: '%s'. Create it and add .txt or "
            ".pdf clinical guideline files, then re-run `python -m src.ingest`.",
            GUIDELINES_DIR,
        )
        return

    filenames = sorted(
        f for f in os.listdir(GUIDELINES_DIR)
        if f.lower().endswith((".txt", ".pdf"))
    )

    if not filenames:
        logger.warning(
            "No .txt or .pdf files found in '%s'. Add clinical guideline "
            "documents and re-run.",
            GUIDELINES_DIR,
        )
        return

    all_items: List[dict] = []
    files_processed = 0

    for filename in filenames:
        filepath = os.path.join(GUIDELINES_DIR, filename)
        logger.info("Processing: %s", filename)

        try:
            if filename.lower().endswith(".txt"):
                text = load_txt_file(filepath)
            else:
                text = load_pdf_file(filepath)
        except Exception as exc:  # noqa: BLE001 - one bad file shouldn't abort all
            logger.warning("Failed to load %s: %s", filename, exc)
            continue

        if not text or not text.strip():
            logger.warning("No extractable text in %s, skipping.", filename)
            continue

        # Stable doc name -> stable parent/child IDs -> idempotent re-ingestion.
        # Local files have no embedded date, so they default to the current
        # reference year (assumed current). External/dated sources (e.g. PubMed)
        # should be ingested via their own pipeline with the real year.
        doc_name = _sanitize_doc_name(filename)
        items = chunk_with_parent_links(text, doc_name, source=filename)
        if not items:
            logger.warning("No chunks produced from %s, skipping.", filename)
            continue

        all_items.extend(items)
        files_processed += 1
        n_parents = sum(1 for it in items if it["chunk_type"] == "parent")
        n_children = sum(1 for it in items if it["chunk_type"] == "child")
        logger.info("  -> %d parent / %d child chunk(s)", n_parents, n_children)

    if not all_items:
        logger.warning("Nothing to ingest after processing files.")
        return

    try:
        ingest_guidelines(all_items)
    except Exception as exc:  # noqa: BLE001
        logger.error("Ingestion into ChromaDB failed: %s", exc)
        return

    total_parents = sum(1 for it in all_items if it["chunk_type"] == "parent")
    total_children = sum(1 for it in all_items if it["chunk_type"] == "child")
    logger.info("Ingested %d parent + %d child chunks from %d files",
                total_parents, total_children, files_processed)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    ingest_all_guidelines()
