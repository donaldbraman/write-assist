"""
Tests for cite-assist integration.
"""

import pytest

from write_assist.citations import (
    CitationResult,
    CitationSearchRequest,
    CiteAssistClient,
    CiteAssistUnavailable,
)
from write_assist.citations.models import CiteAssistError


class TestCitationModels:
    """Tests for citation data models."""

    def test_citation_search_request_defaults(self) -> None:
        """Test CitationSearchRequest has sensible defaults."""
        request = CitationSearchRequest(query="test")
        assert request.query == "test"
        assert request.library_id == 5673253
        assert request.max_results == 10
        assert request.min_score == 0.3
        assert request.output_mode == "chunks"

    def test_citation_result_relevant_text(self) -> None:
        """Test CitationResult.relevant_text property."""
        # With chunk text
        result = CitationResult(
            id="abc123",
            title="Test Article",
            result_type="chunk",
            score=0.85,
            chunk_text="This is the chunk text.",
        )
        assert result.relevant_text == "This is the chunk text."

        # With summary
        result2 = CitationResult(
            id="abc123",
            title="Test Article",
            result_type="summary",
            score=0.75,
            summary="This is the summary.",
        )
        assert result2.relevant_text == "This is the summary."

    def test_citation_result_bluebook_journal(self) -> None:
        """Test Bluebook formatting for journal articles."""
        result = CitationResult(
            id="abc123",
            title="The Test Article",
            result_type="chunk",
            score=0.85,
            authors=["John Smith", "Jane Doe"],
            year=2020,
            journal="Harvard Law Review",
            volume="100",
            pages="1-50",
        )
        bluebook = result.to_bluebook()
        assert "John Smith & Jane Doe" in bluebook
        assert "*The Test Article*" in bluebook
        assert "100 Harvard Law Review" in bluebook
        assert "(2020)" in bluebook

    def test_citation_result_bluebook_book(self) -> None:
        """Test Bluebook formatting for books."""
        result = CitationResult(
            id="abc123",
            title="The Test Book",
            result_type="chunk",
            score=0.85,
            authors=["John Smith"],
            year=2020,
        )
        bluebook = result.to_bluebook()
        assert "John Smith" in bluebook
        assert "THE TEST BOOK" in bluebook  # Books are capitalized
        assert "(2020)" in bluebook


class TestCiteAssistClient:
    """Tests for CiteAssistClient."""

    @pytest.fixture
    def client(self) -> CiteAssistClient:
        """Create a test client."""
        return CiteAssistClient(
            base_url="http://localhost:8000",
            library_id=5673253,
            timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_search_unavailable(self, client: CiteAssistClient) -> None:
        """Test search when cite-assist is unavailable."""
        # Without a running cite-assist server, should raise CiteAssistUnavailable
        with pytest.raises(CiteAssistUnavailable):
            await client.search("test query")

    @pytest.mark.asyncio
    async def test_search_safe_fallback(self, client: CiteAssistClient) -> None:
        """Test search_safe returns empty results on failure."""
        response = await client.search_safe("test query")
        assert response.results == []
        assert response.total == 0

    @pytest.mark.asyncio
    async def test_health_check_unavailable(self, client: CiteAssistClient) -> None:
        """Test health check when cite-assist is unavailable."""
        result = await client.health_check()
        assert result is False


class TestCiteAssistExceptions:
    """Tests for cite-assist exceptions."""

    def test_cite_assist_error(self) -> None:
        """Test CiteAssistError."""
        error = CiteAssistError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_cite_assist_unavailable(self) -> None:
        """Test CiteAssistUnavailable."""
        error = CiteAssistUnavailable("Service not running")
        assert str(error) == "Service not running"
        assert isinstance(error, CiteAssistError)
