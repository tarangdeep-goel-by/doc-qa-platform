"""Tests for multi-format document processing (DOCX, HTML, TXT)."""

import os
import pytest
from src.document_processor import DocumentProcessor


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# --- Fixture file creation helpers ---

def _create_docx(path: str, paragraphs: list[str]):
    """Create a minimal .docx test file."""
    from docx import Document
    doc = Document()
    doc.core_properties.title = "Test DOCX Title"
    doc.core_properties.author = "Test Author"
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(path)


def _create_html(path: str, title: str, body: str):
    """Create a minimal .html test file."""
    html = f"<html><head><title>{title}</title></head><body>{body}</body></html>"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _create_txt(path: str, content: str):
    """Create a minimal .txt test file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# --- DOCX Tests ---

class TestDocxExtraction:
    def test_basic_extraction(self, tmp_path):
        path = str(tmp_path / "test.docx")
        _create_docx(path, ["Hello world", "Second paragraph"])
        page_data, metadata = DocumentProcessor.extract_text_from_docx(path)

        assert len(page_data) >= 1
        assert page_data[0]["page_num"] == 1
        assert "Hello world" in page_data[0]["text"]
        assert "Second paragraph" in page_data[0]["text"]

    def test_metadata_extraction(self, tmp_path):
        path = str(tmp_path / "test.docx")
        _create_docx(path, ["Content"])
        _, metadata = DocumentProcessor.extract_text_from_docx(path)

        assert metadata["title"] == "Test DOCX Title"
        assert metadata["author"] == "Test Author"
        assert "total_pages" in metadata

    def test_pseudo_page_splitting(self, tmp_path):
        """Long documents should be split into pseudo-pages."""
        path = str(tmp_path / "long.docx")
        # Create paragraphs totaling >6000 chars to get at least 2 pages
        paragraphs = ["A" * 500 for _ in range(15)]
        _create_docx(path, paragraphs)
        page_data, metadata = DocumentProcessor.extract_text_from_docx(path)

        assert len(page_data) >= 2
        assert page_data[0]["page_num"] == 1
        assert page_data[1]["page_num"] == 2

    def test_empty_docx_raises(self, tmp_path):
        path = str(tmp_path / "empty.docx")
        _create_docx(path, [])
        with pytest.raises(ValueError, match="No text could be extracted"):
            DocumentProcessor.extract_text_from_docx(path)


# --- HTML Tests ---

class TestHtmlExtraction:
    def test_basic_extraction(self, tmp_path):
        path = str(tmp_path / "test.html")
        _create_html(path, "My Title", "<p>Hello HTML</p><p>Second</p>")
        page_data, metadata = DocumentProcessor.extract_text_from_html(path)

        assert len(page_data) == 1
        assert page_data[0]["page_num"] == 1
        assert "Hello HTML" in page_data[0]["text"]
        assert "Second" in page_data[0]["text"]

    def test_title_metadata(self, tmp_path):
        path = str(tmp_path / "test.html")
        _create_html(path, "My Title", "<p>Content</p>")
        _, metadata = DocumentProcessor.extract_text_from_html(path)

        assert metadata["title"] == "My Title"
        assert metadata["total_pages"] == 1

    def test_strips_tags(self, tmp_path):
        path = str(tmp_path / "test.html")
        _create_html(path, "T", "<b>Bold</b> and <i>italic</i>")
        page_data, _ = DocumentProcessor.extract_text_from_html(path)

        text = page_data[0]["text"]
        assert "<b>" not in text
        assert "<i>" not in text
        assert "Bold" in text
        assert "italic" in text

    def test_empty_html_raises(self, tmp_path):
        path = str(tmp_path / "empty.html")
        with open(path, "w") as f:
            f.write("<html><body></body></html>")
        with pytest.raises(ValueError, match="No text could be extracted"):
            DocumentProcessor.extract_text_from_html(path)


# --- TXT Tests ---

class TestTxtExtraction:
    def test_basic_extraction(self, tmp_path):
        path = str(tmp_path / "test.txt")
        _create_txt(path, "Hello plain text\nLine two")
        page_data, metadata = DocumentProcessor.extract_text_from_txt(path)

        assert len(page_data) == 1
        assert page_data[0]["page_num"] == 1
        assert "Hello plain text" in page_data[0]["text"]
        assert metadata["total_pages"] == 1

    def test_empty_txt_raises(self, tmp_path):
        path = str(tmp_path / "empty.txt")
        _create_txt(path, "")
        with pytest.raises(ValueError, match="No text could be extracted"):
            DocumentProcessor.extract_text_from_txt(path)


# --- process_document dispatch tests ---

class TestProcessDocumentDispatch:
    def test_dispatches_docx(self, tmp_path):
        path = str(tmp_path / "test.docx")
        _create_docx(path, ["Content"])
        page_data, metadata = DocumentProcessor.process_document(path, "docx")
        assert len(page_data) >= 1
        assert "Content" in page_data[0]["text"]

    def test_dispatches_html(self, tmp_path):
        path = str(tmp_path / "test.html")
        _create_html(path, "Title", "<p>Body</p>")
        page_data, _ = DocumentProcessor.process_document(path, "html")
        assert "Body" in page_data[0]["text"]

    def test_dispatches_htm(self, tmp_path):
        path = str(tmp_path / "test.htm")
        _create_html(path, "Title", "<p>Body</p>")
        page_data, _ = DocumentProcessor.process_document(path, "htm")
        assert "Body" in page_data[0]["text"]

    def test_dispatches_txt(self, tmp_path):
        path = str(tmp_path / "test.txt")
        _create_txt(path, "Plain text")
        page_data, _ = DocumentProcessor.process_document(path, "txt")
        assert "Plain text" in page_data[0]["text"]

    def test_dispatches_pdf(self):
        pdf_path = os.path.join(FIXTURES_DIR, "test.pdf")
        if os.path.exists(pdf_path):
            page_data, _ = DocumentProcessor.process_document(pdf_path, "pdf")
            assert len(page_data) >= 1

    def test_unsupported_format_raises(self, tmp_path):
        path = str(tmp_path / "test.xyz")
        with open(path, "w") as f:
            f.write("data")
        with pytest.raises(ValueError, match="Unsupported format"):
            DocumentProcessor.process_document(path, "xyz")

    def test_case_insensitive_format(self, tmp_path):
        path = str(tmp_path / "test.txt")
        _create_txt(path, "Content")
        page_data, _ = DocumentProcessor.process_document(path, "TXT")
        assert len(page_data) >= 1


# --- Return shape validation ---

class TestReturnShape:
    """Verify all extractors return the same (page_data, metadata) shape."""

    def _validate_shape(self, page_data, metadata):
        assert isinstance(page_data, list)
        assert len(page_data) >= 1
        for page in page_data:
            assert "page_num" in page
            assert "text" in page
            assert isinstance(page["page_num"], int)
            assert isinstance(page["text"], str)
        assert isinstance(metadata, dict)
        assert "total_pages" in metadata

    def test_docx_shape(self, tmp_path):
        path = str(tmp_path / "test.docx")
        _create_docx(path, ["Content"])
        self._validate_shape(*DocumentProcessor.extract_text_from_docx(path))

    def test_html_shape(self, tmp_path):
        path = str(tmp_path / "test.html")
        _create_html(path, "T", "<p>Content</p>")
        self._validate_shape(*DocumentProcessor.extract_text_from_html(path))

    def test_txt_shape(self, tmp_path):
        path = str(tmp_path / "test.txt")
        _create_txt(path, "Content")
        self._validate_shape(*DocumentProcessor.extract_text_from_txt(path))
