"""Question-answering engine using RAG (Retrieval Augmented Generation)."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from google import genai
from .embedder import Embedder
from .vector_store import VectorStore
from .reranker import Reranker
from .structure_detector import detect_structure

logger = logging.getLogger(__name__)


class QAEngine:
    """RAG-based question answering engine."""

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        gemini_api_key: str,
        model_name: str,
        use_reranker: bool,
        reranker_model: str
    ):
        """
        Initialize QA engine.

        Args:
            embedder: Embedder instance
            vector_store: VectorStore instance
            gemini_api_key: Google Gemini API key
            model_name: Gemini model name
            use_reranker: Whether to initialize reranker (slower startup, better quality)
            reranker_model: Cross-encoder model name for reranking
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.model_name = model_name

        # Create Gemini client (new SDK)
        self.client = genai.Client(api_key=gemini_api_key)

        # Initialize reranker if enabled
        self.reranker = Reranker(model_name=reranker_model) if use_reranker else None
        self.use_reranking = use_reranker

    def _expand_query(self, question: str, num_variants: int) -> List[str]:
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

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
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

    def _is_complex_question(self, question: str) -> bool:
        """Classify whether a question needs decomposition into sub-questions."""
        try:
            prompt = (
                "Classify this question as SIMPLE or COMPLEX.\n"
                "COMPLEX = asks about multiple distinct topics, requires comparing/contrasting, "
                "or needs information from different sections.\n"
                "SIMPLE = asks about one specific thing.\n\n"
                f"Question: {question}\n\n"
                "Reply with ONLY the word SIMPLE or COMPLEX."
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={"temperature": 0.0, "maxOutputTokens": 10}
            )
            return "COMPLEX" in response.text.strip().upper()
        except Exception as e:
            print(f"Warning: Complexity classification failed: {e}")
            return False

    def _decompose_query(self, question: str) -> List[str]:
        """Break a complex question into 2-4 simpler sub-questions."""
        try:
            prompt = (
                "Break this complex question into 2-4 simpler sub-questions.\n"
                "Each sub-question should be independently answerable from a document.\n"
                "Keep sub-questions concise and specific.\n\n"
                f"Question: {question}\n\n"
                "Return ONLY the sub-questions, one per line, no numbering or bullets."
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={"temperature": 0.2, "maxOutputTokens": 256}
            )
            subs = [
                line.strip().lstrip("0123456789.-) ")
                for line in response.text.strip().split("\n")
                if line.strip() and len(line.strip()) > 10
            ]
            return subs[:4] if subs else [question]
        except Exception as e:
            print(f"Warning: Query decomposition failed: {e}")
            return [question]

    def _synthesize_answers(
        self, question: str, sub_results: List[Dict[str, Any]]
    ) -> str:
        """Synthesize sub-question answers into a single comprehensive response."""
        parts = []
        for r in sub_results:
            parts.append(f"Sub-question: {r['question']}\nAnswer: {r['answer']}")
        sub_text = "\n\n".join(parts)

        prompt = (
            "You are a document assistant. Synthesize the following sub-answers into one "
            "comprehensive, well-organized answer to the original question.\n"
            "- Merge overlapping information, don't repeat\n"
            "- Keep source citations from the sub-answers\n"
            "- Use clear structure (headings, bullets) if appropriate\n\n"
            f"Original question: {question}\n\n"
            f"Sub-answers:\n{sub_text}\n\n"
            "Synthesized answer:"
        )
        return self._generate_answer(prompt)

    def _classify_query_type(self, question: str) -> str:
        """Classify what structure type the query is likely looking for.

        Returns one of: table, list, specification, general
        """
        q = question.lower()

        # Table indicators: models, comparison, specifications in tabular form
        table_keywords = [
            "models", "compare", "comparison", "specifications", "spec sheet",
            "dimensions", "ratings", "table", "matrix", "overview of all",
            "list all models", "variants", "part numbers", "model numbers"
        ]
        if any(kw in q for kw in table_keywords):
            return "table"

        # List indicators: steps, features, requirements
        list_keywords = [
            "steps", "features", "list", "requirements", "what are the",
            "enumerate", "how many", "types of", "kinds of", "categories"
        ]
        if any(kw in q for kw in list_keywords):
            return "list"

        # Specification indicators: technical values, tolerances
        spec_keywords = [
            "voltage", "current", "temperature", "weight", "power",
            "tolerance", "range", "rating", "capacity", "speed",
            "frequency", "dimension", "size", "resolution"
        ]
        if any(kw in q for kw in spec_keywords):
            return "specification"

        return "general"

    def _search_with_alpha_selection(
        self,
        question: str,
        query_embedding: List[float],
        doc_ids: Optional[List[str]] = None,
        top_k: int = 12
    ) -> Tuple[List[Dict], float]:
        """
        Try multiple alpha values for hybrid search and pick the best based on reranker confidence.

        This addresses the issue where technical documents (with exact terms like "FX5U")
        need BM25-heavy search (low alpha), while narrative content works better with
        vector-heavy search (high alpha).

        Args:
            question: User question
            query_embedding: Pre-computed query embedding
            doc_ids: Optional document ID filter
            top_k: Number of results to return

        Returns:
            Tuple of (best_results, selected_alpha)
        """
        alphas = [0.2, 0.5, 0.8]  # BM25-heavy, balanced, vector-heavy
        candidates = {}

        for alpha in alphas:
            # Run hybrid search with this alpha
            results = self.vector_store.hybrid_search(
                query_vector=query_embedding,
                query_text=question,
                top_k=top_k,
                doc_ids=doc_ids,
                alpha=alpha,
                use_rrf=True
            )

            if not results:
                continue

            # Score with reranker to determine confidence
            if self.use_reranking and self.reranker:
                reranked = self.reranker.rerank(question, results)
                # Use top reranker score as confidence metric
                top_score = reranked[0]["rerank_score"] if reranked else -999
                candidates[alpha] = (results, reranked, top_score)
            else:
                # Fallback: use retrieval score
                top_score = results[0]["score"] if results else -999
                candidates[alpha] = (results, None, top_score)

        if not candidates:
            return [], 0.5

        # Pick alpha with highest reranker confidence
        best_alpha = max(candidates, key=lambda a: candidates[a][2])
        best_results, best_reranked, best_score = candidates[best_alpha]

        logger.info(
            f"Alpha selection: tried {list(candidates.keys())}, "
            f"picked alpha={best_alpha} (score={best_score:.3f})"
        )

        # Return reranked results if available, otherwise original
        return best_reranked or best_results, best_alpha

    def _boost_by_structure(
        self, chunks: List[Dict], query_type: str, boost_factor: float = 0.15
    ) -> List[Dict]:
        """Boost scores of chunks whose structure matches the query type.

        Args:
            chunks: Retrieved chunks with scores
            query_type: Expected structure type from _classify_query_type
            boost_factor: Score boost for matching structures (0-1)

        Returns:
            Chunks with adjusted scores, re-sorted
        """
        if query_type == "general" or not chunks:
            return chunks

        # Map query type to matching structure types
        structure_map = {
            "table": ["table"],
            "list": ["list", "mixed"],
            "specification": ["specification", "table"],
        }
        target_types = structure_map.get(query_type, [])

        boosted = []
        boost_count = 0
        for chunk in chunks:
            structure = chunk["payload"].get("structure", {})
            structure_type = structure.get("structure_type", "prose")

            new_score = chunk["score"]
            if structure_type in target_types:
                new_score += boost_factor
                boost_count += 1

            boosted.append({**chunk, "score": new_score})

        # Re-sort by boosted score
        boosted.sort(key=lambda x: x["score"], reverse=True)

        if boost_count > 0:
            print(f"Structure boost: {boost_count}/{len(chunks)} chunks boosted for query_type={query_type}")

        return boosted

    def answer_question(
        self,
        question: str,
        top_k: int,
        doc_ids: Optional[List[str]] = None,
        chat_history: Optional[List[Dict]] = None,
        use_hybrid: bool = True,
        hybrid_alpha: float = 0.5,
        use_reranking: bool = True,
        min_score: float = 0.3,
        use_query_expansion: bool = False,
        query_expansion_variants: int = 2,
        use_rrf: bool = True,
        rerank_blending: str = "position_aware",
        use_query_decomposition: bool = False,
        use_adaptive_alpha: bool = True
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
            use_query_decomposition: Whether to decompose complex questions into sub-questions
            use_adaptive_alpha: Whether to try multiple alpha values and pick best (improves technical doc retrieval)

        Returns:
            Dictionary with answer and sources
        """
        # Step 0: Query decomposition (if enabled)
        if use_query_decomposition and self._is_complex_question(question):
            print(f"Query decomposition: question classified as COMPLEX")
            sub_questions = self._decompose_query(question)
            print(f"Query decomposition: {len(sub_questions)} sub-questions: {sub_questions}")

            if len(sub_questions) > 1:
                # Answer each sub-question through the full pipeline (without decomposition)
                sub_results = []
                all_sources = []
                for sq in sub_questions:
                    sr = self.answer_question(
                        question=sq,
                        top_k=top_k,
                        doc_ids=doc_ids,
                        use_hybrid=use_hybrid,
                        hybrid_alpha=hybrid_alpha,
                        use_reranking=use_reranking,
                        min_score=min_score,
                        use_query_expansion=use_query_expansion,
                        query_expansion_variants=query_expansion_variants,
                        use_rrf=use_rrf,
                        rerank_blending=rerank_blending,
                        use_query_decomposition=False,  # prevent recursion
                        use_adaptive_alpha=use_adaptive_alpha,
                    )
                    sub_results.append(sr)
                    all_sources.extend(sr.get("sources", []))

                # Deduplicate sources across sub-answers
                seen_texts = set()
                unique_sources = []
                for s in all_sources:
                    key = s["chunk_text"][:100]
                    if key not in seen_texts:
                        seen_texts.add(key)
                        unique_sources.append(s)

                # Synthesize final answer
                answer = self._synthesize_answers(question, sub_results)
                return {
                    "question": question,
                    "answer": answer,
                    "sources": unique_sources[:top_k],
                    "retrieved_count": len(unique_sources),
                    "decomposed": True,
                    "sub_questions": [sr["question"] for sr in sub_results],
                }

        # Pipeline config logging
        print(f"Pipeline config: top_k={top_k}, hybrid={use_hybrid}, reranking={use_reranking}, expansion={use_query_expansion}, rrf={use_rrf}, decomp={use_query_decomposition}, adaptive_alpha={use_adaptive_alpha}")

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

        # Use adaptive alpha selection for single-query hybrid search (most impactful case)
        alpha_selected = None
        if use_adaptive_alpha and use_hybrid and not use_query_expansion and self.reranker:
            # Adaptive alpha: try multiple alphas, pick best based on reranker confidence
            search_results, alpha_selected = self._search_with_alpha_selection(
                question=question,
                query_embedding=query_embeddings[0],
                doc_ids=doc_ids,
                top_k=retrieval_k
            )
            print(f"Pipeline: {len(search_results)} chunks retrieved via adaptive alpha={alpha_selected}")
            # Results are already reranked by _search_with_alpha_selection
        elif use_query_expansion and len(query_variants) > 1:
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

        if alpha_selected is None:
            print(f"Pipeline: {len(search_results)} chunks retrieved (retrieval_k={retrieval_k})")

        # Step 2.5: Rerank if enabled (skip if already reranked by adaptive alpha)
        if use_reranking and self.reranker and search_results and alpha_selected is None:
            pre_rerank_count = len(search_results)
            search_results = self.reranker.rerank_with_position_blending(
                query=question,
                chunks=search_results,
                blend_strategy=rerank_blending
            )
            print(f"Pipeline: {pre_rerank_count} chunks reranked (all kept)")

        # Step 2.6: Deduplicate near-identical chunks (overlap can cause duplicates)
        search_results = self._deduplicate_chunks(search_results)

        # Step 2.7: Filter noise chunks (very short/substance-free)
        search_results = self._filter_noise_chunks(search_results)

        # Step 2.8: Dynamic score cutoff (replaces hardcoded top_k from reranker)
        search_results = self._dynamic_score_cutoff(search_results)

        # Step 2.9: Structure-aware boosting
        query_type = self._classify_query_type(question)
        if query_type != "general":
            search_results = self._boost_by_structure(search_results, query_type)

        # Step 2.10: Check if we have confident results
        reranking_applied = use_reranking and self.reranker and len(search_results) > 0

        if not search_results:
            return {
                "question": question,
                "answer": "I couldn't find any relevant information in the documents to answer this question.",
                "sources": [],
                "retrieved_count": 0,
                "low_confidence": True
            }

        # Check top score against threshold
        # Skip when reranking is active — cross-encoder blended scores use a
        # different scale (can be negative) so the 0-1 threshold doesn't apply.
        top_score = search_results[0]["score"] if search_results else 0
        if not reranking_applied and top_score < min_score:
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

        print(f"Pipeline: {len(search_results)} chunks sent to LLM")

        # Step 3: Build context from retrieved chunks with enhanced formatting
        context = self._format_context_with_sources(search_results)

        # Build sources list for response
        sources = []
        for result in search_results:
            payload = result["payload"]
            score = result["score"]

            sources.append({
                "doc_id": payload["doc_id"],
                "doc_title": payload["doc_title"],
                "chunk_text": payload["text"][:200] + "..." if len(payload["text"]) > 200 else payload["text"],
                "score": round(score, 3),
                "page_num": payload.get("page_num")
            })

        # Step 4: Generate answer with Gemini
        prompt = self._build_prompt(question, context, query_type)
        answer = self._generate_answer(prompt)

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "retrieved_count": len(search_results)
        }

    def _deduplicate_chunks(
        self, chunks: List[Dict], threshold: float = 0.85
    ) -> List[Dict]:
        """Remove near-duplicate chunks based on text overlap (Jaccard similarity)."""
        if len(chunks) <= 1:
            return chunks

        unique = [chunks[0]]
        for chunk in chunks[1:]:
            text = chunk["payload"]["text"]
            words = set(text.lower().split())
            is_dup = False
            for existing in unique:
                ex_words = set(existing["payload"]["text"].lower().split())
                if not words or not ex_words:
                    continue
                jaccard = len(words & ex_words) / len(words | ex_words)
                if jaccard > threshold:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(chunk)

        if len(unique) < len(chunks):
            print(f"Deduplication: {len(chunks)} -> {len(unique)} chunks")
        return unique

    def _filter_noise_chunks(self, chunks: List[Dict], min_length: int = 50) -> List[Dict]:
        """Remove very short or noise-only chunks that add no substance."""
        filtered = [c for c in chunks if len(c["payload"]["text"].strip()) >= min_length]
        if len(filtered) < len(chunks):
            print(f"Noise filter: {len(chunks)} → {len(filtered)} chunks (removed {len(chunks) - len(filtered)} short chunks)")
        return filtered if filtered else chunks  # fallback: keep originals if all filtered

    def _dynamic_score_cutoff(self, chunks, max_chunks=15, drop_ratio=0.6):
        """Keep chunks in the top portion of the score range.

        Uses score range (top - bottom) to set cutoff, which works for
        any score scale (positive, negative, blended).

        Adaptive minimum: keeps at least 50% of small pools (floor of 3).
        For small candidate pools (<=12), uses wider ratio (0.8) to avoid
        over-filtering.
        """
        # Adaptive minimum: keep at least 50% of small pools, floor of 3
        min_chunks = max(3, int(len(chunks) * 0.5))

        if len(chunks) <= min_chunks:
            return chunks

        # For small candidate pools (≤12), use wider ratio to avoid over-filtering
        effective_ratio = 0.8 if len(chunks) <= 12 else drop_ratio

        top_score = chunks[0]["score"]
        bottom_score = chunks[-1]["score"]
        score_range = top_score - bottom_score

        if score_range <= 0:
            return chunks[:max_chunks]

        cutoff = top_score - effective_ratio * score_range
        kept = [c for c in chunks if c["score"] >= cutoff]

        if len(kept) < min_chunks:
            kept = chunks[:min_chunks]
        elif len(kept) > max_chunks:
            kept = kept[:max_chunks]

        print(f"Dynamic cutoff: {len(chunks)} → {len(kept)} chunks (cutoff={cutoff:.3f}, top={top_score:.3f}, range={score_range:.3f}, min={min_chunks})")
        return kept

    def _reorder_top_and_tail(self, chunks):
        """Place best chunks at start and end, weakest in middle.

        LLMs attend most to the beginning and end of context (lost-in-the-middle).
        Interleave: best→position 1, 2nd best→position N, 3rd→position 2, etc.
        """
        if len(chunks) <= 2:
            return chunks
        reordered = [None] * len(chunks)
        left, right = 0, len(chunks) - 1
        for i, chunk in enumerate(chunks):
            if i % 2 == 0:
                reordered[left] = chunk
                left += 1
            else:
                reordered[right] = chunk
                right -= 1
        return reordered

    def _build_prompt(self, question: str, context: str, query_type: str = "general") -> str:
        """
        Build prompt for Gemini with per-source engagement and few-shot example.

        Args:
            question: User question
            context: Retrieved context from documents
            query_type: Classified query type (table, list, specification, general)

        Returns:
            Formatted prompt string
        """
        type_hints = {
            "table": "\nPresent specifications or model data in a markdown table.",
            "list": "\nPresent the answer as a clean numbered or bulleted list.",
            "specification": "\nInclude exact values, units, and tolerances. Use a table if comparing multiple specs.",
        }
        suffix = type_hints.get(query_type, "")

        return f"""You are an expert technical writer producing a clear, well-structured reference answer. Use ONLY the provided sources.

INSTRUCTIONS:
1. Read every source. Extract specific details — numbers, dates, names, conditions, definitions, amounts.
2. For each major point, describe it fully using information from the sources. Do not merely name a concept; explain what it is, why it matters, and include any qualifications or exceptions found in the sources.
3. If multiple sources cover the same topic, merge their details into one comprehensive description.
4. Cite sources inline as [Source N]. Place one citation at the end of a sentence or paragraph that covers that source — do NOT repeat the same citation on every line within the same section.
5. NEVER say information is "not provided" if it appears in any source.
6. Use structured formatting: **headings** (##) to separate major topics, **bold labels** for key terms, bullets for lists, numbered steps for procedures, and tables for comparisons or specifications.
7. Never claim that information is absent or a feature does not exist unless sources explicitly state so.
8. Be concise. One clear sentence is better than three that repeat the same idea. Avoid filler introductions like "Here's how X works:" — go straight to the content.

CITATION DETAILS:
- NEVER put the same [Source N] on consecutive lines. If steps 1-5 all come from Source 3, cite [Source 3] once after step 5 or in a note below the list.
- When multiple sources contribute to one section, list them together: [Source 3][Source 4].

FORMATTING DETAILS:
- Use ## headings to separate major topics, ### for subtopics.
- Use numbered lists for step-by-step procedures.
- Use bullet lists for feature lists or descriptions.
- Use markdown tables (with | pipes and header separators) for comparisons, settings, or specs.
- Use **bold** for UI elements, menu paths, and key terms.
- When the same detail (e.g. "30-second timeout") applies to multiple items, state it once or put it in a summary table. Do NOT repeat it per section.
- NEVER copy large blocks of raw source text into your answer. Summarize and restructure the information. Keep table cells short (under 80 characters).

EXAMPLE:
Sources:
  Source 1: "Connect PC to CPU via Ethernet cable. Select Online > Connection Destination. Choose Ethernet. Specify adapter. Click Communication Test. Timeout: 30s, retries: 0."
  Source 2: "Connect PC to CPU via USB cable. Select Online > Connection Destination. Choose USB. Click Communication Test. Timeout: 30s, retries: 0."
  Source 3: "XR-7 motor: 48V DC, 750W continuous. Weight: 12.3 kg."
  Source 4: "XR-7 battery: 48V 20Ah lithium-ion. Regenerative braking with 15% energy recovery."

Q: How do I connect to the CPU, and what are the XR-7 specs?

A: ## Connecting to the CPU Module

### Direct Ethernet

1. Connect the PC to the CPU module with an Ethernet cable.
2. Select **Online > Current Connection Destination**.
3. Choose **Ethernet** and specify the PC-side adapter.
4. Click **Communication Test** to verify [Source 1].

### USB

1. Connect the PC to the CPU module with a USB cable.
2. Select **Online > Current Connection Destination**.
3. Choose **USB** and click **Communication Test** [Source 2].

Both methods default to a 30-second timeout with 0 retries.

## XR-7 Specifications

| Spec | Value |
|------|-------|
| Motor | 48V DC, 750W continuous [Source 3] |
| Battery | 48V 20Ah lithium-ion [Source 4] |
| Braking | Regenerative, ~15% recovery [Source 4] |
| Weight | 12.3 kg [Source 3] |

---

Context from documents:
{context}

Question: {question}
{suffix}
Answer:"""

    def _format_context_with_sources(self, search_results: List[Dict]) -> str:
        """
        Format context from search results with relevance indicators.

        Args:
            search_results: List of search results with payload and score

        Returns:
            Formatted context string with visual hierarchy
        """
        # Reorder: best chunks at start and end (lost-in-the-middle mitigation)
        search_results = self._reorder_top_and_tail(search_results)

        context_parts = []
        for i, result in enumerate(search_results, 1):
            payload = result["payload"]

            # Add page number if available
            page_info = f", Page {payload.get('page_num')}" if payload.get('page_num') else ""

            # Clean source header — no scores or stars to avoid LLM bias
            source_info = f"Source {i}: \"{payload['doc_title']}\"{page_info}"

            # Truncate excessively long chunks to prevent LLM from dumping raw text
            text = payload['text']
            if len(text) > 2000:
                text = text[:2000] + "\n[...truncated]"

            context_parts.append(f"{source_info}\n{text}")

        return "\n\n" + "="*80 + "\n\n".join(context_parts)

    def _generate_answer(self, prompt: str) -> str:
        """Generate answer using Gemini."""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "temperature": 0.4,        # Balanced: factual but not overly terse
                    "topP": 0.9,              # Reasonable diversity (camelCase!)
                    "maxOutputTokens": 8192   # Allow thorough answers (camelCase!)
                }
            )
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
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Test"
            )
            return True
        except Exception:
            return False
