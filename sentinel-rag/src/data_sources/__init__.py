"""External clinical evidence sources for Sentinel-RAG.

Each module in this package fetches guideline/evidence material from a public
source and normalizes it into a common dict shape the ingest pipeline can
consume (including the temporal-recency fields used by recency_scorer).
"""
