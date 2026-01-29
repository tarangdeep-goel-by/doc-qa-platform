"""Question-answering engine using RAG (Retrieval Augmented Generation)."""

from typing import List, Dict, Any, Optional
import google.generativeai as genai
from .embedder import Embedder
from .vector_store import VectorStore
from .reranker import Reranker


class QAEngine:
    """RAG-based question answering engine."""

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        gemini_api_key: str,
        model_name: str = "gemini-2.5-flash",
        use_reranker: bool = True
    ):
        """
        Initialize QA engine.

        Args:
            embedder: Embedder instance
            vector_store: VectorStore instance
            gemini_api_key: Google Gemini API key
            model_name: Gemini model name
            use_reranker: Whether to initialize reranker (slower startup, better quality)
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.model_name = model_name

        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel(model_name)

        # Initialize reranker if enabled
        self.reranker = Reranker() if use_reranker else None

    def _expand_query(self, question: str, num_variants: int = 2) -> List[str]:
        """
        Generate alternative phrasings of the question to improve recall.

        Args:
            question: Original user question
            num_variants: Number of alternative phrasings to generate

        Returns:
            List of query variants [original, variant1, variant2, ...]
        """
        try:
            prompt = f"""Generate {num_variants} alternative ways to phrase this question.
Keep the core intent but use different words, synonyms, or perspectives.
Each variant should be concise and clear.

Question: {question}

