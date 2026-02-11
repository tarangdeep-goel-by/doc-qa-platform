"""Question-answering engine using RAG (Retrieval Augmented Generation)."""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple
from google import genai
from .embedder import Embedder
from .vector_store import VectorStore
from .reranker import Reranker

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
        reranker_model: str,
        fast_model_name: str = None
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.fast_model_name = fast_model_name or model_name

        # Create Gemini client (new SDK)
        self.client = genai.Client(api_key=gemini_api_key)

        # Initialize reranker if enabled
        self.reranker = Reranker(model_name=reranker_model) if use_reranker else None
        self.use_reranking = use_reranker

    def _classify_and_expand(self, question: str, num_variants: int = 2) -> Dict[str, Any]:
        """Classify question complexity and generate expansion variants in a single Gemini call.

        Replaces separate _is_complex_question + _expand_query/_decompose_query calls,
        saving one Gemini round-trip per question. Also fixes NoneType crash when
        Gemini returns empty response for classification.

        Returns:
            dict with is_complex, variants (original + alternatives), sub_questions (if complex)
        """
        try:
            prompt = (
                f"Analyze this question. Respond in the EXACT format below.\n\n"
                f"1. Classify as SIMPLE or COMPLEX:\n"
                f"   - COMPLEX = asks about multiple distinct topics, requires comparing/contrasting, "
                f"or needs information from different sections\n"
                f"   - SIMPLE = asks about one specific thing\n\n"
                f"2. Write {num_variants} alternative phrasings using different words or perspectives.\n\n"
                f"3. If COMPLEX, also break into 2-4 simpler sub-questions (each independently answerable).\n\n"
                f"Question: {question}\n\n"
                f"CLASSIFICATION: [SIMPLE or COMPLEX]\n"
                f"VARIANTS:\n"
                f"1. [alternative phrasing]\n"
                f"2. [alternative phrasing]\n"
                f"SUB_QUESTIONS:\n"
                f"1. [only if COMPLEX, otherwise write NONE]"
            )
            response = self.client.models.generate_content(
                model=self.fast_model_name,
                contents=prompt,
                config={"temperature": 0.2, "maxOutputTokens": 512}
            )

            text = (response.text or "").strip()
            if not text:
                return {"is_complex": False, "variants": [question], "sub_questions": []}

            is_complex = False
            variants = []
            sub_questions = []
            section = None

            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                upper = line.upper()
                if "CLASSIFICATION:" in upper:
                    is_complex = "COMPLEX" in upper
                    section = "classification"
                elif upper.startswith("VARIANT"):
                    section = "variants"
                elif "SUB_QUESTION" in upper.replace("-", "_").replace(" ", "_"):
                    section = "sub_questions"
                elif section == "variants" and len(line) > 2 and line[0].isdigit():
                    item = line.lstrip("0123456789.-) ").strip()
                    if len(item) > 10:
                        variants.append(item)
                elif section == "sub_questions" and len(line) > 2 and line[0].isdigit():
                    item = line.lstrip("0123456789.-) ").strip()
                    if len(item) > 10:
                        sub_questions.append(item)

            return {
                "is_complex": is_complex,
                "variants": [question] + variants[:num_variants],
                "sub_questions": sub_questions[:4] if is_complex else [],
            }
        except Exception as e:
            logger.warning(f"classify_and_expand failed: {e}")
            return {"is_complex": False, "variants": [question], "sub_questions": []}

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

        # Phase 1: Run all hybrid searches in parallel (stateless HTTP + read-only BM25)
        def _search_for_alpha(alpha):
            return alpha, self.vector_store.hybrid_search(
                query_vector=query_embedding,
                query_text=question,
                top_k=top_k,
                doc_ids=doc_ids,
                alpha=alpha,
                use_rrf=True
            )

        search_results_by_alpha = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(_search_for_alpha, a) for a in alphas]
            for future in futures:
                try:
                    alpha, results = future.result()
                    if results:
                        search_results_by_alpha[alpha] = results
                except Exception as e:
                    logger.warning(f"Alpha search failed: {e}")

        # Phase 2: Rerank each sequentially (CrossEncoder model is not thread-safe)
        for alpha, results in search_results_by_alpha.items():
            if self.use_reranking and self.reranker:
                reranked = self.reranker.rerank(question, results)
                top_score = reranked[0]["rerank_score"] if reranked else -999
                candidates[alpha] = (results, reranked, top_score)
            else:
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
            logger.info(f"Structure boost: {boost_count}/{len(chunks)} chunks boosted for query_type={query_type}")

        return boosted

    def _retrieve(
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
        Run retrieval pipeline: classify, search, rerank, filter.

        Returns dict with keys:
            - search_results: filtered chunks
            - sources: formatted sources list
            - context: formatted context string
            - prompt: final LLM prompt
            - query_type: classified query type
            - early_return: None or a complete response dict (for empty/low-confidence/decomposed)
            - decomposed_result: full response dict if query was decomposed, else None
        """
        # Guard: empty question
        if not question or not question.strip():
            return {
                "early_return": {
                    "question": question,
                    "answer": "I don't have enough information to answer an empty question. Please provide a specific question about your documents.",
                    "sources": [],
                    "low_confidence": True,
                    "retrieved_count": 0,
                    "_chunks": [],
                }
            }

        # Step 0+1: Combined classification + expansion (single Gemini call)
        query_variants = [question]
        query_weights = [1.0]

        if use_query_decomposition or use_query_expansion:
            # Parallel: classify+expand and embed original question concurrently
            with ThreadPoolExecutor(max_workers=2) as executor:
                ce_future = executor.submit(self._classify_and_expand, question, query_expansion_variants)
                embed_future = executor.submit(self.embedder.embed_text, question)

                ce_result = ce_future.result()
                original_embedding = embed_future.result()

            # Handle complex question decomposition
            if use_query_decomposition and ce_result["is_complex"]:
                sub_questions = ce_result["sub_questions"]
                logger.info(f"Query decomposition: COMPLEX, {len(sub_questions)} sub-questions: {sub_questions}")

                if len(sub_questions) > 1:
                    def _run_sub_question(sq):
                        return self.answer_question(
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
                            use_query_decomposition=False,
                            use_adaptive_alpha=use_adaptive_alpha,
                        )

                    with ThreadPoolExecutor(max_workers=len(sub_questions)) as executor:
                        sub_results = list(executor.map(_run_sub_question, sub_questions))

                    all_sources = []
                    for sr in sub_results:
                        all_sources.extend(sr.get("sources", []))

                    seen_texts = set()
                    unique_sources = []
                    for s in all_sources:
                        key = s["chunk_text"][:100]
                        if key not in seen_texts:
                            seen_texts.add(key)
                            unique_sources.append(s)

                    return {
                        "early_return": None,
                        "decomposed_result": {
                            "question": question,
                            "sub_results": sub_results,
                            "sources": unique_sources[:top_k],
                            "retrieved_count": len(unique_sources),
                            "sub_questions": [sr["question"] for sr in sub_results],
                        }
                    }

            # Use query variants for expansion (simple questions or decomp disabled)
            if use_query_expansion:
                query_variants = ce_result["variants"]
                query_weights = [2.0] + [1.0] * (len(query_variants) - 1)

            # Embed extra variants in batch (original already done in parallel)
            if use_query_expansion and len(query_variants) > 1:
                extra_variants = query_variants[1:]  # skip original
                extra_embeddings = list(self.embedder.embed_texts(extra_variants))
                query_embeddings = [original_embedding] + extra_embeddings
            else:
                query_embeddings = [original_embedding]
        else:
            query_embeddings = [self.embedder.embed_text(question)]

        # Pipeline config logging
        logger.info(f"Pipeline config: top_k={top_k}, hybrid={use_hybrid}, reranking={use_reranking}, expansion={use_query_expansion}, rrf={use_rrf}, decomp={use_query_decomposition}, adaptive_alpha={use_adaptive_alpha}")

        # Step 3: Retrieve relevant chunks (get more candidates if reranking)
        retrieval_k = top_k * 2 if use_reranking and self.reranker else top_k

        # Phase A: Find best alpha via parallel search + sequential rerank
        alpha_selected = None
        adaptive_results = None
        if use_adaptive_alpha and use_hybrid and self.reranker:
            adaptive_results, alpha_selected = self._search_with_alpha_selection(
                question=question,
                query_embedding=query_embeddings[0],
                doc_ids=doc_ids,
                top_k=retrieval_k
            )
            logger.info(f"Pipeline: adaptive alpha selected={alpha_selected}")

        # Phase B: Main retrieval using best alpha (or default)
        effective_alpha = alpha_selected if alpha_selected is not None else hybrid_alpha

        if use_query_expansion and len(query_variants) > 1:
            search_results = self.vector_store.multi_query_hybrid_search(
                query_variants=query_variants,
                query_embeddings=query_embeddings,
                query_weights=query_weights,
                top_k=retrieval_k,
                doc_ids=doc_ids,
                alpha=effective_alpha,
                use_rrf=use_rrf
            )
            adaptive_results = None
        elif use_hybrid:
            if adaptive_results is not None:
                search_results = adaptive_results
            else:
                search_results = self.vector_store.hybrid_search(
                    query_vector=query_embeddings[0],
                    query_text=query_variants[0],
                    top_k=retrieval_k,
                    doc_ids=doc_ids,
                    alpha=effective_alpha,
                    use_rrf=use_rrf
                )
        else:
            search_results = self.vector_store.search(
                query_vector=query_embeddings[0],
                top_k=retrieval_k,
                doc_ids=doc_ids
            )

        logger.info(f"Pipeline: {len(search_results)} chunks retrieved (retrieval_k={retrieval_k})")

        # Step 2.5: Rerank
        already_reranked = adaptive_results is not None and search_results is adaptive_results
        if use_reranking and self.reranker and search_results and not already_reranked:
            pre_rerank_count = len(search_results)
            search_results = self.reranker.rerank_with_position_blending(
                query=question,
                chunks=search_results,
                blend_strategy=rerank_blending
            )
            logger.info(f"Pipeline: {pre_rerank_count} chunks reranked (all kept)")

        # Step 2.6-2.9: Post-processing
        search_results = self._deduplicate_chunks(search_results)
        search_results = self._filter_noise_chunks(search_results)
        search_results = self._dynamic_score_cutoff(search_results)

        query_type = self._classify_query_type(question)
        if query_type != "general":
            search_results = self._boost_by_structure(search_results, query_type)

        # Check confidence
        reranking_applied = use_reranking and self.reranker and len(search_results) > 0

        if not search_results:
            return {
                "early_return": {
                    "question": question,
                    "answer": "I couldn't find any relevant information in the documents to answer this question.",
                    "sources": [],
                    "retrieved_count": 0,
                    "low_confidence": True,
                    "_chunks": [],
                }
            }

        top_score = search_results[0]["score"] if search_results else 0
        if not reranking_applied and top_score < min_score:
            return {
                "early_return": {
                    "question": question,
                    "answer": (
                        "I don't have enough information to answer that question confidently. "
                        "This could mean:\n"
                        "- The information isn't in the uploaded documents\n"
                        "- The question needs to be more specific\n"
                        "- Try rephrasing or check if the right documents are uploaded"
                    ),
                    "sources": self._format_sources(search_results),
                    "retrieved_count": len(search_results),
                    "low_confidence": True,
                    "top_score": top_score,
                    "_chunks": search_results,
                }
            }

        logger.info(f"Pipeline: {len(search_results)} chunks sent to LLM")

        context = self._format_context_with_sources(search_results)
        sources = self._format_sources(search_results)
        prompt = self._build_prompt(question, context, query_type, chat_history=chat_history)

        return {
            "early_return": None,
            "decomposed_result": None,
            "search_results": search_results,
            "sources": sources,
            "context": context,
            "prompt": prompt,
            "query_type": query_type,
        }

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
        Answer a question using RAG pipeline (non-streaming).

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
        retrieval = self._retrieve(
            question=question,
            top_k=top_k,
            doc_ids=doc_ids,
            chat_history=chat_history,
            use_hybrid=use_hybrid,
            hybrid_alpha=hybrid_alpha,
            use_reranking=use_reranking,
            min_score=min_score,
            use_query_expansion=use_query_expansion,
            query_expansion_variants=query_expansion_variants,
            use_rrf=use_rrf,
            rerank_blending=rerank_blending,
            use_query_decomposition=use_query_decomposition,
            use_adaptive_alpha=use_adaptive_alpha,
        )

        # Handle early returns (empty, low-confidence)
        if retrieval.get("early_return"):
            return retrieval["early_return"]

        # Handle decomposed queries
        if retrieval.get("decomposed_result"):
            dr = retrieval["decomposed_result"]
            answer = self._synthesize_answers(question, dr["sub_results"])
            return {
                "question": question,
                "answer": answer,
                "sources": dr["sources"],
                "retrieved_count": dr["retrieved_count"],
                "decomposed": True,
                "sub_questions": dr["sub_questions"],
                "_chunks": [],
            }

        # Normal path: generate answer
        answer = self._generate_answer(retrieval["prompt"])
        return {
            "question": question,
            "answer": answer,
            "sources": retrieval["sources"],
            "retrieved_count": len(retrieval["search_results"]),
            "_chunks": retrieval["search_results"],
        }

    def _generate_answer_stream(self, prompt: str):
        """Yield text chunks from Gemini streaming API."""
        from .gemini_retry import gemini_retry

        response = gemini_retry(lambda: self.client.models.generate_content_stream(
            model=self.fast_model_name,
            contents=prompt,
            config={
                "temperature": 0.4,
                "topP": 0.9,
                "maxOutputTokens": 8192,
            },
        ))
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def answer_question_stream(
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
    ):
        """
        Stream an answer using RAG pipeline. Yields SSE event dicts.

        Event types:
            retrieval_done: {"type": "retrieval_done", "sources": [...]}
            chunk: {"type": "chunk", "content": "partial text..."}
            done: {"type": "done", "full_content": "complete answer"}
            error: {"type": "error", "detail": "..."}
        """
        try:
            retrieval = self._retrieve(
                question=question,
                top_k=top_k,
                doc_ids=doc_ids,
                chat_history=chat_history,
                use_hybrid=use_hybrid,
                hybrid_alpha=hybrid_alpha,
                use_reranking=use_reranking,
                min_score=min_score,
                use_query_expansion=use_query_expansion,
                query_expansion_variants=query_expansion_variants,
                use_rrf=use_rrf,
                rerank_blending=rerank_blending,
                use_query_decomposition=use_query_decomposition,
                use_adaptive_alpha=use_adaptive_alpha,
            )

            # Handle early returns (no streaming needed)
            if retrieval.get("early_return"):
                er = retrieval["early_return"]
                yield {"type": "retrieval_done", "sources": er.get("sources", [])}
                yield {"type": "chunk", "content": er["answer"]}
                yield {"type": "done", "full_content": er["answer"]}
                return

            # Handle decomposed queries (sub-questions answered non-streaming, synthesis non-streaming)
            if retrieval.get("decomposed_result"):
                dr = retrieval["decomposed_result"]
                yield {"type": "retrieval_done", "sources": dr["sources"]}
                answer = self._synthesize_answers(question, dr["sub_results"])
                yield {"type": "chunk", "content": answer}
                yield {"type": "done", "full_content": answer}
                return

            # Normal path: emit sources, then stream LLM generation
            yield {"type": "retrieval_done", "sources": retrieval["sources"]}

            full_content = []
            for text_chunk in self._generate_answer_stream(retrieval["prompt"]):
                full_content.append(text_chunk)
                yield {"type": "chunk", "content": text_chunk}

            yield {"type": "done", "full_content": "".join(full_content)}

        except Exception as e:
            logger.exception("Streaming answer failed")
            yield {"type": "error", "detail": str(e)}

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
            logger.debug(f"Deduplication: {len(chunks)} -> {len(unique)} chunks")
        return unique

    def _filter_noise_chunks(self, chunks: List[Dict], min_length: int = 50) -> List[Dict]:
        """Remove very short or noise-only chunks that add no substance."""
        filtered = [c for c in chunks if len(c["payload"]["text"].strip()) >= min_length]
        if len(filtered) < len(chunks):
            logger.debug(f"Noise filter: {len(chunks)} → {len(filtered)} chunks (removed {len(chunks) - len(filtered)} short chunks)")
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

        logger.debug(f"Dynamic cutoff: {len(chunks)} → {len(kept)} chunks (cutoff={cutoff:.3f}, top={top_score:.3f}, range={score_range:.3f}, min={min_chunks})")
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

    def _build_prompt(self, question: str, context: str, query_type: str = "general", chat_history: Optional[List[Dict]] = None) -> str:
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
1. Read every source carefully. Extract ALL specific details — numbers, dates, names, conditions, definitions, amounts, limits, exceptions, and caveats.
2. Be EXHAUSTIVE: for each topic, include the primary answer AND all secondary details such as sub-types, variants, edge cases, practical tips, restrictions, and "what NOT to do" warnings found in the sources.
3. If multiple sources cover the same topic, merge ALL their details into one comprehensive description. Do not drop details just because they seem minor.
4. Cite sources inline as [Source N]. Place one citation at the end of a sentence or paragraph that covers that source — do NOT repeat the same citation on every line within the same section.
5. NEVER say information is "not provided" if it appears in any source.
6. Use structured formatting: **headings** (##) to separate major topics, **bold labels** for key terms, bullets for lists, numbered steps for procedures, and tables for comparisons or specifications.
7. Never claim that information is absent or a feature does not exist unless sources explicitly state so.
8. Prefer completeness over brevity. Include all relevant details from the sources, but do not repeat the same idea. Avoid filler introductions — go straight to the content.
9. Structure dense answers carefully: group related details under clear headings, use tables for numeric specs, and use bullet lists for multiple items. Every section should be scannable.

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

{self._format_chat_history(chat_history)}Question: {question}
{suffix}
Answer:"""

    def _format_chat_history(self, chat_history: Optional[List[Dict]]) -> str:
        """Format chat history as conversation context for the prompt."""
        if not chat_history:
            return ""
        lines = ["Previous conversation:"]
        for turn in chat_history[-5:]:  # last 5 turns
            lines.append(f"User: {turn['question']}")
            lines.append(f"Assistant: {turn['answer']}")
        lines.append("")
        return "\n".join(lines) + "\n"

    def _format_sources(self, search_results: List[Dict]) -> List[Dict]:
        """Build sources list for API response from search results."""
        return [
            {
                "doc_id": r["payload"]["doc_id"],
                "doc_title": r["payload"]["doc_title"],
                "chunk_text": r["payload"]["text"][:200] + "..." if len(r["payload"]["text"]) > 200 else r["payload"]["text"],
                "score": round(r["score"], 3),
                "page_num": r["payload"].get("page_num"),
            }
            for r in search_results
        ]

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
        """Generate answer using Gemini with retry on transient errors."""
        from .gemini_retry import gemini_retry

        response = gemini_retry(lambda: self.client.models.generate_content(
            model=self.fast_model_name,
            contents=prompt,
            config={
                "temperature": 0.4,
                "topP": 0.9,
                "maxOutputTokens": 8192,
            }
        ))
        return response.text.strip()

