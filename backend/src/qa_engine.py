"""Question-answering engine using RAG (Retrieval Augmented Generation)."""

from typing import List, Dict, Any, Optional
import google.generativeai as genai
from .embedder import Embedder
from .vector_store import VectorStore


class QAEngine:
    """RAG-based question answering engine."""

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        gemini_api_key: str,
        model_name: str = "gemini-2.5-flash"
    ):
        """
        Initialize QA engine.

        Args:
            embedder: Embedder instance
            vector_store: VectorStore instance
            gemini_api_key: Google Gemini API key
            model_name: Gemini model name
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.model_name = model_name

        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel(model_name)

    def answer_question(
        self,
        question: str,
        top_k: int = 10,
        doc_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG pipeline.

        Args:
            question: User question
            top_k: Number of chunks to retrieve
            doc_ids: Optional list of document IDs to filter search

        Returns:
            Dictionary with answer and sources
        """
        # Step 1: Embed the question
        query_embedding = self.embedder.embed_text(question)

        # Step 2: Retrieve relevant chunks from Qdrant
        search_results = self.vector_store.search(
            query_vector=query_embedding,
            top_k=top_k,
            doc_ids=doc_ids
        )

        if not search_results:
            return {
                "question": question,
                "answer": "I couldn't find any relevant information in the documents to answer this question.",
                "sources": [],
                "retrieved_count": 0
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
                "score": round(score, 3)
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
        """Build prompt for Gemini."""
        return f"""You are a helpful assistant answering questions about documents.

Context from relevant documents:
{context}

User Question: {question}

Instructions:
- Answer the question based ONLY on the context above.
- Cite which document(s) you used in your answer.
- If the context doesn't contain relevant information, say so clearly.
- Be concise but thorough.
- If you're uncertain, acknowledge it.

Answer:"""

    def _generate_answer(self, prompt: str) -> str:
        """Generate answer using Gemini."""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def check_gemini_connection(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            # Try a simple generation
            response = self.model.generate_content("Test")
            return True
        except Exception:
            return False
