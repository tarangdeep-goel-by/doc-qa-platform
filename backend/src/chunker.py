"""Text chunking utilities for splitting documents into semantic chunks."""

import re
from typing import List


class TextChunker:
    """Chunks text into overlapping segments for better retrieval."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize chunker.

        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks with smart boundaries.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        # Clean text: normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        prev_start = -1

        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size

            # If this is the last chunk, take everything
            if end >= len(text):
                chunks.append(text[start:].strip())
                break

            # Try to find a good breaking point (paragraph, sentence, or word boundary)
            chunk_end = self._find_break_point(text, start, end)

            # Extract chunk
            chunk = text[start:chunk_end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position forward, accounting for overlap
            new_start = chunk_end - self.chunk_overlap

            # Ensure we make progress (avoid infinite loop)
            if new_start <= prev_start:
                new_start = chunk_end

            prev_start = start
            start = new_start

        return chunks

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """
        Find a smart breaking point near the target end position.

        Preference order:
        1. Paragraph break (\n\n)
        2. Sentence end (. ! ?)
        3. Word boundary (space)
        4. Character boundary (fallback)

        Args:
            text: Full text
            start: Start position
            end: Target end position

        Returns:
            Actual break position
        """
        # Search window: look back up to 100 chars from target end
        search_start = max(start, end - 100)
        search_text = text[search_start:end]

        # Try to find paragraph break
        paragraph_breaks = [m.end() for m in re.finditer(r'\n\s*\n', search_text)]
        if paragraph_breaks:
            return search_start + paragraph_breaks[-1]

        # Try to find sentence end
        sentence_ends = [m.end() for m in re.finditer(r'[.!?]\s+', search_text)]
        if sentence_ends:
            return search_start + sentence_ends[-1]

        # Try to find word boundary
        word_boundaries = [m.end() for m in re.finditer(r'\s+', search_text)]
        if word_boundaries:
            return search_start + word_boundaries[-1]

        # Fallback: use target end
        return end
