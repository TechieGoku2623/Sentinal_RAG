"""PubMed evidence fetcher for Sentinel-RAG.

Queries the NCBI E-utilities API (esearch -> efetch) and normalizes each article
into a dict the ingest pipeline can consume. As of this change, every record now
also carries temporal-recency metadata so the agent can de-rate and warn on
aging evidence:

    publication_year: int          # e.g. 2023
    publication_date: str          # "YYYY-MM-DD" (best-effort; day may be 01)
    is_recent: bool                # published within the last 3 years

Only the Python standard library is used (urllib + ElementTree) so this module
adds no new dependency. Network access is optional: if NCBI is unreachable the
functions fail soft (log + return []), which keeps the rest of the app working.

NOTE: PubMed is a research index, not a substitute for vetted clinical
guidelines. Recency metadata here flags *when* evidence was published; it does
not assert that newer evidence is clinically superior. Clinicians must still
verify currency against authoritative guidelines.
"""

from __future__ import annotations

import logging
import time
import urllib.parse
import urllib.request
from typing import List, Optional
from xml.etree import ElementTree as ET

from src import config
from src.recency_scorer import CURRENT_YEAR, is_recent

logger = logging.getLogger(__name__)

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SEARCH_URL = f"{EUTILS_BASE}/esearch.fcgi"
FETCH_URL = f"{EUTILS_BASE}/efetch.fcgi"

# Be polite to NCBI: short timeout, identify the tool, rate-limit (see config).
HTTP_TIMEOUT = config.HTTP_TIMEOUT_SECONDS
TOOL_NAME = config.TOOL_NAME
RATE_LIMIT_SECONDS = config.PUBMED_RATE_LIMIT_SECONDS

# Map three-letter month abbreviations (PubMed uses these) to month numbers.
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _http_get(url: str, params: dict) -> bytes:
    """Issue a GET request and return the raw response bytes.

    Retries once after a 1-second pause on a transient failure (covers PubMed
    rate-limit / blips) before propagating the error to the caller.
    """
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"
    req = urllib.request.Request(full_url, headers={"User-Agent": TOOL_NAME})

    last_exc: Exception | None = None
    for attempt in range(1 + config.HTTP_MAX_RETRIES):
        try:
            with urllib.request.urlopen(  # nosec B310
                req, timeout=HTTP_TIMEOUT
            ) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - retry once, then raise
            last_exc = exc
            logger.warning("PubMed HTTP attempt %d failed (%s); backing off.",
                           attempt + 1, exc)
            time.sleep(1.0)
    raise last_exc  # type: ignore[misc]


def _parse_pub_date(article: ET.Element) -> tuple:
    """Extract (year, 'YYYY-MM-DD') from an article's <PubDate>.

    PubMed dates are messy: some have Year/Month/Day, some only a Year, some a
    free-text <MedlineDate> like "2019 Jan-Feb". We extract the best year we can
    and default the month/day to 01 when missing.
    """
    pub_date = article.find(".//JournalIssue/PubDate")
    if pub_date is None:
        return None, None

    year_el = pub_date.find("Year")
    month_el = pub_date.find("Month")
    day_el = pub_date.find("Day")

    year: Optional[int] = None
    month = 1
    day = 1

    if year_el is not None and (year_el.text or "").strip().isdigit():
        year = int(year_el.text.strip())
    else:
        # Fall back to free-text MedlineDate, e.g. "2019 Jan-Feb".
        medline = pub_date.find("MedlineDate")
        if medline is not None and medline.text:
            token = medline.text.strip().split()[0]
            if token[:4].isdigit():
                year = int(token[:4])

    if year is None:
        return None, None

    if month_el is not None and month_el.text:
        m = month_el.text.strip().lower()
        if m.isdigit():
            month = max(1, min(12, int(m)))
        elif m[:3] in _MONTHS:
            month = _MONTHS[m[:3]]

    if day_el is not None and (day_el.text or "").strip().isdigit():
        day = max(1, min(31, int(day_el.text.strip())))

    return year, f"{year:04d}-{month:02d}-{day:02d}"


def _extract_abstract(article: ET.Element) -> str:
    """Join all <AbstractText> segments (some abstracts are structured)."""
    parts = []
    for node in article.findall(".//Abstract/AbstractText"):
        text = "".join(node.itertext()).strip()
        if text:
            label = node.get("Label")
            parts.append(f"{label}: {text}" if label else text)
    return "\n".join(parts)


def _parse_articles(xml_bytes: bytes) -> List[dict]:
    """Parse an efetch PubmedArticleSet into normalized record dicts."""
    records: List[dict] = []
    root = ET.fromstring(xml_bytes)

    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text.strip() if pmid_el is not None and pmid_el.text else ""

        title_el = article.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""

        journal_el = article.find(".//Journal/Title")
        journal = journal_el.text.strip() if journal_el is not None and \
            journal_el.text else ""

        abstract = _extract_abstract(article)
        year, pub_date = _parse_pub_date(article)

        records.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "source": f"PubMed:{pmid}" if pmid else "PubMed",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            # Temporal-recency fields (new):
            "publication_year": year if year else 0,
            "publication_date": pub_date if pub_date else "",
            "is_recent": is_recent(year) if year else False,
        })

    return records


def fetch_pubmed_abstracts(
    query: str,
    max_results: int = config.PUBMED_DEFAULT_RESULTS,
) -> List[dict]:
    """Fetch and normalize PubMed abstracts for a clinical query.

    Args:
        query: Search terms (PubMed query syntax supported).
        max_results: Maximum number of articles to return
            (defaults to ``config.PUBMED_DEFAULT_RESULTS``).

    Returns:
        A list of record dicts, each with:
            pmid, title, abstract, journal, source, url,
            publication_year (int), publication_date ("YYYY-MM-DD"),
            is_recent (bool — published within the last RECENT_YEARS years).
        Returns [] on any error (network, parse, empty result) so callers can
        degrade gracefully.
    """
    import json

    if not query or not query.strip():
        logger.warning("fetch_pubmed_abstracts called with empty query.")
        return []

    start = time.perf_counter()
    try:
        # 1) esearch -> list of PMIDs.
        search_bytes = _http_get(SEARCH_URL, {
            "db": "pubmed",
            "term": query.strip(),
            "retmax": max_results,
            "retmode": "json",
            "tool": TOOL_NAME,
        })

        ids = json.loads(search_bytes).get("esearchresult", {}).get("idlist", [])
        if not ids:
            logger.info("PubMed returned no results for query=%r", query)
            return []

        # Respect NCBI's rate limit between the two calls.
        time.sleep(RATE_LIMIT_SECONDS)

        # 2) efetch -> full article XML for those PMIDs.
        fetch_bytes = _http_get(FETCH_URL, {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
            "tool": TOOL_NAME,
        })

        records = _parse_articles(fetch_bytes)
        recent = sum(1 for r in records if r["is_recent"])
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "API call: source=PubMed status=ok results=%d recent=%d "
            "latency_ms=%d (query=%r, ref_year=%d)",
            len(records), recent, latency_ms, query, CURRENT_YEAR,
        )
        return records

    except Exception as exc:  # noqa: BLE001 - fail soft, never crash the caller
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error("API call: source=PubMed status=error latency_ms=%d "
                     "query=%r error=%s", latency_ms, query, exc)
        return []
