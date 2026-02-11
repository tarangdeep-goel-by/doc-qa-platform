"""Centralized RAG pipeline configuration — single source of truth."""

import os
from dataclasses import dataclass, fields


def str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ("true", "1", "yes")


@dataclass(frozen=True)
class RAGConfig:
    """Immutable RAG pipeline configuration read from environment variables.

    All RAG params live here. Consumers call from_env() once at startup
    and pass to_answer_kwargs() to qa_engine.answer_question().
    """

    top_k: int
    use_hybrid: bool
    hybrid_alpha: float
    use_reranking: bool
    use_query_expansion: bool
    query_expansion_variants: int
    rerank_blending: str
    use_query_decomposition: bool
    use_adaptive_alpha: bool

    @classmethod
    def from_env(cls) -> "RAGConfig":
        """Read all RAG params from environment. Fast-fail on missing vars."""
        return cls(
            top_k=int(os.environ["TOP_K_RESULTS"]),
            use_hybrid=str_to_bool(os.environ["USE_HYBRID_SEARCH"]),
            hybrid_alpha=float(os.environ["HYBRID_ALPHA"]),
            use_reranking=str_to_bool(os.environ["USE_RERANKING"]),
            use_query_expansion=str_to_bool(os.environ["USE_QUERY_EXPANSION"]),
            query_expansion_variants=int(os.environ["QUERY_EXPANSION_VARIANTS"]),
            rerank_blending=os.environ["RERANKER_BLENDING"],
            use_query_decomposition=str_to_bool(os.environ["USE_QUERY_DECOMPOSITION"]),
            use_adaptive_alpha=str_to_bool(os.environ["USE_ADAPTIVE_ALPHA"]),
        )

    def to_answer_kwargs(self, **overrides) -> dict:
        """Build kwargs dict for qa_engine.answer_question(). Overrides merged in."""
        kwargs = {f.name: getattr(self, f.name) for f in fields(self)}
        kwargs.update(overrides)
        return kwargs

    def to_dict(self) -> dict:
        """For eval history / logging. Returns typed values (not strings)."""
        return {f.name: getattr(self, f.name) for f in fields(self)}
