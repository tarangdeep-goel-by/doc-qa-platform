"""BM25 keyword-based search index for document retrieval."""

from rank_bm25 import BM25Okapi
from typing import List, Dict, Any, Optional
import pickle
import os
import numpy as np


class BM25Index:
    """BM25 keyword search index for documents."""

    def __init__(self, cache_dir: str = "data/bm25"):
        """
        Initialize BM25 index.

        Args:
            cache_dir: Directory to cache the BM25 index
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.index: Optional[BM25Okapi] = None
        self.doc_ids: List[str] = []
        self.chunk_indices: List[int] = []
        self.chunks: List[Dict[str, Any]] = []

    def build_index(self, chunks: List[Dict[str, Any]]):
        """
        Build BM25 index from document chunks.

        Args:
            chunks: List of chunk dictionaries with 'text', 'doc_id', etc.
        """
        if not chunks:
            print("Warning: No chunks provided to build BM25 index")
            return

        # Store chunks for later retrieval
        self.chunks = chunks

        # Tokenize all chunks (simple whitespace tokenization)
        tokenized_chunks = [
            chunk["text"].lower().split()
            for chunk in chunks
        ]

        # Build BM25 index
        self.index = BM25Okapi(tokenized_chunks)
        self.doc_ids = [chunk.get("doc_id", "") for chunk in chunks]
        self.chunk_indices = list(range(len(chunks)))

        print(f"Built BM25 index with {len(chunks)} chunks")

        # Cache the index
        self._save_cache()

    def search(
        self,
        query: str,
        top_k: int = 20,
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

        # Tokenize query
        tokenized_query = query.lower().split()

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
                results.append({
                    "chunk_index": int(idx),
                    "score": float(scores[idx]),
                    "doc_id": self.doc_ids[idx],
                    "chunk": self.chunks[idx]
                })

        return results

    def _save_cache(self):
        """Save BM25 index to disk cache."""
        cache_file = os.path.join(self.cache_dir, "bm25_index.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'index': self.index,
                    'doc_ids': self.doc_ids,
                    'chunk_indices': self.chunk_indices,
                    'chunks': self.chunks
                }, f)
            print(f"Saved BM25 index cache to {cache_file}")
        except Exception as e:
            print(f"Warning: Failed to save BM25 cache: {e}")

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
                self.chunk_indices = data['chunk_indices']
                self.chunks = data['chunks']
            print(f"Loaded BM25 index cache from {cache_file}")
            return True
        except Exception as e:
            print(f"Warning: Failed to load BM25 cache: {e}")
            return False

    def clear_cache(self):
        """Clear BM25 index cache from disk."""
        cache_file = os.path.join(self.cache_dir, "bm25_index.pkl")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"Cleared BM25 cache: {cache_file}")
