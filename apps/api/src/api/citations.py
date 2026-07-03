"""Citation validation against Semantic Scholar API.

Validates that proposed citations correspond to real published papers.
Uses title-based matching with a configurable similarity threshold.
"""
from difflib import SequenceMatcher
from typing import Any

import httpx

from api.logging import logger
from api.models.interpretation import Citation, VerifiedCitation

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search"
TITLE_MATCH_THRESHOLD = 0.60


def _normalise_title(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for comparison."""
    import re
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _title_similarity(a: str, b: str) -> float:
    """Compute similarity between two title strings (0.0 - 1.0)."""
    return SequenceMatcher(None, _normalise_title(a), _normalise_title(b)).ratio()


def _search_semantic_scholar(title: str) -> list[dict[str, Any]]:
    """Search Semantic Scholar by title query. Returns list of paper matches."""
    params = {
        "query": title,
        "limit": 5,
        "fields": "title,year,authors,venue,externalIds",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(SEMANTIC_SCHOLAR_API, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    except httpx.HTTPError as e:
        logger.warning("semantic_scholar_error", error=str(e))
        return []


def validate_citation(citation: Citation) -> VerifiedCitation:
    """Validate a single citation by searching Semantic Scholar.

    Returns a VerifiedCitation with verified=True if a strong title match is found.
    """
    matches = _search_semantic_scholar(citation.title)

    best_similarity = 0.0
    best_match: dict[str, Any] | None = None

    for paper in matches:
        paper_title = paper.get("title", "")
        sim = _title_similarity(citation.title, paper_title)
        if sim > best_similarity:
            best_similarity = sim
            best_match = paper

    verified = best_similarity >= TITLE_MATCH_THRESHOLD and best_match is not None

    if verified and best_match:
        year = best_match.get("year") or citation.year
        venue = (best_match.get("venue") or "") or citation.venue
        external_ids = best_match.get("externalIds") or {}
        doi = external_ids.get("DOI") or citation.doi_or_url
        return VerifiedCitation(
            authors=citation.authors,
            year=year,
            title=best_match["title"],
            venue=venue,
            doi_or_url=doi,
            verified=True,
        )

    return VerifiedCitation(
        authors=citation.authors,
        year=citation.year,
        title=citation.title,
        venue=citation.venue,
        doi_or_url=citation.doi_or_url,
        verified=False,
    )


def validate_citations(citations: list[Citation]) -> list[VerifiedCitation]:
    """Validate all citations, returning results with verified status."""
    return [validate_citation(c) for c in citations]
