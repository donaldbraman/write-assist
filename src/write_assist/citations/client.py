"""
Client for cite-assist citation search API.
"""

import logging
import os
from typing import Any

import httpx

from write_assist.citations.models import (
    CitationResult,
    CitationSearchRequest,
    CitationSearchResponse,
    CiteAssistUnavailable,
)

logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30.0
DEFAULT_LIBRARY_ID = 5673253


class CiteAssistClient:
    """Async client for cite-assist search API."""

    def __init__(
        self,
        base_url: str | None = None,
        library_id: int | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """Initialize the cite-assist client.

        Args:
            base_url: cite-assist API URL (default: CITE_ASSIST_URL env or localhost:8000)
            library_id: Zotero library ID (default: CITE_ASSIST_LIBRARY_ID env or 5673253)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.environ.get("CITE_ASSIST_URL", DEFAULT_BASE_URL)
        self.library_id = library_id or int(
            os.environ.get("CITE_ASSIST_LIBRARY_ID", str(DEFAULT_LIBRARY_ID))
        )
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "CiteAssistClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search(
        self,
        query: str,
        max_results: int = 10,
        min_score: float = 0.3,
        output_mode: str = "chunks",
        include_summaries: bool = False,
    ) -> CitationSearchResponse:
        """Search for relevant citations.

        Args:
            query: Search query text
            max_results: Maximum number of results
            min_score: Minimum similarity score threshold
            output_mode: Output mode (auto, chunks, summaries, both)
            include_summaries: Include summaries in chunks mode

        Returns:
            CitationSearchResponse with matching citations

        Raises:
            CiteAssistUnavailable: If cite-assist service is not available
        """
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )

        request = CitationSearchRequest(
            query=query,
            library_id=self.library_id,
            max_results=max_results,
            min_score=min_score,
            output_mode=output_mode,
            include_summaries=include_summaries,
        )

        try:
            response = await self._client.post(
                "/api/v3/search",
                json=request.model_dump(),
            )
            response.raise_for_status()
            data = response.json()

            # Parse results
            results = []
            for item in data.get("results", []):
                results.append(
                    CitationResult(
                        id=item.get("id", ""),
                        title=item.get("title", "Unknown"),
                        result_type=item.get("result_type", "chunk"),
                        score=item.get("score", 0.0),
                        chunk_text=item.get("chunk_text"),
                        chunk_index=item.get("chunk_index"),
                        summary=item.get("summary"),
                        chunk_score=item.get("chunk_score"),
                        summary_score=item.get("summary_score"),
                        authors=item.get("authors", []),
                        year=item.get("year"),
                        journal=item.get("journal"),
                        volume=item.get("volume"),
                        pages=item.get("pages"),
                    )
                )

            return CitationSearchResponse(
                results=results,
                total=data.get("total", len(results)),
                query_time_ms=data.get("query_time_ms", 0),
            )

        except httpx.ConnectError as e:
            logger.warning(f"cite-assist unavailable: {e}")
            raise CiteAssistUnavailable(f"Cannot connect to cite-assist at {self.base_url}") from e
        except httpx.TimeoutException as e:
            logger.warning(f"cite-assist timeout: {e}")
            raise CiteAssistUnavailable(
                f"cite-assist request timed out after {self.timeout}s"
            ) from e
        except httpx.HTTPStatusError as e:
            logger.warning(f"cite-assist error: {e}")
            raise CiteAssistUnavailable(
                f"cite-assist returned error: {e.response.status_code}"
            ) from e

    async def search_safe(
        self,
        query: str,
        max_results: int = 10,
        min_score: float = 0.3,
        output_mode: str = "chunks",
    ) -> CitationSearchResponse:
        """Search with graceful fallback on errors.

        Returns empty response if cite-assist is unavailable.
        """
        try:
            return await self.search(
                query=query,
                max_results=max_results,
                min_score=min_score,
                output_mode=output_mode,
            )
        except CiteAssistUnavailable:
            logger.warning("cite-assist unavailable, returning empty results")
            return CitationSearchResponse(results=[], total=0, query_time_ms=0)

    async def health_check(self) -> bool:
        """Check if cite-assist is available.

        Returns:
            True if service is healthy, False otherwise
        """
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=5.0,  # Shorter timeout for health check
            )

        try:
            response = await self._client.get("/health")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
