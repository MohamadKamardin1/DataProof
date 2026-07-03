"""Tests for the citation validation service."""

from unittest.mock import patch

from api.citations import validate_citation, validate_citations
from api.models.interpretation import Citation, VerifiedCitation

SAMPLE_CITATION = Citation(
    authors="Chen, J.",
    year=1999,
    title="Rb/Sr ratios in loess-paleosol sequences",
    venue="Earth and Planetary Science Letters",
    doi_or_url="10.1016/S0012-821X(99)00066-5",
)


class TestCitationValidation:
    def test_title_normalisation_strips_punctuation(self):
        from api.citations import _normalise_title

        result = _normalise_title("Rb/Sr ratios in loess-paleosol sequences?")
        assert result == "rbsr ratios in loesspaleosol sequences"

    def test_title_similarity_exact_match(self):
        from api.citations import _title_similarity

        sim = _title_similarity("Hello World", "Hello World")
        assert sim == 1.0

    def test_title_similarity_no_match(self):
        from api.citations import _title_similarity

        sim = _title_similarity("Quantum Physics", "Cooking Pasta")
        assert sim < 0.4

    def test_title_similarity_partial(self):
        from api.citations import _title_similarity

        sim = _title_similarity("Rb/Sr ratios in loess", "Rb/Sr ratios in loess-paleosol sequences")
        assert 0.5 < sim < 1.0

    @patch("api.citations._search_semantic_scholar")
    def test_validate_citation_verified(self, mock_search):
        mock_search.return_value = [
            {
                "title": "Rb/Sr ratios in loess-paleosol sequences",
                "year": 1999,
                "venue": "Earth and Planetary Science Letters",
                "authors": [{"name": "Chen, J."}],
                "externalIds": {"DOI": "10.1016/S0012-821X(99)00066-5"},
            }
        ]

        result = validate_citation(SAMPLE_CITATION)
        assert result.verified is True
        assert result.title == "Rb/Sr ratios in loess-paleosol sequences"

    @patch("api.citations._search_semantic_scholar")
    def test_validate_citation_unverified_wrong_title(self, mock_search):
        mock_search.return_value = [
            {
                "title": "Completely different paper about something else",
                "year": 2020,
                "venue": "Some Journal",
                "authors": [{"name": "Smith, A."}],
                "externalIds": {},
            }
        ]

        result = validate_citation(SAMPLE_CITATION)
        assert result.verified is False

    @patch("api.citations._search_semantic_scholar")
    def test_validate_citation_unverified_no_results(self, mock_search):
        mock_search.return_value = []

        result = validate_citation(SAMPLE_CITATION)
        assert result.verified is False
        # Original values preserved
        assert result.title == SAMPLE_CITATION.title

    def test_validate_citations_batch(self):
        with patch("api.citations._search_semantic_scholar") as mock_search:
            mock_search.return_value = [
                {
                    "title": "Rb/Sr ratios in loess-paleosol sequences",
                    "year": 1999,
                    "venue": "EPSL",
                    "authors": [],
                    "externalIds": {},
                }
            ]

            results = validate_citations([SAMPLE_CITATION, SAMPLE_CITATION])
            assert len(results) == 2
            assert all(isinstance(r, VerifiedCitation) for r in results)
