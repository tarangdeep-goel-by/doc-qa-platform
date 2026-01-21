"""Document processing utilities for extracting text from various formats."""

import os
from typing import Dict, Any, Tuple
import PyPDF2


class DocumentProcessor:
    """Processes documents and extracts text."""

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (extracted_text, metadata)
        """
        text_parts = []
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

                # Extract text from all pages
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_parts.append(page_text)
                    except Exception as e:
                        print(f"Warning: Error extracting text from page {page_num + 1}: {e}")
                        continue

            # Combine all text
            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                raise ValueError("No text could be extracted from PDF")

            return full_text, metadata

        except Exception as e:
            raise ValueError(f"Failed to process PDF: {str(e)}")

    @staticmethod
    def process_document(file_path: str, file_format: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process document and extract text based on format.

        Args:
            file_path: Path to document
            file_format: File format (pdf, docx, html, txt)

        Returns:
            Tuple of (extracted_text, metadata)
        """
        if file_format.lower() == 'pdf':
            return DocumentProcessor.extract_text_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        """Get file size in MB."""
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
