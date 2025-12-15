"""
Pydantic models for cite-assist integration.
"""

from pydantic import BaseModel, Field


class CitationSearchRequest(BaseModel):
    """Request to search the citation database."""

    query: str = Field(..., description="Search query text")
    library_id: int = Field(default=5673253, description="Zotero library ID")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum results to return")
    min_score: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum similarity score")
    output_mode: str = Field(
        default="chunks",
        description="Output mode: auto, chunks, summaries, both",
    )
    include_summaries: bool = Field(default=False, description="Include summaries in chunks mode")


class CitationResult(BaseModel):
    """A single citation result from cite-assist."""

    id: str = Field(..., description="Zotero item key")
    title: str = Field(..., description="Document title")
    result_type: str = Field(..., description="Result type: chunk or summary")
    score: float = Field(..., description="Relevance score (0-1)")
    chunk_text: str | None = Field(default=None, description="Matching text chunk")
    chunk_index: int | None = Field(default=None, description="Index of chunk in document")
    summary: str | None = Field(default=None, description="Document summary")
    chunk_score: float | None = Field(default=None, description="Chunk-specific score")
    summary_score: float | None = Field(default=None, description="Summary-specific score")

    # CSL metadata fields
    authors: list[str] = Field(default_factory=list, description="Author names")
    year: int | None = Field(default=None, description="Publication year")
    journal: str | None = Field(default=None, description="Journal name")
    volume: str | None = Field(default=None, description="Volume number")
    pages: str | None = Field(default=None, description="Page range")

    @property
    def relevant_text(self) -> str:
        """Get the most relevant text (chunk or summary)."""
        return self.chunk_text or self.summary or ""

    def to_bluebook(self) -> str:
        """Format citation in Bluebook style."""
        authors_str = " & ".join(self.authors) if self.authors else "Unknown"
        year_str = f" ({self.year})" if self.year else ""

        if self.journal:
            # Journal article format
            vol_str = f"{self.volume} " if self.volume else ""
            pages_str = f" {self.pages}" if self.pages else ""
            return f"{authors_str}, *{self.title}*, {vol_str}{self.journal}{pages_str}{year_str}."
        else:
            # Book format
            return f"{authors_str}, {self.title.upper()}{year_str}."


class CitationSearchResponse(BaseModel):
    """Response from cite-assist search endpoint."""

    results: list[CitationResult] = Field(default_factory=list)
    total: int = Field(default=0, description="Total matching documents")
    query_time_ms: float = Field(default=0, description="Query execution time in ms")


class CiteAssistError(Exception):
    """Error from cite-assist service."""

    pass


class CiteAssistUnavailable(CiteAssistError):
    """cite-assist service is unavailable."""

    pass
