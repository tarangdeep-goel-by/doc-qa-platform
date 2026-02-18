"""Document processing utilities for extracting text from various formats."""

import os
from typing import Dict, Any, Tuple, List
import PyPDF2

# Optional pdfplumber for table extraction
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class DocumentProcessor:
    """Processes documents and extracts text."""

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extract text from PDF file with page tracking.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (page_data, metadata)
            page_data: List of dicts with {page_num: int, text: str}
            metadata: Dict with PDF metadata
        """
        page_data = []
        metadata = {}

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                # Extract metadata
                metadata['total_pages'] = len(pdf_reader.pages)

                # Try to get PDF metadata
                if pdf_reader.metadata:
                    metadata['author'] = pdf_reader.metadata.get('/Author', '')
                    metadata['title'] = pdf_reader.metadata.get('/Title', '')
                    metadata['subject'] = pdf_reader.metadata.get('/Subject', '')
                    metadata['creator'] = pdf_reader.metadata.get('/Creator', '')

                # Extract text from all pages with page numbers
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            page_data.append({
                                'page_num': page_num + 1,  # 1-indexed
                                'text': page_text
                            })
                    except Exception as e:
                        print(f"Warning: Error extracting text from page {page_num + 1}: {e}")
                        continue

            # Validate we got some text
            if not page_data:
                raise ValueError("No text could be extracted from PDF")

            return page_data, metadata

        except Exception as e:
            raise ValueError(f"Failed to process PDF: {str(e)}")

    @staticmethod
    def extract_text_with_tables(file_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extract text from PDF with table-aware extraction using pdfplumber.

        Tables are converted to markdown format to preserve structure.
        This is particularly useful for technical documents with specifications.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (page_data, metadata)
            page_data: List of dicts with {page_num: int, text: str}
            metadata: Dict with PDF metadata
        """
        if not PDFPLUMBER_AVAILABLE:
            print("Warning: pdfplumber not available, falling back to PyPDF2")
            return DocumentProcessor.extract_text_from_pdf(file_path)

        page_data = []
        metadata = {}

        try:
            with pdfplumber.open(file_path) as pdf:
                metadata['total_pages'] = len(pdf.pages)

                # Try to get PDF metadata
                if pdf.metadata:
                    metadata['author'] = pdf.metadata.get('Author', '')
                    metadata['title'] = pdf.metadata.get('Title', '')
                    metadata['subject'] = pdf.metadata.get('Subject', '')
                    metadata['creator'] = pdf.metadata.get('Creator', '')

                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract tables as markdown
                        tables = page.extract_tables()
                        table_md_parts = []
                        for table in tables:
                            if table:
                                md = DocumentProcessor._table_to_markdown(table)
                                if md:
                                    table_md_parts.append(md)

                        # Extract regular text
                        text = page.extract_text() or ""

                        # Combine text with tables at the end
                        if table_md_parts:
                            combined = text + "\n\n" + "\n\n".join(table_md_parts)
                        else:
                            combined = text

                        if combined.strip():
                            page_data.append({
                                'page_num': page_num,
                                'text': combined
                            })

                    except Exception as e:
                        print(f"Warning: Error extracting from page {page_num}: {e}")
                        continue

            if not page_data:
                raise ValueError("No text could be extracted from PDF")

            return page_data, metadata

        except Exception as e:
            raise ValueError(f"Failed to process PDF with pdfplumber: {str(e)}")

    @staticmethod
    def _table_to_markdown(table: List[List]) -> str:
        """
        Convert a table (list of rows) to markdown format.

        Args:
            table: List of rows, each row is a list of cell values

        Returns:
            Markdown table string
        """
        if not table or not table[0]:
            return ""

        # Clean cells and handle None values
        def clean_cell(cell) -> str:
            if cell is None:
                return ""
            return str(cell).strip().replace("|", "\\|").replace("\n", " ")

        # Build header row
        header = table[0]
        header_cells = [clean_cell(c) for c in header]
        header_row = "| " + " | ".join(header_cells) + " |"

        # Build separator row
        sep_row = "| " + " | ".join(["---"] * len(header)) + " |"

        # Build data rows
        data_rows = []
        for row in table[1:]:
            if row:
                # Pad row if shorter than header
                cells = [clean_cell(c) for c in row]
                while len(cells) < len(header):
                    cells.append("")
                data_rows.append("| " + " | ".join(cells[:len(header)]) + " |")

        return "\n".join([header_row, sep_row] + data_rows)

    @staticmethod
    def process_document(file_path: str, file_format: str, use_pdfplumber: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process document and extract text based on format.

        Args:
            file_path: Path to document
            file_format: File format (pdf, docx, html, txt)
            use_pdfplumber: Whether to use pdfplumber for table-aware extraction

        Returns:
            Tuple of (page_data, metadata)
            page_data: List of dicts with {page_num: int, text: str}
        """
        if file_format.lower() == 'pdf':
            if use_pdfplumber:
                return DocumentProcessor.extract_text_with_tables(file_path)
            return DocumentProcessor.extract_text_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        """Get file size in MB."""
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
