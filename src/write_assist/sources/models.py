"""
Models for source document loading.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Type of source document."""

    LOCAL_FILE = "local_file"
    GOOGLE_DOC = "google_doc"
    URL = "url"


class SourceDocument(BaseModel):
    """A loaded source document with content."""

    source_type: SourceType
    path: str = Field(..., description="Original path or URL")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Extracted text content")
    word_count: int = Field(default=0, description="Approximate word count")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def preview(self) -> str:
        """Get a preview of the content (first 200 chars)."""
        if len(self.content) <= 200:
            return self.content
        return self.content[:200] + "..."


class SourceLoadError(Exception):
    """Error loading a source document."""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message
        super().__init__(f"Failed to load '{path}': {message}")


class GoogleDocsUnavailable(SourceLoadError):
    """Google Docs API is not available."""

    def __init__(self, path: str, reason: str = "Service account not configured"):
        super().__init__(path, f"Google Docs unavailable: {reason}")
