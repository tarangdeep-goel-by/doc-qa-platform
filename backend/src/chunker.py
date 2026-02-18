"""Text chunking utilities for splitting documents into semantic chunks."""

import re
from typing import List, Dict, Any

from src.structure_detector import detect_blocks, find_headers


class TextChunker:
    """Chunks text into overlapping segments for better retrieval.

    Supports two modes:
    - Structure-aware (default): detects tables, lists, headers and avoids
      splitting inside structural blocks. Uses adaptive chunk sizes.
    - Fixed-size fallback: simple character-based splitting with overlap.
    """

    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        structure_aware: bool = True,
        min_chunk_size: int = 300,
        max_chunk_size: int = 3000,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.structure_aware = structure_aware
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks, preserving structural blocks."""
        if not text or not text.strip():
            return []

        if self.structure_aware:
            chunks = self._structure_aware_chunk(text)
            if chunks:
                return chunks

        # Fallback: fixed-size chunking (no whitespace collapse)
        return self._fixed_size_chunk(text)

    def _structure_aware_chunk(self, text: str) -> List[str]:
        """Split text respecting structural blocks (tables, lists, headers).

        1. Detect structural blocks in full text.
        2. Build segments: alternating prose gaps and structural blocks.
        3. Split prose gaps at paragraph boundaries, never inside blocks.
        4. Merge small adjacent segments up to max_chunk_size.
        """
        blocks = detect_blocks(text)
        if not blocks:
            return []  # no structure detected, caller falls back to fixed-size

        # Build ordered segments: (start, end, type)
        # Fill gaps between blocks with "prose" segments
        segments = []
        pos = 0
        for bstart, bend, btype in blocks:
            if bstart > pos:
                # Prose gap before this block
                segments.append((pos, bstart, "prose"))
            segments.append((bstart, bend, btype))
            pos = bend
        # Trailing prose after last block
        if pos < len(text):
            segments.append((pos, len(text), "prose"))

        # Split each segment into chunks
        raw_chunks = []
        for seg_start, seg_end, seg_type in segments:
            seg_text = text[seg_start:seg_end]
            if not seg_text.strip():
                continue

            if seg_type == "prose":
                # Split prose at paragraph boundaries
                prose_chunks = self._split_prose(seg_text)
                raw_chunks.extend(prose_chunks)
            elif seg_type == "header":
                # Headers stay standalone (will be merged with next chunk)
                raw_chunks.append(seg_text.strip())
            else:
                # Structural block: keep intact if under max, else split carefully
                if len(seg_text) <= self.max_chunk_size:
                    raw_chunks.append(seg_text.strip())
                else:
                    # Block too large — split at line boundaries
                    raw_chunks.extend(self._split_block_at_lines(seg_text))

        # Merge small chunks (especially headers with next chunk)
        merged = self._merge_small_chunks(raw_chunks)
        return [c for c in merged if c.strip()]

    def _split_prose(self, text: str) -> List[str]:
        """Split prose text at paragraph boundaries, respecting chunk_size."""
        # Split on double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current = []
        current_len = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if current_len + len(para) + 1 > self.chunk_size and current:
                chunks.append('\n\n'.join(current))
                # Overlap: keep last paragraph if it fits
                if len(current) > 1 and len(current[-1]) < self.chunk_overlap:
                    current = [current[-1]]
                    current_len = len(current[0])
                else:
                    current = []
                    current_len = 0

            current.append(para)
            current_len += len(para) + 2  # +2 for \n\n join

        if current:
            chunks.append('\n\n'.join(current))

        # If paragraphs didn't produce good splits, fall back to sentence splitting
        final = []
        for chunk in chunks:
            if len(chunk) > self.max_chunk_size:
                final.extend(self._split_at_sentences(chunk))
            else:
                final.append(chunk)

        return final

    def _split_at_sentences(self, text: str) -> List[str]:
        """Split text at sentence boundaries when paragraph splitting isn't enough."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = []
        current_len = 0

        for sent in sentences:
            if current_len + len(sent) + 1 > self.chunk_size and current:
                chunks.append(' '.join(current))
                current = []
                current_len = 0
            current.append(sent)
            current_len += len(sent) + 1

        if current:
            chunks.append(' '.join(current))

        return chunks

    def _split_block_at_lines(self, text: str) -> List[str]:
        """Split a large structural block at line boundaries."""
        lines = text.split('\n')
        chunks = []
        current = []
        current_len = 0

        for line in lines:
            if current_len + len(line) + 1 > self.chunk_size and current:
                chunks.append('\n'.join(current))
                current = []
                current_len = 0
            current.append(line)
            current_len += len(line) + 1

        if current:
            chunks.append('\n'.join(current))

        return chunks

    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """Merge small adjacent chunks, especially headers with following content."""
        if not chunks:
            return chunks

        merged = []
        i = 0
        while i < len(chunks):
            current = chunks[i]

            # Merge with next if current is too small
            while len(current) < self.min_chunk_size and i + 1 < len(chunks):
                i += 1
                current = current + '\n\n' + chunks[i]

            # Don't exceed max
            if len(current) > self.max_chunk_size:
                # Split at a reasonable point
                sub_chunks = self._split_at_sentences(current)
                merged.extend(sub_chunks)
            else:
                merged.append(current)
            i += 1

        return merged

    def _fixed_size_chunk(self, text: str) -> List[str]:
        """Original fixed-size chunking (no whitespace collapse)."""
        text = text.strip()
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        prev_start = -1

        while start < len(text):
            end = start + self.chunk_size

            if end >= len(text):
                chunks.append(text[start:].strip())
                break

            chunk_end = self._find_break_point(text, start, end)
            chunk = text[start:chunk_end].strip()
            if chunk:
                chunks.append(chunk)

            new_start = chunk_end - self.chunk_overlap
            if new_start <= prev_start:
                new_start = chunk_end

            prev_start = start
            start = new_start

        return chunks

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """Find a smart breaking point near the target end position."""
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

        return end

    def chunk_with_page_tracking(
        self,
        page_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Chunk text while preserving page number and section headers.

        Args:
            page_data: List of dicts with {page_num: int, text: str}

        Returns:
            List of dicts with {text: str, page_num: int, section_title: str}
        """
        chunks = []

        for page_info in page_data:
            page_num = page_info['page_num']
            text = page_info['text']

            # Find headers in this page for section context
            headers = find_headers(text)

            page_chunks = self.chunk_text(text)

            for chunk_text in page_chunks:
                # Find nearest header that precedes this chunk
                chunk_start = text.find(chunk_text[:50])  # approximate position
                section_title = ""
                if headers and chunk_start >= 0:
                    for h_offset, h_text in reversed(headers):
                        if h_offset <= chunk_start:
                            section_title = h_text
                            break

                chunks.append({
                    'text': chunk_text,
                    'page_num': page_num,
                    'section_title': section_title,
                })

        return chunks
