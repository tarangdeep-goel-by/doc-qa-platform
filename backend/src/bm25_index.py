"""BM25 keyword-based search index for document retrieval."""

import logging
import re
from rank_bm25 import BM25Okapi
from typing import List, Dict, Any, Optional
import pickle
import os
import numpy as np

logger = logging.getLogger(__name__)

# Common English stop words (avoids NLTK dependency)
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "it", "its", "this", "that", "these", "those", "he", "she", "they",
    "we", "you", "i", "me", "my", "his", "her", "our", "your", "their",
    "what", "which", "who", "whom", "when", "where", "why", "how",
    "not", "no", "nor", "if", "then", "than", "too", "very", "just",
    "about", "above", "after", "again", "all", "also", "am", "any",
    "because", "before", "between", "both", "during", "each", "few",
    "further", "get", "got", "here", "into", "more", "most", "only",
    "other", "out", "over", "own", "same", "so", "some", "such",
    "there", "through", "under", "until", "up", "while",
})

# Regex: split on non-alphanumeric (keeps model numbers like FX5U-32MR/ES intact via hyphens)
_TOKEN_RE = re.compile(r"[a-z0-9][\w\-/]*[a-z0-9]|[a-z0-9]", re.IGNORECASE)


def tokenize(text: str) -> List[str]:
    """Tokenize text with stop word removal and lowercasing."""
    tokens = _TOKEN_RE.findall(text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


class BM25Index:
    """BM25 keyword search index for documents."""

    def __init__(self, cache_dir: str):
        """
        Initialize BM25 index.

        Args:
            cache_dir: Directory to cache the BM25 index
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.index: Optional[BM25Okapi] = None
        self.doc_ids: List[str] = []
        self.point_ids: List[str] = []
        self.chunks: List[Dict[str, Any]] = []

    def build_index(self, chunks: List[Dict[str, Any]], point_ids: List[str] = None):
        """
        Build BM25 index from document chunks.

        Args:
            chunks: List of chunk dictionaries with 'text', 'doc_id', etc.
            point_ids: Qdrant point IDs corresponding to each chunk (for ID-based fusion)
        """
        if not chunks:
            logger.warning("No chunks provided to build BM25 index")
            return

        # Store chunks for later retrieval
        self.chunks = chunks
        self.point_ids = point_ids or [""] * len(chunks)

        # Tokenize with stop word removal and punctuation handling
        tokenized_chunks = [tokenize(chunk["text"]) for chunk in chunks]

        # Build BM25 index
        self.index = BM25Okapi(tokenized_chunks)
        self.doc_ids = [chunk.get("doc_id", "") for chunk in chunks]

        logger.info(f"Built BM25 index with {len(chunks)} chunks")

        # Cache the index
        self._save_cache()

    def search(
        self,
        query: str,
        top_k: int,
        doc_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using BM25.

        Args:
            query: Search query
            top_k: Number of results to return
            doc_ids: Optional list of document IDs to filter results

        Returns:
            List of search results with scores
        """
        if not self.index or not self.chunks:
            return []

        # Tokenize query with same pipeline as indexing
        tokenized_query = tokenize(query)

        # Get BM25 scores for all chunks
        scores = self.index.get_scores(tokenized_query)

        # Filter by doc_ids if specified
        if doc_ids:
            scores = np.array([
                score if self.doc_ids[i] in doc_ids else -1
                for i, score in enumerate(scores)
            ])
        else:
            scores = np.array(scores)

        # Get top k indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        # Build results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include positive scores
                result = {
                    "chunk_index": int(idx),
                    "score": float(scores[idx]),
                    "doc_id": self.doc_ids[idx],
                    "chunk": self.chunks[idx]
                }
                if self.point_ids and idx < len(self.point_ids):
                    result["point_id"] = self.point_ids[idx]
                results.append(result)

        return results

    def _save_cache(self):
        """Save BM25 index to disk cache."""
        cache_file = os.path.join(self.cache_dir, "bm25_index.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'index': self.index,
                    'doc_ids': self.doc_ids,
                    'point_ids': self.point_ids,
                    'chunks': self.chunks
                }, f)
            logger.info(f"Saved BM25 index cache to {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save BM25 cache: {e}")

    def load_cache(self) -> bool:
        """
        Load BM25 index from disk cache.

        Returns:
            True if cache was loaded successfully, False otherwise
        """
        cache_file = os.path.join(self.cache_dir, "bm25_index.pkl")
        if not os.path.exists(cache_file):
            return False

        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                self.index = data['index']
                self.doc_ids = data['doc_ids']
                self.point_ids = data.get('point_ids', [""] * len(self.doc_ids))
                self.chunks = data['chunks']
            logger.info(f"Loaded BM25 index cache from {cache_file}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load BM25 cache: {e}")
            return False

