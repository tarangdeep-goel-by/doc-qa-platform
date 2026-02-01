"""Semantic chunking - splits text at topic boundaries using embedding similarity."""

import re
import numpy as np
from typing import List, Dict, Any, Optional


# Sentence-splitting regex: split on sentence-ending punctuation followed by space/newline.
_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences, filtering out very short fragments."""
    parts = _SENTENCE_RE.split(text)
    return [s.strip() for s in parts if len(s.strip()) > 10]


class SemanticChunker:
    """Chunks text at semantic boundaries using embedding similarity.

    Algorithm (Max-Min inspired):
    1. Split text into sentences
    2. Group sentences into small segments (~200 chars each)
    3. Embed all segments
    4. Compute cosine similarity between consecutive segments
    5. Find breakpoints where similarity drops below threshold
    6. Merge segments between breakpoints into chunks
    7. Apply min/max size constraints
    """

    def __init__(
        self,
        embedder,
        min_chunk_size: int = 500,
        max_chunk_size: int = 4000,
        similarity_percentile: int = 25,
    ):
        """
        Args:
            embedder: Embedder instance for generating segment embeddings
            min_chunk_size: Minimum chunk size in chars (merge if smaller)
            max_chunk_size: Maximum chunk size in chars (split if larger)
            similarity_percentile: Breakpoint threshold as percentile of similarity scores.
                                   Lower = fewer breaks = bigger chunks.
        """
        self.embedder = embedder
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.similarity_percentile = similarity_percentile

    def chunk_with_page_tracking(
        self, page_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Semantic chunking with page number tracking.

        Args:
            page_data: List of {page_num: int, text: str}

        Returns:
            List of {text: str, page_num: int}
        """
        # Build combined text with page boundary tracking
        sentences: List[Dict[str, Any]] = []  # [{text, page_num}]
        for page in page_data:
            page_num = page["page_num"]
            text = page["text"].strip()
            if not text:
                continue
            for sent in _split_sentences(text):
                sentences.append({"text": sent, "page_num": page_num})

        if not sentences:
            return []

        if len(sentences) <= 3:
            # Too few sentences for semantic splitting
            combined = " ".join(s["text"] for s in sentences)
            return [{"text": combined, "page_num": sentences[0]["page_num"]}]

        # Group sentences into segments (~200 chars each for embedding efficiency)
        segments = self._build_segments(sentences)

        if len(segments) <= 2:
            # Not enough segments to find breakpoints
            combined = " ".join(seg["text"] for seg in segments)
            return [{"text": combined, "page_num": segments[0]["page_num"]}]

        # Embed all segments
        segment_texts = [seg["text"] for seg in segments]
        print(f"  Semantic chunking: embedding {len(segment_texts)} segments...")
        embeddings = self.embedder.embed_texts(segment_texts)

        # Compute consecutive cosine similarities
        similarities = self._consecutive_similarities(embeddings)

        # Find breakpoints (low similarity = topic change)
        threshold = np.percentile(similarities, self.similarity_percentile)
        breakpoints = [i for i, sim in enumerate(similarities) if sim < threshold]

        # Merge segments between breakpoints into chunks
        chunks = self._merge_at_breakpoints(segments, breakpoints)

        # Apply size constraints
        chunks = self._enforce_size_constraints(chunks)

        print(
            f"  Semantic chunking: {len(sentences)} sentences -> "
            f"{len(segments)} segments -> {len(chunks)} chunks "
            f"(threshold={threshold:.3f})"
        )
        return chunks

    def _build_segments(
        self, sentences: List[Dict[str, Any]], target_size: int = 200
    ) -> List[Dict[str, Any]]:
        """Group sentences into segments of ~target_size chars."""
        segments = []
        current_texts = []
        current_size = 0
        current_page = sentences[0]["page_num"]

        for sent in sentences:
            current_texts.append(sent["text"])
            current_size += len(sent["text"]) + 1  # +1 for space

            if current_size >= target_size:
                segments.append({
                    "text": " ".join(current_texts),
                    "page_num": current_page,
                })
                current_texts = []
                current_size = 0
                current_page = sent["page_num"]

        # Remaining sentences
        if current_texts:
            segments.append({
                "text": " ".join(current_texts),
                "page_num": current_page,
            })

        return segments

    def _consecutive_similarities(self, embeddings: np.ndarray) -> List[float]:
        """Compute cosine similarity between consecutive embeddings."""
        similarities = []
        for i in range(len(embeddings) - 1):
            a = embeddings[i]
            b = embeddings[i + 1]
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                similarities.append(0.0)
            else:
                similarities.append(float(np.dot(a, b) / (norm_a * norm_b)))
        return similarities

    def _merge_at_breakpoints(
        self,
        segments: List[Dict[str, Any]],
        breakpoints: List[int],
    ) -> List[Dict[str, Any]]:
        """Merge segments between breakpoints into chunks."""
        chunks = []
        break_set = set(breakpoints)
        current_texts = []
        current_page = segments[0]["page_num"]

        for i, seg in enumerate(segments):
            current_texts.append(seg["text"])

            # Split after this segment if it's a breakpoint (or last segment)
            if i in break_set or i == len(segments) - 1:
                chunks.append({
                    "text": " ".join(current_texts),
                    "page_num": current_page,
                })
                current_texts = []
                if i + 1 < len(segments):
                    current_page = segments[i + 1]["page_num"]

        return chunks

    def _enforce_size_constraints(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Split chunks that are too large, merge chunks that are too small."""
        result = []

        for chunk in chunks:
            text = chunk["text"]
            page_num = chunk["page_num"]

            if len(text) > self.max_chunk_size:
                # Split oversized chunk at sentence boundaries
                sentences = _split_sentences(text)
                current = []
                current_len = 0
                for sent in sentences:
                    if current_len + len(sent) > self.max_chunk_size and current:
                        result.append({
                            "text": " ".join(current),
                            "page_num": page_num,
                        })
                        current = []
                        current_len = 0
                    current.append(sent)
                    current_len += len(sent) + 1
                if current:
                    result.append({
                        "text": " ".join(current),
                        "page_num": page_num,
                    })
            else:
                result.append(chunk)

        # Merge tiny chunks with their neighbor
        if len(result) <= 1:
            return result

        merged = [result[0]]
        for chunk in result[1:]:
            if len(merged[-1]["text"]) < self.min_chunk_size:
                # Merge with previous
                merged[-1]["text"] += " " + chunk["text"]
            else:
                merged.append(chunk)

        # Handle case where last chunk is too small
        if len(merged) > 1 and len(merged[-1]["text"]) < self.min_chunk_size:
            merged[-2]["text"] += " " + merged[-1]["text"]
            merged.pop()

        return merged
