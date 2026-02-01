"""Embedding utilities supporting sentence-transformers (local) and Gemini API."""

import os
from typing import List
import numpy as np


class Embedder:
    """Generates embeddings using either local models or Gemini API."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        gemini_api_key: str = None,
        output_dimensionality: int = 768,
    ):
        """
        Initialize embedder.

        For Gemini models (model_name starts with "gemini-"), uses the API.
        Otherwise, uses sentence-transformers locally.

        Args:
            model_name: Model name. Use "gemini-embedding-001" for Gemini API
                        or a sentence-transformers model name for local.
            gemini_api_key: Required for Gemini models.
            output_dimensionality: Embedding dimension for Gemini (supports MRL).
        """
        self.model_name = model_name
        self.use_gemini = model_name.startswith("gemini-")

        if self.use_gemini:
            from google import genai

            api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise ValueError("GEMINI_API_KEY required for Gemini embeddings")

            self.client = genai.Client(api_key=api_key)
            self.output_dimensionality = output_dimensionality
            self.embedding_dim = output_dimensionality
            self.model = None
            print(f"Using Gemini embeddings: {model_name} (dim={output_dimensionality})")
        else:
            from sentence_transformers import SentenceTransformer

            print(f"Loading embedding model: {model_name}...")
            self.client = None
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            print(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            Numpy array of embeddings
        """
        if not texts:
            return np.array([])

        if self.use_gemini:
            return self._embed_texts_gemini(texts)
        else:
            return self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 10,
                convert_to_numpy=True,
            )

    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Numpy array embedding
        """
        if self.use_gemini:
            result = self._embed_texts_gemini([text])
            return result[0]
        else:
            return self.model.encode(text, convert_to_numpy=True)

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        return self.embedding_dim

    def _embed_texts_gemini(self, texts: List[str]) -> np.ndarray:
        """
        Embed texts using Gemini API with batching.

        Gemini supports up to 250 texts per request.
        """
        all_embeddings = []
        gemini_batch_size = 100  # Conservative batch size

        for i in range(0, len(texts), gemini_batch_size):
            batch = texts[i : i + gemini_batch_size]

            if len(texts) > gemini_batch_size:
                print(
                    f"  Embedding batch {i // gemini_batch_size + 1}/"
                    f"{(len(texts) - 1) // gemini_batch_size + 1} "
                    f"({len(batch)} texts)..."
                )

            response = self.client.models.embed_content(
                model=self.model_name,
                contents=batch,
                config={"output_dimensionality": self.output_dimensionality},
            )

            for embedding in response.embeddings:
                all_embeddings.append(embedding.values)

        return np.array(all_embeddings, dtype=np.float32)
