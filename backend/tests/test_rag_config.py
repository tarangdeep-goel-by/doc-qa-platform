"""Tests for RAGConfig centralized pipeline config."""

import pytest

from src.rag_config import RAGConfig, str_to_bool


class TestStrToBool:
    """Test str_to_bool() helper."""

    @pytest.mark.parametrize("val", ["true", "True", "TRUE", "1", "yes", "Yes"])
    def test_truthy(self, val):
        assert str_to_bool(val) is True

    @pytest.mark.parametrize("val", ["false", "False", "0", "no", "No", "", "random"])
    def test_falsy(self, val):
        assert str_to_bool(val) is False


class TestFromEnv:
    """Test RAGConfig.from_env()."""

    ENV_VARS = {
        "TOP_K_RESULTS": "12",
        "USE_HYBRID_SEARCH": "true",
        "HYBRID_ALPHA": "0.5",
        "USE_RERANKING": "true",
        "USE_QUERY_EXPANSION": "true",
        "QUERY_EXPANSION_VARIANTS": "2",
        "RERANKER_BLENDING": "position_aware",
        "USE_QUERY_DECOMPOSITION": "true",
        "USE_ADAPTIVE_ALPHA": "true",
    }

    def test_all_vars_set(self, monkeypatch):
        for k, v in self.ENV_VARS.items():
            monkeypatch.setenv(k, v)
        config = RAGConfig.from_env()
        assert config.top_k == 12
        assert config.use_hybrid is True
        assert config.hybrid_alpha == 0.5
        assert config.use_reranking is True
        assert config.use_query_expansion is True
        assert config.query_expansion_variants == 2
        assert config.rerank_blending == "position_aware"
        assert config.use_query_decomposition is True
        assert config.use_adaptive_alpha is True

    def test_missing_var_raises(self, monkeypatch):
        # Set all but one
        for k, v in self.ENV_VARS.items():
            monkeypatch.setenv(k, v)
        monkeypatch.delenv("TOP_K_RESULTS", raising=False)
        with pytest.raises(KeyError):
            RAGConfig.from_env()

    def test_type_conversions(self, monkeypatch):
        for k, v in self.ENV_VARS.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("TOP_K_RESULTS", "20")
        monkeypatch.setenv("HYBRID_ALPHA", "0.7")
        monkeypatch.setenv("USE_RERANKING", "false")
        config = RAGConfig.from_env()
        assert config.top_k == 20
        assert config.hybrid_alpha == 0.7
        assert config.use_reranking is False

    def test_frozen_immutability(self, monkeypatch):
        for k, v in self.ENV_VARS.items():
            monkeypatch.setenv(k, v)
        config = RAGConfig.from_env()
        with pytest.raises(AttributeError):
            config.top_k = 99


class TestToAnswerKwargs:
    """Test to_answer_kwargs()."""

    def _make_config(self):
        return RAGConfig(
            top_k=12, use_hybrid=True, hybrid_alpha=0.5,
            use_reranking=True, use_query_expansion=True,
            query_expansion_variants=2, rerank_blending="position_aware",
            use_query_decomposition=True, use_adaptive_alpha=True,
        )

    def test_all_fields_present(self):
        config = self._make_config()
        kwargs = config.to_answer_kwargs()
        assert kwargs["top_k"] == 12
        assert kwargs["use_hybrid"] is True
        assert kwargs["rerank_blending"] == "position_aware"
        assert len(kwargs) == 9  # All 9 fields

    def test_overrides(self):
        config = self._make_config()
        kwargs = config.to_answer_kwargs(doc_ids=["d1"], chat_history=[])
        assert kwargs["doc_ids"] == ["d1"]
        assert kwargs["chat_history"] == []
        assert kwargs["top_k"] == 12  # Original still present

    def test_override_replaces_config_value(self):
        config = self._make_config()
        kwargs = config.to_answer_kwargs(top_k=50)
        assert kwargs["top_k"] == 50


class TestToDict:
    """Test to_dict()."""

    def test_matches_fields(self):
        config = RAGConfig(
            top_k=12, use_hybrid=True, hybrid_alpha=0.5,
            use_reranking=True, use_query_expansion=False,
            query_expansion_variants=2, rerank_blending="simple",
            use_query_decomposition=True, use_adaptive_alpha=False,
        )
        d = config.to_dict()
        assert d["top_k"] == 12
        assert d["use_hybrid"] is True
        assert d["use_query_expansion"] is False
        assert isinstance(d["hybrid_alpha"], float)
