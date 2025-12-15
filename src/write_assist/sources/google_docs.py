"""
Google Docs loading for source documents.
"""

import logging
import os
import re
from typing import Any

from write_assist.sources.models import (
    GoogleDocsUnavailable,
    SourceDocument,
    SourceLoadError,
    SourceType,
)

logger = logging.getLogger(__name__)

# Google Docs URL patterns
GOOGLE_DOC_PATTERNS = [
    # Standard edit/view URLs
    r"https?://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)(?:/.*)?",
    # Mobile URLs
    r"https?://docs\.google\.com/document/u/\d+/d/([a-zA-Z0-9_-]+)(?:/.*)?",
]


def extract_doc_id(url: str) -> str | None:
    """
    Extract Google Doc ID from various URL formats.

    Args:
        url: Google Docs URL

    Returns:
        Document ID or None if not a valid Google Docs URL
    """
    for pattern in GOOGLE_DOC_PATTERNS:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    return None


def is_google_doc_url(url: str) -> bool:
    """Check if a URL is a Google Docs URL."""
    return extract_doc_id(url) is not None


def load_google_doc(url: str, key_path: str | None = None) -> SourceDocument:
    """
    Load a Google Doc as a source document.

    Args:
        url: Google Docs URL
        key_path: Path to service account key file (optional, uses env var if not provided)

    Returns:
        SourceDocument with extracted content

    Raises:
        GoogleDocsUnavailable: If Google Docs API is not available
        SourceLoadError: If document cannot be loaded
    """
    doc_id = extract_doc_id(url)
    if not doc_id:
        raise SourceLoadError(url, "Invalid Google Docs URL")

    # Try to import auth-utils
    try:
        from auth_utils.google import GoogleServiceAccount
    except ImportError as e:
        raise GoogleDocsUnavailable(url, "auth-utils not installed: pip install auth-utils") from e

    # Get key path from env if not provided
    if key_path is None:
        key_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY")

    if not key_path:
        raise GoogleDocsUnavailable(
            url,
            "Service account key not configured. "
            "Set GOOGLE_SERVICE_ACCOUNT_KEY env var or pass key_path.",
        )

    try:
        auth = GoogleServiceAccount(key_path=key_path, scopes=["docs_readonly"])
        docs_service = auth.build_service("docs", "v1")

        # Fetch the document
        doc = docs_service.documents().get(documentId=doc_id).execute()

        # Extract text content
        content = _extract_text_from_doc(doc)
        title = doc.get("title", "Untitled Document")

        return SourceDocument(
            source_type=SourceType.GOOGLE_DOC,
            path=url,
            title=title,
            content=content.strip(),
            word_count=len(content.split()),
            metadata={
                "doc_id": doc_id,
                "revision_id": doc.get("revisionId"),
            },
        )

    except FileNotFoundError as e:
        raise GoogleDocsUnavailable(url, f"Service account key not found: {key_path}") from e
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            raise SourceLoadError(
                url,
                "Document not found. Ensure the document exists and is shared "
                "with the service account email.",
            ) from e
        if "403" in error_msg:
            raise SourceLoadError(
                url,
                "Access denied. Share the document with the service account email.",
            ) from e
        raise SourceLoadError(url, f"Failed to load Google Doc: {e}") from e


def _extract_text_from_doc(doc: dict[str, Any]) -> str:
    """
    Extract plain text from a Google Docs document structure.

    Args:
        doc: Google Docs API document response

    Returns:
        Extracted text content
    """
    content = doc.get("body", {}).get("content", [])
    text_parts = []

    for element in content:
        if "paragraph" in element:
            paragraph_text = _extract_paragraph_text(element["paragraph"])
            if paragraph_text:
                text_parts.append(paragraph_text)
        elif "table" in element:
            table_text = _extract_table_text(element["table"])
            if table_text:
                text_parts.append(table_text)

    return "\n\n".join(text_parts)


def _extract_paragraph_text(paragraph: dict[str, Any]) -> str:
    """Extract text from a paragraph element."""
    elements = paragraph.get("elements", [])
    text_parts = []

    for elem in elements:
        if "textRun" in elem:
            text = elem["textRun"].get("content", "")
            text_parts.append(text)

    return "".join(text_parts).strip()


def _extract_table_text(table: dict[str, Any]) -> str:
    """Extract text from a table element."""
    rows = table.get("tableRows", [])
    row_texts = []

    for row in rows:
        cells = row.get("tableCells", [])
        cell_texts = []

        for cell in cells:
            cell_content = cell.get("content", [])
            cell_text_parts = []

            for element in cell_content:
                if "paragraph" in element:
                    para_text = _extract_paragraph_text(element["paragraph"])
                    if para_text:
                        cell_text_parts.append(para_text)

            cell_texts.append(" ".join(cell_text_parts))

        row_texts.append(" | ".join(cell_texts))

    return "\n".join(row_texts)
