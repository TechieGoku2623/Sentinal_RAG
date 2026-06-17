"""OpenFDA drug-label fetcher for Sentinel-RAG.

Queries the public openFDA drug-label endpoint and normalizes a label into a
dict the ingest pipeline can consume, including the temporal-recency fields
(``publication_year`` / ``is_recent``) derived from the label's effective date.

openFDA is authoritative for FDA-approved labeling (indications, dosage,
contraindications, warnings), which complements PubMed (primary literature) and
uploaded guidelines. Standard library only — no new dependency. Network access
is optional: failures degrade to a structured "not found" result rather than
raising.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Optional

from src import config
from src.recency_scorer import is_recent

logger = logging.getLogger(__name__)

OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
HTTP_TIMEOUT = config.HTTP_TIMEOUT_SECONDS
TOOL_NAME = config.TOOL_NAME

# Returned when a drug cannot be found (or the API is unavailable).
NOT_FOUND_MESSAGE = "Drug not in FDA database"


def _not_found(drug_name: str) -> dict:
    """Structured 'not found' result (never raises to the caller)."""
    return {
        "found": False,
        "drug_name": drug_name,
        "message": NOT_FOUND_MESSAGE,
    }


def _http_get(url: str, params: dict) -> bytes:
    """GET request returning raw bytes, retrying once on transient failure."""
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    req = urllib.request.Request(full_url, headers={"User-Agent": TOOL_NAME})

    last_exc: Optional[Exception] = None
    for attempt in range(1 + config.HTTP_MAX_RETRIES):
        try:
            with urllib.request.urlopen(  # nosec B310
                req, timeout=HTTP_TIMEOUT
            ) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - retry once, then raise
            last_exc = exc
            logger.warning("openFDA HTTP attempt %d failed (%s); backing off.",
                           attempt + 1, exc)
            time.sleep(1.0)
    raise last_exc  # type: ignore[misc]


def _first(field) -> str:
    """openFDA returns most label fields as lists; take the first as a string."""
    if isinstance(field, list) and field:
        return str(field[0]).strip()
    if isinstance(field, str):
        return field.strip()
    return ""


def _year_from_effective_time(effective_time: str) -> int:
    """Parse a YYYYMMDD effective_time into a year int (0 if unparseable)."""
    if effective_time and effective_time[:4].isdigit():
        return int(effective_time[:4])
    return 0


def fetch_openfda_label(drug_name: str) -> dict:
    """Fetch a drug's FDA label and normalize it.

    Args:
        drug_name: Brand or generic drug name (e.g. "metformin").

    Returns:
        On success, a dict:
            {
                "found": True,
                "drug_name": str,
                "brand_name": str,
                "generic_name": str,
                "indications": str,
                "dosage": str,
                "warnings": str,
                "source": str,                 # e.g. "OpenFDA:metformin"
                "publication_year": int,        # from label effective_time
                "publication_date": str,        # "YYYY-MM-DD"
                "is_recent": bool,
            }
        If the drug is not found or the API is unavailable, a structured
        ``{"found": False, "message": "Drug not in FDA database", ...}``.
    """
    if not drug_name or not drug_name.strip():
        logger.warning("fetch_openfda_label called with empty drug_name.")
        return _not_found(drug_name or "")

    drug = drug_name.strip()
    search = (
        f'openfda.brand_name:"{drug}" OR openfda.generic_name:"{drug}"'
    )
    start = time.perf_counter()

    try:
        raw = _http_get(OPENFDA_LABEL_URL, {
            "search": search,
            "limit": config.OPENFDA_DEFAULT_RESULTS,
        })
        payload = json.loads(raw)
        results = payload.get("results") or []
        if not results:
            logger.info("API call: source=OpenFDA status=not_found drug=%r", drug)
            return _not_found(drug)

        label = results[0]
        openfda = label.get("openfda", {}) or {}
        effective_time = _first(label.get("effective_time", ""))
        year = _year_from_effective_time(effective_time)
        pub_date = (
            f"{effective_time[:4]}-{effective_time[4:6]}-{effective_time[6:8]}"
            if year else ""
        )

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info("API call: source=OpenFDA status=ok drug=%r latency_ms=%d",
                    drug, latency_ms)

        return {
            "found": True,
            "drug_name": drug,
            "brand_name": _first(openfda.get("brand_name")),
            "generic_name": _first(openfda.get("generic_name")),
            "indications": _first(label.get("indications_and_usage")),
            "dosage": _first(label.get("dosage_and_administration")),
            "warnings": _first(label.get("warnings")),
            "source": f"OpenFDA:{drug}",
            "publication_year": year,
            "publication_date": pub_date,
            "is_recent": is_recent(year) if year else False,
        }

    except Exception as exc:  # noqa: BLE001 - fail soft, structured not-found
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error("API call: source=OpenFDA status=error drug=%r "
                     "latency_ms=%d error=%s", drug, latency_ms, exc)
        return _not_found(drug)
