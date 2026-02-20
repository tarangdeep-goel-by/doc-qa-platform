"""Tests for Embedder with mocked APIs."""

import sys
import numpy as np
import pytest
from unittest.mock import patch, MagicMock


def _make_gemini_embedder():
    """Create an Embedder in Gemini mode with mocked genai."""
    mock_genai = MagicMock()
    with patch.dict(sys.modules, {"google": MagicMock(), "google.genai": mock_genai}):
        from src.embedder import Embedder
        embedder = Embedder(
            model_name="gemini-embedding-001",
            gemini_api_key="test-key",
            output_dimensionality=768,
        )
    return embedder


class TestEmbedderInit:
    """Test Embedder initialization."""

    def test_gemini_mode(self):
        mock_genai = MagicMock()
        with patch.dict(sys.modules, {"google": MagicMock(), "google.genai": mock_genai}):
            from src.embedder import Embedder
            embedder = Embedder(
                model_name="gemini-embedding-001",
                gemini_api_key="test-key",
                output_dimensionality=768,
            )
            assert embedder.use_gemini is True
            assert embedder.embedding_dim == 768

    def test_no_api_key_raises(self):
        mock_genai = MagicMock()
        with patch.dict(sys.modules, {"google": MagicMock(), "google.genai": mock_genai}):
            from src.embedder import Embedder
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                Embedder(model_name="gemini-embedding-001", gemini_api_key=None)

    def test_local_mode(self):
        mock_st_class = MagicMock()
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st_class.return_value = mock_model

        mock_st_module = MagicMock()
        mock_st_module.SentenceTransformer = mock_st_class

        with patch.dict(sys.modules, {"sentence_transformers": mock_st_module}):
            from src.embedder import Embedder
            embedder = Embedder(model_name="all-MiniLM-L6-v2")
            assert embedder.use_gemini is False
            assert embedder.embedding_dim == 384


class TestEmbedTexts:
    """Test embed_texts()."""

    def test_empty_list(self):
        embedder = _make_gemini_embedder()
        result = embedder.embed_texts([])
        assert len(result) == 0

    def test_single_batch(self):
        embedder = _make_gemini_embedder()

        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding]

        with patch("src.embedder.gemini_retry", return_value=mock_response):
            result = embedder.embed_texts(["hello"])
        assert result.shape == (1, 3)

    def test_multi_batch(self):
        embedder = _make_gemini_embedder()

        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2]
        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding] * 100

        with patch("src.embedder.gemini_retry", return_value=mock_response) as mock_retry:
            # 150 texts → 2 batches (100 per batch)
            embedder.embed_texts(["text"] * 150)
        assert mock_retry.call_count == 2

    def test_local_mode(self):
        mock_st_class = MagicMock()
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_st_class.return_value = mock_model
        mock_st_module = MagicMock()
        mock_st_module.SentenceTransformer = mock_st_class

        with patch.dict(sys.modules, {"sentence_transformers": mock_st_module}):
            from src.embedder import Embedder
            embedder = Embedder(model_name="all-MiniLM-L6-v2")
            result = embedder.embed_texts(["hello"])
        mock_model.encode.assert_called_once()
        assert result.shape == (1, 3)


class TestEmbedText:
    """Test embed_text() single text."""

    def test_single_text(self):
        embedder = _make_gemini_embedder()

        mock_embedding = MagicMock()
        mock_embedding.values = [0.1, 0.2, 0.3]
        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding]

        with patch("src.embedder.gemini_retry", return_value=mock_response):
            result = embedder.embed_text("hello")
        assert len(result) == 3


class TestGetEmbeddingDimension:
    """Test get_embedding_dimension()."""

    def test_dimension(self):
        mock_genai = MagicMock()
        with patch.dict(sys.modules, {"google": MagicMock(), "google.genai": mock_genai}):
            from src.embedder import Embedder
            embedder = Embedder(
                model_name="gemini-embedding-001",
                gemini_api_key="key",
                output_dimensionality=512,
            )
            assert embedder.get_embedding_dimension() == 512
