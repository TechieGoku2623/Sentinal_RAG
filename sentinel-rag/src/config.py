"""Central configuration for Sentinel-RAG.

Single source of truth for every tunable constant in the system — model
settings, confidence thresholds, chunking sizes, retrieval breadth, recency
bands, external-API limits, and on-disk paths. Modules import from here instead
of hard-coding values, so a clinical reviewer can audit and tune the system's
behavior in exactly one place.

This module imports nothing from the rest of the package, so it can be imported
anywhere without risk of a circular import.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Model settings
# ---------------------------------------------------------------------------
LLM_MODEL: str = "llama-3.1-8b-instant"
LLM_TEMPERATURE: float = 0.1   # low: clinical answers must be faithful, not creative
VALIDATOR_TEMPERATURE: float = 0.0  # deterministic fact-checking
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Confidence thresholds (the safety policy of the reflection loop)
# ---------------------------------------------------------------------------
HIGH_CONFIDENCE: float = 0.85   # >= this: well grounded, return it
MED_CONFIDENCE: float = 0.75    # >= this (but < HIGH): retry with more context
MAX_RETRIES: int = 2            # hard cap on re-retrieval loops before flagging

# Confidence penalties applied by the reflection node.
PARTIAL_SUPPORT_PENALTY: float = 0.15  # validator says PARTIALLY_SUPPORTED
OUTDATED_SOURCE_PENALTY: float = 0.10  # oldest source > AGING_YEARS

# Query–corpus alignment: fraction of discriminative query key terms that must
# appear in retrieved docs before we trust a SUPPORTED verdict.
QUERY_ALIGNMENT_MIN: float = 0.34

# Without a corpus anchor term, require this higher alignment before release.
QUERY_ALIGNMENT_STRICT: float = 0.67

# Target protocol decision accuracy on the eval harness (in-scope pass + OOS flag).
PROTOCOL_ACCURACY_TARGET: float = 0.99

# Categories covered by the bundled sample guideline (eval in-scope set).
CORPUS_CATEGORIES: tuple[str, ...] = ("diabetes",)

# Vocabulary anchors for the ingested diabetes corpus — query + retrieved text must
# share at least one before we treat an answer as in-scope.
CORPUS_ANCHOR_TERMS: tuple[str, ...] = (
    "diabetes", "metformin", "hba1c", "glycemic", "glucose", "insulin",
    "sulfonylurea", "sulfonylureas", "egfr", "mellitus", "glucoflozin",
    "gliptamax", "hypoglycemia", "iodinated", "contrast", "lactic", "acidosis",
)

# Topic terms that indicate a question is outside the diabetes corpus when absent
# from retrieved guideline text.
OUT_OF_SCOPE_SIGNATURE_TERMS: tuple[str, ...] = (
    "naloxone", "opioid", "overdose", "fentanyl", "syringe",
    "hypertension", "lisinopril", "hydrochlorothiazide", "thiazide",
    "warfarin", "nsaid", "nsaids", "ssri", "maoi", "grapefruit", "statins",
    "spironolactone", "resistant", "cpr", "anaphylaxis", "epinephrine",
    "metoprolol", "hyperkalemia", "serotonin", "syndrome", "bleeding",
)

# ---------------------------------------------------------------------------
# Conversational memory
# ---------------------------------------------------------------------------
MAX_HISTORY_MESSAGES: int = 6   # keep last 3 user/assistant turns
HISTORY_WINDOW: int = 3         # turns surfaced into the prompt

# ---------------------------------------------------------------------------
# Chunking (parent-child)
# ---------------------------------------------------------------------------
CHILD_CHUNK_SIZE: int = 100
CHILD_OVERLAP: int = 20
PARENT_CHUNK_SIZE: int = 500
PARENT_OVERLAP: int = 50

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
DEFAULT_RESULTS: int = 5    # child chunks searched normally
EXPANDED_RESULTS: int = 10  # child chunks searched on a retry

# ---------------------------------------------------------------------------
# Recency
# ---------------------------------------------------------------------------
CURRENT_YEAR: int = 2025
RECENT_YEARS: int = 3   # <= this many years old counts as "recent"
AGING_YEARS: int = 5    # older than this triggers the outdated warning/penalty

# ---------------------------------------------------------------------------
# External APIs
# ---------------------------------------------------------------------------
# NCBI E-utilities asks for <= 3 requests/sec without an API key; 0.34s between
# calls keeps us safely under that limit.
PUBMED_RATE_LIMIT_SECONDS: float = 0.34
PUBMED_DEFAULT_RESULTS: int = 50
OPENFDA_DEFAULT_RESULTS: int = 1
HTTP_TIMEOUT_SECONDS: int = 15
HTTP_MAX_RETRIES: int = 1  # retry once on transient failure, then degrade

# ---------------------------------------------------------------------------
# Storage paths
# ---------------------------------------------------------------------------
CHROMA_PATH: str = "./chroma_db"
CHILD_COLLECTION_NAME: str = "clinical_guidelines_child"
PARENT_COLLECTION_NAME: str = "clinical_guidelines_parent"

GUIDELINES_DIR: str = "data/guidelines"
FEEDBACK_FILE: str = "data/feedback/confidence_log.csv"
DATABASE_URL: str = "sqlite:///./data/sentinel.db"

# ---------------------------------------------------------------------------
# API / platform
# ---------------------------------------------------------------------------
API_HOST: str = "0.0.0.0"
API_PORT: int = 8000
API_KEY: str = ""  # set SENTINEL_API_KEY in .env; empty = auth disabled (dev only)
DEFAULT_TENANT_ID: str = "default"
CORS_ORIGINS: str = "http://localhost:8501,http://localhost:3000"

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
TOOL_NAME: str = "sentinel-rag"
LANGCHAIN_PROJECT_DEFAULT: str = "sentinel-rag-clinical"