Return ONLY the {num_variants} variants, one per line, without numbering or additional text."""

            response = self.model.generate_content(prompt)
            variants_text = response.text.strip()

            # Parse variants (one per line)
            variants = [v.strip() for v in variants_text.split('\n') if v.strip()]

            # Limit to requested number
            variants = variants[:num_variants]

            # Return original + variants
            return [question] + variants

        except Exception as e:
            # If expansion fails, fall back to original query only
            print(f"Warning: Query expansion failed: {e}")
            return [question]

    def answer_question(
        self,
        question: str,
        top_k: int = 10,
        doc_ids: Optional[List[str]] = None,
        chat_history: Optional[List[Dict]] = None,
        use_hybrid: bool = True,
        hybrid_alpha: float = 0.5,
        use_reranking: bool = True,
        min_score: float = 0.3,
        use_query_expansion: bool = False,
        query_expansion_variants: int = 2,
        use_rrf: bool = True,
        rerank_blending: str = "position_aware"
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG pipeline.

        Args:
            question: User question
            top_k: Number of chunks to retrieve
            doc_ids: Optional list of document IDs to filter search
            chat_history: Optional chat history for context (Gemini format)
            use_hybrid: Whether to use hybrid search (vector + BM25) or pure vector
            hybrid_alpha: Weight for hybrid search (0=all BM25, 1=all vector, 0.5=balanced)
            use_reranking: Whether to rerank results with cross-encoder
            min_score: Minimum confidence score threshold (0-1)
            use_query_expansion: Whether to generate alternative query phrasings (improves recall)
            query_expansion_variants: Number of alternative phrasings to generate
            use_rrf: Whether to use Reciprocal Rank Fusion (True) or weighted fusion (False)
            rerank_blending: Blending strategy for reranking ("position_aware" or "replace")

        Returns:
            Dictionary with answer and sources
        """
        # Step 1: Query expansion (if enabled)
        if use_query_expansion:
            query_variants = self._expand_query(question, num_variants=query_expansion_variants)
            # Weight original query 2×, variants 1× each
            query_weights = [2.0] + [1.0] * query_expansion_variants
        else:
            query_variants = [question]
            query_weights = [1.0]

        # Step 2: Embed all query variants
        query_embeddings = [self.embedder.embed_text(q) for q in query_variants]

        # Step 3: Retrieve relevant chunks (get more candidates if reranking)
        retrieval_k = top_k * 2 if use_reranking and self.reranker else top_k

        if use_query_expansion and len(query_variants) > 1:
            # Multi-query search with fusion
            search_results = self.vector_store.multi_query_hybrid_search(
                query_variants=query_variants,
                query_embeddings=query_embeddings,
                query_weights=query_weights,
                top_k=retrieval_k,
                doc_ids=doc_ids,
                alpha=hybrid_alpha,
                use_rrf=use_rrf
            )
        elif use_hybrid:
            # Single query hybrid search
            search_results = self.vector_store.hybrid_search(
                query_vector=query_embeddings[0],
                query_text=query_variants[0],
                top_k=retrieval_k,
                doc_ids=doc_ids,
                alpha=hybrid_alpha,
                use_rrf=use_rrf
            )
        else:
            # Single query vector search
            search_results = self.vector_store.search(
                query_vector=query_embeddings[0],
                top_k=retrieval_k,
                doc_ids=doc_ids
            )

        # Step 2.5: Rerank if enabled
        if use_reranking and self.reranker and search_results:
            search_results = self.reranker.rerank_with_position_blending(
                query=question,
                chunks=search_results,
                top_k=top_k,
                blend_strategy=rerank_blending
            )

        # Step 2.6: Check if we have confident results
        if not search_results:
            return {
                "question": question,
                "answer": "I couldn't find any relevant information in the documents to answer this question.",
                "sources": [],
                "retrieved_count": 0,
                "low_confidence": True
            }

        # Check top score against threshold
        top_score = search_results[0]["score"] if search_results else 0
        if top_score < min_score:
            # Format sources consistently even for low confidence responses
            formatted_sources = [
                {
                    "doc_id": result["payload"]["doc_id"],
                    "doc_title": result["payload"]["doc_title"],
                    "chunk_text": result["payload"]["text"][:200] + "..." if len(result["payload"]["text"]) > 200 else result["payload"]["text"],
                    "score": round(result["score"], 3),
                    "page_num": result["payload"].get("page_num")
                }
                for result in search_results
            ]

            return {
                "question": question,
                "answer": (
                    "I don't have enough information to answer that question confidently. "
                    "This could mean:\n"
                    "- The information isn't in the uploaded documents\n"
                    "- The question needs to be more specific\n"
                    "- Try rephrasing or check if the right documents are uploaded"
                ),
                "sources": formatted_sources,
                "retrieved_count": len(search_results),
                "low_confidence": True,
                "top_score": top_score
            }

        # Step 3: Build context from retrieved chunks
        context_parts = []
        sources = []

        for i, result in enumerate(search_results):
            payload = result["payload"]
            score = result["score"]

            # Add to context
            context_parts.append(
                f'[Document: "{payload["doc_title"]}", Chunk {payload["chunk_index"] + 1}]: {payload["text"]}'
            )

            # Add to sources
            sources.append({
                "doc_id": payload["doc_id"],
                "doc_title": payload["doc_title"],
                "chunk_text": payload["text"][:200] + "..." if len(payload["text"]) > 200 else payload["text"],
                "score": round(score, 3),
                "page_num": payload.get("page_num")
            })

        context = "\n\n".join(context_parts)

        # Step 4: Generate answer with Gemini
        prompt = self._build_prompt(question, context)
        answer = self._generate_answer(prompt)

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "retrieved_count": len(search_results)
        }

    def _build_prompt(self, question: str, context: str) -> str:
        """
        Build prompt for Gemini with strict grounding instructions.

        Args:
            question: User question
            context: Retrieved context from documents

        Returns:
            Formatted prompt string
        """
        return f"""You are a precise document assistant. Your task is to answer questions using ONLY information explicitly stated in the provided context.

CRITICAL RULES:
1. Answer ONLY using information EXPLICITLY stated in the context below
2. If the context doesn't contain enough information, say so clearly
3. NEVER infer, guess, or use general knowledge beyond the context
4. Quote specific passages when answering
5. Cite which document(s) you used

Context from documents:
{context}

User Question: {question}

BEFORE answering, verify:
- Is the answer explicitly stated in the context?
- Can I quote the specific passage that supports this?
- Am I using ONLY the context, not my general knowledge?

If you cannot find sufficient information in the context:
- Say "I cannot find information about [topic] in the available documents"
- Suggest the user might need to check other sources or rephrase the question
- Do NOT attempt to answer from general knowledge

Answer:"""

    def _generate_answer(self, prompt: str) -> str:
        """Generate answer using Gemini."""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def _check_source_metadata(self, sources: List[Dict]) -> str:
        """
        Generate warnings based on source metadata.

        Args:
            sources: List of source dictionaries with metadata

        Returns:
            Warning string to append to answer (empty if no warnings)
        """
        warnings = []

        if not sources:
            return ""

        # Check for low scores
        if sources[0]["score"] < 0.5:
            warnings.append(
                "⚠️ Note: The retrieved information may not be directly related to your question. "
                "Consider rephrasing or checking if the relevant documents are uploaded."
            )

        # Could add more checks:
        # - Conflicting information from different documents
        # - Outdated documents (if date metadata available)
        # - Missing page numbers

        return "\n\n" + "\n".join(warnings) if warnings else ""

    def check_gemini_connection(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            # Try a simple generation
            response = self.model.generate_content("Test")
            return True
        except Exception:
            return False
