"""
Tests for source document loading.
"""

import tempfile

import pytest

from write_assist.sources import (
    GoogleDocsUnavailable,
    SourceDocument,
    SourceLoader,
    SourceLoadError,
    SourceType,
    extract_doc_id,
    is_google_doc_url,
    is_local_path,
    load_local_file,
)


class TestSourceDocument:
    """Tests for SourceDocument model."""

    def test_preview_short_content(self) -> None:
        """Test preview for short content."""
        doc = SourceDocument(
            source_type=SourceType.LOCAL_FILE,
            path="/test.txt",
            title="Test",
            content="Short content",
            word_count=2,
        )
        assert doc.preview == "Short content"

    def test_preview_long_content(self) -> None:
        """Test preview truncation for long content."""
        doc = SourceDocument(
            source_type=SourceType.LOCAL_FILE,
            path="/test.txt",
            title="Test",
            content="x" * 300,
            word_count=1,
        )
        assert len(doc.preview) == 203  # 200 + "..."
        assert doc.preview.endswith("...")


class TestLocalFileLoading:
    """Tests for local file loading."""

    def test_load_text_file(self) -> None:
        """Test loading a text file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, world!")
            f.flush()

            doc = load_local_file(f.name)

            assert doc.source_type == SourceType.LOCAL_FILE
            assert doc.content == "Hello, world!"
            assert doc.word_count == 2

    def test_load_markdown_file(self) -> None:
        """Test loading a markdown file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Title\n\nSome content here.")
            f.flush()

            doc = load_local_file(f.name)

            assert doc.source_type == SourceType.LOCAL_FILE
            assert "# Title" in doc.content
            assert doc.metadata["extension"] == ".md"

    def test_load_nonexistent_file(self) -> None:
        """Test error on nonexistent file."""
        with pytest.raises(SourceLoadError) as exc_info:
            load_local_file("/nonexistent/file.txt")

        assert "not found" in str(exc_info.value).lower()

    def test_is_local_path(self) -> None:
        """Test local path detection."""
        assert is_local_path("/path/to/file.txt")
        assert is_local_path("./relative/file.md")
        assert is_local_path("file.txt")
        assert not is_local_path("https://example.com")
        assert not is_local_path("http://example.com")


class TestGoogleDocsDetection:
    """Tests for Google Docs URL detection."""

    def test_extract_doc_id_standard(self) -> None:
        """Test doc ID extraction from standard URL."""
        url = "https://docs.google.com/document/d/1abc123def/edit"
        assert extract_doc_id(url) == "1abc123def"

    def test_extract_doc_id_view(self) -> None:
        """Test doc ID extraction from view URL."""
        url = "https://docs.google.com/document/d/xyz789/view"
        assert extract_doc_id(url) == "xyz789"

    def test_extract_doc_id_plain(self) -> None:
        """Test doc ID extraction from plain URL."""
        url = "https://docs.google.com/document/d/abc-123_XYZ"
        assert extract_doc_id(url) == "abc-123_XYZ"

    def test_extract_doc_id_mobile(self) -> None:
        """Test doc ID extraction from mobile URL."""
        url = "https://docs.google.com/document/u/0/d/mobile123/edit"
        assert extract_doc_id(url) == "mobile123"

    def test_extract_doc_id_invalid(self) -> None:
        """Test doc ID extraction from invalid URL."""
        assert extract_doc_id("https://example.com") is None
        assert extract_doc_id("/local/path") is None

    def test_is_google_doc_url(self) -> None:
        """Test Google Docs URL detection."""
        assert is_google_doc_url("https://docs.google.com/document/d/abc/edit")
        assert not is_google_doc_url("https://example.com")
        assert not is_google_doc_url("/local/path")


class TestSourceLoader:
    """Tests for SourceLoader."""

    def test_detect_type_local(self) -> None:
        """Test type detection for local paths."""
        assert SourceLoader.detect_type("/path/to/file.txt") == SourceType.LOCAL_FILE
        assert SourceLoader.detect_type("./file.md") == SourceType.LOCAL_FILE

    def test_detect_type_google_doc(self) -> None:
        """Test type detection for Google Docs URLs."""
        url = "https://docs.google.com/document/d/abc123/edit"
        assert SourceLoader.detect_type(url) == SourceType.GOOGLE_DOC

    def test_load_local_file(self) -> None:
        """Test loading local file through loader."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            f.flush()

            loader = SourceLoader()
            doc = loader.load(f.name)

            assert doc.content == "Test content"

    def test_load_safe_returns_none(self) -> None:
        """Test load_safe returns None on error."""
        loader = SourceLoader()
        result = loader.load_safe("/nonexistent/file.txt")
        assert result is None

    def test_load_many_with_errors(self) -> None:
        """Test load_many continues on errors with warn mode."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Good content")
            f.flush()

            loader = SourceLoader(on_error="warn")
            docs = loader.load_many([f.name, "/nonexistent.txt"])

            # Should only load the valid file
            assert len(docs) == 1
            assert docs[0].content == "Good content"


class TestGoogleDocsLoading:
    """Tests for Google Docs loading (requires auth)."""

    def test_load_without_credentials(self) -> None:
        """Test error when no credentials configured."""
        from write_assist.sources.google_docs import load_google_doc

        with pytest.raises(GoogleDocsUnavailable):
            load_google_doc("https://docs.google.com/document/d/test/edit")
