"""
Main source document loader with auto-detection.
"""

import logging
from collections.abc import Callable

from write_assist.sources.google_docs import is_google_doc_url, load_google_doc
from write_assist.sources.local import is_local_path, load_local_file
from write_assist.sources.models import (
    GoogleDocsUnavailable,
    SourceDocument,
    SourceLoadError,
    SourceType,
)

logger = logging.getLogger(__name__)


class SourceLoader:
    """
    Unified source document loader with auto-detection.

    Automatically detects source type from path/URL and loads content.

    Example:
        >>> loader = SourceLoader()
        >>> doc = loader.load("/path/to/file.md")
        >>> doc = loader.load("https://docs.google.com/document/d/abc123/edit")
    """

    def __init__(
        self,
        google_key_path: str | None = None,
        on_error: str = "raise",
    ):
        """
        Initialize the source loader.

        Args:
            google_key_path: Path to Google service account key file
            on_error: Error handling strategy: "raise", "skip", or "warn"
        """
        self.google_key_path = google_key_path
        self.on_error = on_error

    def load(self, path: str) -> SourceDocument:
        """
        Load a source document from a path or URL.

        Auto-detects the source type and uses the appropriate loader.

        Args:
            path: Local file path or URL

        Returns:
            SourceDocument with extracted content

        Raises:
            SourceLoadError: If loading fails and on_error="raise"
        """
        source_type = self.detect_type(path)

        if source_type == SourceType.GOOGLE_DOC:
            return load_google_doc(path, key_path=self.google_key_path)
        elif source_type == SourceType.LOCAL_FILE:
            return load_local_file(path)
        else:
            raise SourceLoadError(path, f"Unsupported source type: {source_type}")

    def load_many(
        self,
        paths: list[str],
        on_progress: Callable[[str, bool], None] | None = None,
    ) -> list[SourceDocument]:
        """
        Load multiple source documents.

        Args:
            paths: List of paths or URLs
            on_progress: Optional callback (path, success) for progress

        Returns:
            List of successfully loaded documents
        """
        documents = []

        for path in paths:
            try:
                doc = self.load(path)
                documents.append(doc)
                if on_progress:
                    on_progress(path, True)

            except SourceLoadError as e:
                if on_progress:
                    on_progress(path, False)

                if self.on_error == "raise":
                    raise
                elif self.on_error == "warn":
                    logger.warning(f"Failed to load source: {e}")
                # "skip" - silently continue

            except GoogleDocsUnavailable as e:
                if on_progress:
                    on_progress(path, False)

                if self.on_error == "raise":
                    raise
                elif self.on_error == "warn":
                    logger.warning(f"Google Docs unavailable: {e}")
                # "skip" - silently continue

        return documents

    @staticmethod
    def detect_type(path: str) -> SourceType:
        """
        Detect the source type from a path or URL.

        Args:
            path: Local file path or URL

        Returns:
            SourceType enum value
        """
        if is_google_doc_url(path):
            return SourceType.GOOGLE_DOC
        elif is_local_path(path):
            return SourceType.LOCAL_FILE
        else:
            return SourceType.URL

    def load_safe(self, path: str) -> SourceDocument | None:
        """
        Load a source document, returning None on error.

        Args:
            path: Local file path or URL

        Returns:
            SourceDocument or None if loading fails
        """
        try:
            return self.load(path)
        except (SourceLoadError, GoogleDocsUnavailable) as e:
            logger.warning(f"Failed to load source: {e}")
            return None
