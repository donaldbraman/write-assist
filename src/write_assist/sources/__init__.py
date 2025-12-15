"""
Source document loading for local files and Google Docs.
"""

from write_assist.sources.google_docs import extract_doc_id, is_google_doc_url, load_google_doc
from write_assist.sources.loader import SourceLoader
from write_assist.sources.local import is_local_path, load_local_file
from write_assist.sources.models import (
    GoogleDocsUnavailable,
    SourceDocument,
    SourceLoadError,
    SourceType,
)

__all__ = [
    # Main loader
    "SourceLoader",
    # Models
    "SourceDocument",
    "SourceType",
    "SourceLoadError",
    "GoogleDocsUnavailable",
    # Local file loading
    "load_local_file",
    "is_local_path",
    # Google Docs loading
    "load_google_doc",
    "is_google_doc_url",
    "extract_doc_id",
]
