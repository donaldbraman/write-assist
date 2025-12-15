"""
Citation search integration with cite-assist.
"""

from write_assist.citations.client import CiteAssistClient
from write_assist.citations.models import (
    CitationResult,
    CitationSearchRequest,
    CitationSearchResponse,
    CiteAssistError,
    CiteAssistUnavailable,
)

__all__ = [
    "CiteAssistClient",
    "CiteAssistError",
    "CiteAssistUnavailable",
    "CitationResult",
    "CitationSearchRequest",
    "CitationSearchResponse",
]
