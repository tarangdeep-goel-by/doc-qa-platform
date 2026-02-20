"""
Pytest configuration and shared fixtures.
"""

import os
import time
import pytest

from src.embedder import Embedder
from src.vector_store import VectorStore


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture(scope="session", autouse=True)
def wait_for_qdrant():
    """Wait for Qdrant to be reachable before any test runs.

    Set SKIP_QDRANT_WAIT=true for unit tests that don't need Qdrant.
    """
    if os.environ.get("SKIP_QDRANT_WAIT", "").lower() in ("true", "1", "yes"):
        print("Skipping Qdrant wait (SKIP_QDRANT_WAIT=true)")
        return

    from qdrant_client import QdrantClient

    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", "6333"))
    max_retries = 30

    for attempt in range(max_retries):
        try:
            client = QdrantClient(host=host, port=port, timeout=5)
            client.get_collections()
            print(f"Qdrant ready at {host}:{port}")
            return
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                pytest.exit(
                    f"Qdrant not reachable at {host}:{port} after {max_retries}s"
                )


@pytest.fixture(scope="session")
def reranker_available():
    """Check once per session if the reranker model can be loaded."""
    try:
        from src.reranker import Reranker
        Reranker(model_name=os.environ.get("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"))
        return True
    except Exception:
        print("WARNING: Reranker model not available, tests will run with use_reranker=False")
        return False


@pytest.fixture
def embedder():
    """Shared Embedder instance — identical across test files."""
    return Embedder(
        model_name=os.environ["EMBEDDING_MODEL"],
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        output_dimensionality=int(os.environ["EMBEDDING_DIM"]),
    )


@pytest.fixture
def vector_store_factory():
    """Factory that creates VectorStore instances with auto-cleanup.

    Usage:
        def test_something(vector_store_factory):
            store = vector_store_factory("test_my_feature")
            # ... use store ...
            # collection is auto-deleted after test
    """
    stores = []

    def _create(collection_name: str):
        store = VectorStore(
            host=os.environ["QDRANT_HOST"],
            port=int(os.environ["QDRANT_PORT"]),
            collection_name=collection_name,
            vector_size=int(os.environ["EMBEDDING_DIM"]),
            bm25_cache_dir=os.environ["BM25_CACHE_DIR"],
        )
        stores.append((store, collection_name))
        return store

    yield _create

    for store, name in stores:
        try:
            store.client.delete_collection(name)
        except Exception:
            pass
