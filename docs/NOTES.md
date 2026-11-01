# Research notes: doc-qa-platform

Notes from a full read of the code, eval data and git history (77 commits, 2026-01-21 to 2026-10-11). Paths are relative to the repo root. Where a claim in older docs disagrees with the code, the code wins and the disagreement is called out.

## 1. What it is

A self-hosted RAG app for asking questions of long documents. FastAPI backend, React frontend, Qdrant for vectors, a pickled BM25 index for keywords, Google Gemini for embeddings and generation, and a local cross-encoder for reranking. Answers stream over SSE with inline `[Source N]` citations that the UI turns into clickable badges. An offline eval harness compares answers against reference answers using an LLM judge plus embedding similarity and ROUGE.

## 2. Architecture at a glance

```
frontend (React/Vite, :3000)  --REST + SSE-->  backend (FastAPI, :8000)
                                                 |-- Qdrant (:6333, collection "documents", cosine)
                                                 |-- BM25 pickle (backend/data/bm25/bm25_index.pkl)
                                                 |-- JSON/JSONL files under backend/data/
                                                 |-- Gemini API (embeddings, expansion, generation)
                                                 '-- cross-encoder (sentence-transformers, in-process CPU)
```

Wiring happens in `backend/api/main.py` (`lifespan`): builds `Embedder`, `VectorStore` (which owns the `BM25Index`), `DocumentStore`, `ChatManager`, `QAEngine`, `RAGConfig.from_env()`, `InteractionLogger`, `FeedbackStore`, and stashes them on `app.state`. The core pipeline vars are read with `os.environ[...]` so a missing one fails fast at startup; `docker-compose.yml` is meant to be the single source of defaults (commit `47e38f2`, 2026-02-01). Some ops vars still have code fallbacks: `GEMINI_FAST_MODEL` (falls back to `GEMINI_MODEL`), `CORS_ORIGINS`, `COOKIE_SECURE` (defaults to `true`), `MAX_UPLOAD_SIZE_MB`, `UPLOAD_RATE_LIMIT`, `USE_PDFPLUMBER` (defaults to `false`), `LOG_LEVEL`, the JWT expiries.

## 3. Ingestion path

Entry: `POST /api/admin/upload` in `backend/api/routers/admin.py` (rate limit `UPLOAD_RATE_LIMIT`, default `10/minute`; admin-only).

1. **Validation.** Extension allow-list (`.pdf .docx .html .htm .txt`), size limit (`MAX_UPLOAD_SIZE_MB`, default 50, checked on Content-Length and again on the bytes), magic-byte check for PDF/DOCX/HTML. Duplicate detection is by **filename only** (409 if a document with the same filename exists).
2. **Extraction** (`backend/src/document_processor.py`).
   - PDF: `pdfplumber` when `USE_PDFPLUMBER=true` (the compose default). Each page's text plus any tables converted to Markdown tables, **appended at the end of the page text** (not inline where they appear). PyPDF2 page text is used only when `USE_PDFPLUMBER` is off or pdfplumber isn't installed; a pdfplumber failure on a file is not retried with PyPDF2.
   - DOCX: paragraphs grouped into pseudo-pages of ~3000 chars.
   - HTML: BeautifulSoup `get_text`, single page. TXT: single page.
   - No OCR. Scanned PDFs yield nothing; the extractor raises "No text could be extracted" and the client gets a generic 500 "Failed to process document".
3. **Chunking.** Default is `TextChunker(structure_aware=True)` in `backend/src/chunker.py`; `USE_SEMANTIC_CHUNKING=true` switches to `SemanticChunker` (`backend/src/semantic_chunker.py`).
   - Chunking runs **per page**. Chunks never cross page boundaries, which keeps page citations exact but splits content that runs across pages.
   - Structure-aware mode: `detect_blocks()` in `backend/src/structure_detector.py` uses regexes to find table blocks (pipe rows, ASCII borders, 3+ aligned columns, at least 2 consecutive lines), list blocks (bullets/numbered/lettered, at least 3 lines) and headers (`Section 1`, `1.2 Title`, ALL-CAPS lines, Markdown `#`). Gaps between blocks are prose.
   - Prose is split on blank lines up to `CHUNK_SIZE` (2500 chars); the "overlap" is only carrying the last paragraph forward if it is shorter than `CHUNK_OVERLAP` (500). Oversized pieces fall back to sentence splits.
   - Structural blocks are kept whole up to `max_chunk_size=3000`, otherwise split on line boundaries.
   - Small pieces (< 300 chars, e.g. a lone header) are merged forward into the next piece.
   - If no structure is detected on a page, it falls back to fixed-size character chunking with a break-point search (paragraph, sentence, then word) and real 500-char overlap.
   - Each chunk gets a `section_title`: the nearest preceding header on the same page (approximate, located via `text.find(chunk[:50])`).
   - Semantic mode: sentences grouped into ~200-char segments, embedded, breakpoints where consecutive cosine similarity falls below the 25th percentile, then 500/4000 char min/max. Costs an extra embedding pass at ingest. Off by default.
4. **Enrichment.** `DocumentChunk.build_enriched_text()` in `backend/src/models.py` prefixes `[Document: <title> | Page: n | Section: s]` to the chunk. The enriched text is what gets embedded and what BM25 indexes; the raw text is what the LLM and the UI see.
5. **Embedding.** `backend/src/embedder.py`. If the model name starts with `gemini-`, it calls `client.models.embed_content` via the `google-genai` SDK in batches of 100 with `output_dimensionality` (768 by default, Matryoshka truncation). Otherwise loads a sentence-transformers model locally. No task type (RETRIEVAL_DOCUMENT vs RETRIEVAL_QUERY) is set. Calls go through `gemini_retry` (3 attempts, 2s/4s backoff on 503/429-ish errors).
6. **Structure tagging.** `detect_structure()` labels each chunk `table | list | specification | mixed | prose` and stores it in the payload under `structure`.
7. **Storage.** `VectorStore.add_document_chunks()` upserts points with random UUIDs into Qdrant collection `documents` (cosine). It then **rebuilds the whole BM25 index** by scrolling every point in Qdrant and re-pickling. Document metadata goes to `backend/data/documents.json` and the original file to `backend/data/uploads/<doc_id>.<ext>`.

Deletion (`DELETE /api/admin/documents/{doc_id}`, bulk delete) removes Qdrant points by `doc_id` filter and rebuilds BM25 again.

## 4. Query path

Two entry points share the same engine (`backend/src/qa_engine.py`):

- `POST /api/query/ask` (non-streaming, 30/minute) calls `answer_question`.
- `POST /api/chats/{chat_id}/ask` (SSE, 30/minute) calls `answer_question_stream` and persists messages, chat history, and an interaction log line. 300 s stream timeout.

### 4.1 Document scope and auto-routing

A chat has `doc_ids`. If `auto_route` is set and the chat is new and empty, `route_query()` (`backend/src/doc_router.py`) scores every chunk with BM25, sums scores per document, and keeps documents scoring at least 45% of the top document, up to 5. This runs once, on the first question; the result is saved into the chat. Empty `doc_ids` means "all documents".

### 4.2 `_retrieve()` step by step

1. **Classify + expand (one LLM call).** If expansion or decomposition is on, `_classify_and_expand` asks the fast model (`GEMINI_FAST_MODEL`, default `gemini-2.5-flash-lite`, temperature 0.2) to label the question SIMPLE/COMPLEX, write 2 paraphrases, and if COMPLEX write 2-4 sub-questions. Parsed line by line from a fixed text format. In parallel, the original question is embedded.
2. **Decomposition.** If COMPLEX with more than one sub-question, each sub-question runs the full `answer_question` pipeline in its own thread (decomposition disabled for the children), and a final LLM call synthesises the sub-answers. Sources are merged and deduped by the first 100 chars of chunk text.
3. **Expansion.** Otherwise the paraphrases are embedded in one batch. Weights: original 2.0, each variant 1.0.
4. **Adaptive alpha.** `_search_with_alpha_selection` runs `hybrid_search` three times in parallel with alpha 0.2, 0.5, 0.8 and picks the alpha whose top result scored highest. **See bug B1: alpha is ignored by `hybrid_search`, so this does nothing except cost three extra searches.**
5. **Hybrid search** (`backend/src/vector_store.py`).
   - Candidate pool per method: `min(top_k * 4, 20)`, so 20 in practice.
   - Vector: Qdrant `query_points` with an optional `MatchAny` filter on `doc_id`.
   - BM25: `rank_bm25.BM25Okapi` over enriched text. Tokeniser lowercases, keeps hyphen/slash runs together (so `FX5U-32MR/ES` is one token), drops a hand-written stop-word list and single-char tokens. Doc filtering is done by setting scores of out-of-scope chunks to -1.
   - Fusion: Reciprocal Rank Fusion with k=60, plus position bonuses of +0.05/+0.02/+0.02 for ranks 1-3 in each list. BM25 results are matched to vector results by Qdrant point id. **BM25 hits that are not already in the vector top 20 are dropped** (see B2). Fused scores are min-max normalised to 0-1.
   - Multi-query: `multi_query_hybrid_search` runs hybrid search per variant, multiplies normalised scores by the variant weight, sums per chunk, and normalises again.
   - Retrieval k is `top_k * 2` (24) when reranking is on, `top_k` (12) otherwise.
6. **Rerank.** `backend/src/reranker.py`, `cross-encoder/ms-marco-MiniLM-L-6-v2` via sentence-transformers, behind a thread lock. Default `RERANKER_BLENDING=position_aware`: by retrieval rank, ranks 1-3 get 0.75 retrieval + 0.25 rerank, 4-10 get 0.5/0.5, 11+ get 0.25/0.75. The retrieval score is the normalised 0-1 fused score; the rerank score is the raw cross-encoder logit (roughly -11 to +11). `replace` uses the logit alone. The reranker scores the raw chunk text, not the enriched text.
7. **Post-processing.**
   - Near-duplicate removal: word-set Jaccard > 0.85.
   - Noise filter: drop chunks under 50 chars (unless that would drop everything).
   - Dynamic cutoff: keep chunks within `top - ratio * (top - bottom)` where ratio is 0.8 for pools of 12 or fewer and 0.6 otherwise; at least `max(3, 50% of pool)`, at most 15.
   - Query-type boost: keyword heuristics label the question `table | list | specification | general`; matching chunk structures get +0.15 and are re-sorted.
   - Neighbour fetch: for non-prose chunks, fetch up to 2 adjacent chunks (`chunk_index ± 1`) from Qdrant and append them at the end with score 0.
8. **Confidence guard.** If nothing survives, a canned "couldn't find" answer. If reranking was **not** applied and the top score is below `min_score` (0.3), a canned low-confidence answer with sources. With reranking on (the default) the score guard never fires.
9. **Prompt.** `_build_prompt` builds one long instruction prompt: "expert technical writer", use only sources, be exhaustive, cite inline as `[Source N]` without repeating the same citation on consecutive lines, structure with headings/tables/lists, never claim information is absent unless sources say so. Includes a worked few-shot example (PLC connection steps and a made-up "XR-7" spec table). Context is `Source i: "<doc title>", Page p` followed by chunk text truncated to 2000 chars. No scores are shown to the model, on purpose. A type hint is appended for table/list/spec questions. The last 5 chat turns (answers truncated to 300 chars on save) are included as "Previous conversation".
10. **Generation.** `_generate_answer` / `_generate_answer_stream` both call the **fast model** (`gemini-2.5-flash-lite`) with temperature 0.4, top-p 0.9, max 8192 output tokens. `GEMINI_MODEL` (`gemini-2.5-flash`) is passed to `QAEngine` but not used for any generation since commit `ffadc1b` (2026-02-19). It is still used by the eval judge and the dataset generator.

### 4.3 SSE contract

Events from `/api/chats/{id}/ask`: optional `docs_routed {doc_ids, doc_names}`, then `retrieval_done {sources}`, a stream of `chunk {content}`, and `done {message_id}`, or `error {detail}`. Decomposed and early-return answers arrive as a single `chunk`.

### 4.4 Citations

- Backend: the `sources` list and the `Source N` labels in the prompt are built from the same ordered list, so `[Source N]` in a normal answer maps to `sources[N-1]`. Each source carries doc id, title, page, a 200-char snippet and the score.
- Frontend: `frontend/src/utils/citationParser.ts` rewrites `[Source N]` (and an older `(Document: "...", Chunk n)` format) into `[[N]]` markers, rendered by `components/markdown/CitationLink.tsx` as numbered pill buttons that scroll to the source in `SourcesBadge.tsx`. Out-of-range numbers are left as plain text.
- Citations are not verified: nothing checks that a cited source supports the sentence.

## 5. Other backend pieces

- `backend/src/chat_manager.py`: one directory per chat under `backend/data/chats/<chat_id>/`, holding `metadata.json` (including a `gemini_chat_history` of the last 5 turns) and `messages.json`, written atomically.
- `backend/src/interaction_logger.py`: appends each completed Q&A (question, answer, sources, latency, doc ids, RAG config, message id) to `backend/data/interactions.jsonl`.
- `backend/src/feedback_store.py`: thumbs up/down per assistant message to `backend/data/feedback.jsonl`, including the message's stored sources (200-char snippets with doc, page and score; commit `a7a0fae`).
- `backend/api/auth.py`, `backend/src/user_store.py`, `backend/api/routers/auth_router.py`: optional JWT auth. If `JWT_SECRET` is unset, every request is a sentinel `anonymous` user with role `admin`. If set (min 32 chars), access tokens (15 min) as Bearer, refresh tokens (7 days) in an HTTP-only cookie, users in SQLite `backend/data/users.db`, bcrypt passwords. `scripts/seed_admin.py` creates the first admin. `CLIENT_DOCUMENT_VIEW` lets non-admin clients see the documents page.
- `backend/scripts/rechunk_documents.py`, `backend/scripts/upload_and_eval.py`: maintenance and one-shot upload-then-eval.
- Security middleware: `nosniff`, `X-Frame-Options: DENY`, HSTS when `COOKIE_SECURE=true`; slowapi rate limits; global exception handler that hides internals.

## 6. Frontend

`frontend/` is React 18 + TypeScript + Vite + Tailwind + Zustand (`store/appStore.ts`, `authStore.ts`, `uiStore.ts`) + react-markdown with remark-gfm. Routes in `src/App.tsx`: `/login`, `/` (new chat screen that auto-creates a chat with auto-route on first message), `/chat/:chatId`, `/documents` (admin or client-document-view). Vite dev server on 3000 proxies `/api` and `/health` to 8000. The UI went through a "dark glass" redesign (2026-02-19) and then a warm amber palette (2026-02-21).

## 7. Storage

| What | Where |
|---|---|
| Vectors + chunk payloads | Qdrant `documents` collection, bind-mounted at `./qdrant_storage` |
| BM25 index (pickle of `BM25Okapi`, chunks, doc ids, point ids) | `backend/data/bm25/bm25_index.pkl` |
| Document metadata | `backend/data/documents.json` |
| Uploaded originals | `backend/data/uploads/` |
| Chats | `backend/data/chats/<chat_id>/{metadata,messages}.json` |
| Interaction log / feedback | `backend/data/interactions.jsonl`, `backend/data/feedback.jsonl` |
| Users (auth mode only) | `backend/data/users.db` |
| Eval results | `backend/evaluation/results/` (`history.jsonl` tracked; individual `*.json` gitignored, though older ones were committed before the ignore rule) |

## 8. Running it

- `cp .env.example .env`, set `GEMINI_API_KEY` (and optionally `JWT_SECRET`).
- `docker compose up --build -d qdrant backend`. Backend image is `python:3.11-slim`, code is copied in (not mounted), so code changes need a rebuild. The first start downloads the cross-encoder from Hugging Face (commit `ea52f0c` on 2026-01-30 disabled reranking for a while because of a Hugging Face timeout).
- `cd frontend && npm ci && npm run dev`, open http://localhost:3000.
- Tests: `docker compose run --rm test` (all), or `unit-tests`, `integration-tests`, `api-tests` profiles. 348 `test_` functions across 22 files in `backend/tests/`.
- Production: `deploy.sh` installs Docker on an Ubuntu VPS, clones the repo (placeholder URL `<your-username>`), and runs `docker-compose.yml` + `docker-compose.prod.yml`. The prod overlay exposes the **backend only** on port 80 with `CORS_ORIGINS: "*"`. Nothing builds or serves the frontend in production; the Caddy service is commented out.

### Config (set in `docker-compose.yml` unless noted)

| Var | Default | Used for |
|---|---|---|
| `GEMINI_API_KEY` | from `.env` | all Gemini calls |
| `GEMINI_MODEL` | `gemini-2.5-flash` | eval judge, dataset generator (not answer generation) |
| `GEMINI_FAST_MODEL` | `gemini-2.5-flash-lite` | classify/expand, answer generation, synthesis |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | `gemini-embedding-001` / `768` | embeddings, Qdrant vector size |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | reranking |
| `USE_RERANKING` | `true` | load and use the cross-encoder |
| `RERANKER_BLENDING` | `position_aware` | or `replace` |
| `USE_HYBRID_SEARCH` | `true` | vector + BM25 |
| `HYBRID_ALPHA` | `0.5` | no effect (see B1) |
| `USE_ADAPTIVE_ALPHA` | `true` | no effect beyond extra searches (see B1) |
| `USE_QUERY_EXPANSION` / `QUERY_EXPANSION_VARIANTS` | `true` / `2` | paraphrase fusion |
| `USE_QUERY_DECOMPOSITION` | `true` | sub-question answering |
| `TOP_K_RESULTS` | `12` | base k |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `2500` / `500` | chunker |
| `USE_SEMANTIC_CHUNKING` | `false` | semantic chunker |
| `USE_PDFPLUMBER` | `true` | table-aware PDF extraction |
| `BM25_CACHE_DIR` | `data/bm25` | BM25 pickle |
| `QDRANT_HOST` / `QDRANT_PORT` | `qdrant` / `6333` | |
| `DATA_DIR` / `UPLOAD_DIR` | `data` / `data/uploads` | |
| `JWT_SECRET`, `JWT_ACCESS_EXPIRY_MINUTES`, `JWT_REFRESH_EXPIRY_DAYS` | empty / 15 / 7 | auth mode |
| `CORS_ORIGINS`, `COOKIE_SECURE`, `MAX_UPLOAD_SIZE_MB`, `UPLOAD_RATE_LIMIT`, `LOG_LEVEL`, `CLIENT_DOCUMENT_VIEW` | | ops (`UPLOAD_RATE_LIMIT` is not in compose; code default `10/minute`) |

## 9. Evaluation harness

Code: `backend/evaluation/`.

- `run_evaluation.py`: CLI. `--dataset`, `--output`, `--doc-ids`, `--no-judge`, `--ablation`, `--html`, `--label`, `--reingest` (drop the collection and re-chunk every stored upload first), `--compare A B`. Auto-detects standalone vs conversational datasets. Runs each question through `qa_engine.answer_question` with the live `RAGConfig`, scoped to all documents in `data/documents.json` unless `--doc-ids` is given. Appends a summary line to `results/history.jsonl`.
- `metrics/answer_quality.py`:
  - ROUGE-L and ROUGE-1 F1 on whitespace tokens.
  - Semantic similarity: cosine of the system answer vs the reference answer, embedded with whatever `EMBEDDING_MODEL` the pipeline is using (Gemini now; MiniLM in the early MiniLM runs, so similarity across an embedding-model change is not like-for-like).
  - LLM-as-judge: `GEMINI_MODEL` (gemini-2.5-flash, temperature 0.1) sees the question, a reference answer labelled "gold standard" and the system answer, and scores relevance, completeness, accuracy, organisation on 1-5 in a fixed line format, plus a one-paragraph explanation. `overall` is the mean of the non-zero dimension scores. Parse failures score 0.
- `metrics/retrieval.py`: Precision/Recall/NDCG@1,3,5,10 and MRR. A source counts as relevant if it matches an `expected_sources` entry by page (`"p.22"`), title substring, or snippet substring.
- `metrics/performance.py`: p50/p95/p99/mean/max latency.
- `reporters/`: console and HTML reports, including baseline-vs-experiment comparison.
- `_run_ablation`: ablations (no expansion, no reranking, no adaptive alpha, vector only). Each runs the full pipeline but only scores retrieval metrics, so with no `expected_sources` the ablation output is all zeros.
- Conversational mode replays multi-turn conversations with chat history built the same way as production and reports judge scores by turn position and for context-dependent turns.
- `generate_dataset.py`: uploads a PDF to the Gemini File API, asks `GEMINI_MODEL` to write N questions, then answers each with the whole PDF in context ("oracle" answers). Used for `nvc.json`.
- `history.py`, `view_history.py`, `backfill_history.py`: the JSONL ledger, a viewer with filters, and a one-off import of older result files.

### Datasets (`backend/evaluation/datasets/`)

| File | Questions | Reference answers from |
|---|---|---|
| `fx5u_qa_benchmark.json` | 24 | Claude.ai chat with the Mitsubishi FX5U hardware manual |
| `atomic habits.json` | 28 | Claude.ai chat with the book |
| `separation-letter.json` | 28 | Claude.ai chat with an anonymised separation agreement |
| `real_world_multi_doc.json` | 77 | union of the three above, minus "what is this about" questions |
| `conversational_multi_doc.json` | 6 conversations, 18 turns | stored as `claude_answer`; origin not recorded |
| `nvc.json` | 30 | Gemini oracle via `generate_dataset.py` |

**No dataset has `expected_sources` filled in**, and the conversational runner passes `[]`. Every retrieval metric is therefore 0.0 (precision/recall/NDCG return 0 when there is no ground truth) in every result file except the first three on 2026-02-01 (`baseline_`, `reranking_enabled_`, `reranking_fixed_2026-02-01.json`, 4 FX5U questions), which show non-zero MRR/NDCG from expected sources that were never committed. Apart from those, retrieval was never scored. What the judge scores is the answer.

### Recorded results

From `backend/evaluation/results/history.jsonl` (45 lines) and result files:

Early experiments, 2026-02-01, FX5U 4-question set, semantic similarity of answer vs reference (from `PROJECT_STATUS.md` and the result files):

| Step | Sim |
|---|---|
| Baseline: all-MiniLM-L6-v2, reranking off | 0.742 |
| + reranking, with min-score bug fixed | 0.779 |
| + gemini-embedding-001 (768d) | 0.893 |
| + BM25 tokeniser/stop words + chunk dedup | 0.897 |

The "+21% similarity" in commit `496ce3e` is 0.742 to 0.897 on 4 questions. Most of it is the embedding step, and see the caveat below: similarity is computed with the pipeline's own embedder.

MiniLM vs Gemini embeddings, same config (baseline files, 10 questions total). Caveat: the similarity metric uses the pipeline's embedder, so the MiniLM column is scored with MiniLM embeddings and the Gemini column with Gemini embeddings. The jump mixes a retrieval change with a change of ruler. ROUGE-L in the same files barely moves except on FX5U (0.114 to 0.161; Atomic Habits 0.167 to 0.160; Separation 0.174 to 0.182), and no judge was run:

| Dataset | MiniLM | Gemini |
|---|---|---|
| FX5U (4q) | 0.719 | 0.896 |
| Atomic Habits (3q) | 0.798 | 0.877 |
| Separation (3q) | 0.779 | 0.905 |

Chunk size sweep (`PROJECT_STATUS.md`, 2026-02-02; result files not in repo): 2500/500 best on avg similarity (0.893) vs 3000/600 (0.782), 1500/300 (0.846), 1000/200 (0.839), 1000/400 (0.799), 500/100 (0.820).

Completeness rounds (`PROJECT_STATUS.md`, 2026-02-04): judge completeness 2.00 to 2.78 to 3.17 average over small sets (round 3 over two sets only, FX5U crashed) after structure detection/noise filtering, dynamic cutoff + few-shot prompt, then adaptive min-chunks + "never claim absent" rule. One FX5U round crashed.

v2.0 datasets (2026-02-05): judge overall 4.31 FX5U, 4.87 Atomic Habits, 4.29 Separation, 4.49 average (`PROJECT_STATUS.md`); the only result file kept, `separation_v2_benchmark.json`, is misnamed: it holds the Atomic Habits run (28q, 4.87).

Multi-doc 77-question runs (all three documents in the index, judge = gemini-2.5-flash; dates are `history.jsonl` timestamps, which are UTC, so 02-17 18:34 is 02-18 in IST):

| Date | Label | Overall | Completeness | Sim | p50 latency |
|---|---|---|---|---|---|
| 02-06 | before doc-id fix (first run) | 2.88 | 2.31 | 0.749 | 18.5 s |
| 02-06 | before doc-id fix (second run) | 2.85 | 2.31 | 0.740 | 19.9 s |
| 02-06 | after doc-id fix (PROJECT_STATUS only, file not in repo) | 4.72 | 4.40 | 0.865 | 11.3 s |
| 02-17 | pre-cleanup baseline, patched | 3.69 | 3.18 | 0.823 | 23.2 s |
| 02-18 | steps 1-9 perf work (answers on flash-lite, inferred) | 3.67 | 3.08 | 0.791 | 7.7 s |
| 02-18 | steps 1-9, full flash for answers | 3.81 | 3.21 | 0.808 | 16.3 s |
| 02-18 | post-cleanup | 3.73 | 3.22 | 0.803 | 17.7 s |
| 02-18 | structure-aware chunking | 3.76 | 3.27 | 0.788 | 5.3 s |
| 02-18 | structure-aware + separation PDF uploaded | 4.62 | 4.42 | 0.868 | 5.1 s |
| 02-18 | NVC (30q, Gemini oracle refs) | 4.58 | 3.97 | 0.925 | 6.0 s |

Per-document breakdown of the 02-17 and 02-18 runs shows the separation questions scoring about 2/5 while FX5U was 4.1 to 4.6 and Atomic Habits about 4.9. `PROJECT_STATUS.md` says the separation PDF had not been uploaded to that instance, and the result files agree: none of their retrieved sources is the separation agreement; once it was, the separation set went to 4.67. So the dips between 4.72 and 3.7 were an eval-environment problem, not a pipeline regression. Worth saying out loud, because the headline numbers move more with eval setup than with RAG changes.

Latency: the 02-18 perf pass (parallel classify+embed, batch embedding of variants, one combined classify/expand call, parallel sub-questions, raw-score alpha selection) took p50 from 23.2 s to 16.3 s with answers still on gemini-2.5-flash (judge 3.69 to 3.81, per commit `764b0c8`). The 7.7 s run (judge 3.67) most likely answered with flash-lite (inferred: its label doesn't say, the config records only `fast_model`, and the next run is labelled "full flash model for answer generation"). If so, most of the drop to 7.7 s is the model switch: flash gained 0.14 judge points and doubled p50. The final config uses flash-lite for answers.

### Eval caveats

- Reference answers come from Claude.ai (three sets) or Gemini with the whole PDF (NVC). The judge is Gemini. Judge and NVC oracle are the same model family.
- Small n for the early experiments (4 to 10 questions).
- Judge temperature 0.1 but single sample, no repeats, no variance reported.
- Judge "completeness" is measured against long chat-style reference answers, which rewards verbose answers; this is visible in the prompt drifting to "be EXHAUSTIVE".
- No retrieval ground truth (see above).

## 10. Evolution (git history)

All commits by Tarang. 76 commits between 2026-01-21 and 2026-02-21, then a README commit on 2026-10-11. The history is linear. Eight stages; from stage 4 on, each change has an eval result behind it. "Why" below is quoted or paraphrased from commit messages, `PROJECT_STATUS.md`, `PLANNER.md` or result files; where nothing records it, it says so.

### Stage 1: Naive RAG (2026-01-21 to 01-22)

- Commits: [5a426f8](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/5a426f8), [334dbb2](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/334dbb2).
- What: PDF only, PyPDF2, fixed 1000/200 character chunks, local `all-MiniLM-L6-v2` (384d), Qdrant top-10 by cosine, a ~140-line `qa_engine.py` with a short "answer ONLY from the context" prompt to `gemini-2.5-flash` (the commit message says Gemini 2.0 Flash; code and compose say 2.5). Sources cited as `Document, Chunk n`. `334dbb2` added the React frontend, multi-chat backend (`chat_manager.py`, `routers/chats.py`), page numbers on chunks and filename duplicate detection.
- Why: `IMPLEMENTATION_PLAN.md` describes the goal as a multi-chat interface "with improved citations and two deployment variants (B2B SaaS and D2C)". Nothing was measured.

### Stage 2: Hybrid search and a reranker (2026-01-22)

- Commits: [27e66a6](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/27e66a6), then about seven test and Docker-test commits the same day (`4d65d02` to `e875a59`).
- What: `bm25_index.py` (`rank_bm25`), `hybrid_search` combining vector and BM25 by weighted average `alpha * vector + (1 - alpha) * bm25` (alpha 0.5), `reranker.py` with `cross-encoder/ms-marco-MiniLM-L-6-v2`, and a `min_score=0.3` low-confidence guard.
- Why: the commit lists them as plan phases 2 to 4 with no measurement. `PLANNER.md` (committed 02-01) gives "better recall than pure semantic search" for hybrid. No record of what prompted adding them on day two.

### Stage 3: RRF, query expansion, rank-aware blending (2026-01-29 to 01-30)

- Commits: [1ad06bc](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/1ad06bc), [5a22cbe](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/5a22cbe), [ea52f0c](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/ea52f0c).
- What: "QMD-inspired" changes. Query expansion (2 Gemini paraphrases, original weighted 2x). Reciprocal rank fusion with k=60 and +0.05/+0.02/+0.02 for ranks 1-3, default via `USE_RRF=true`; the weighted branch stayed in code behind the flag. Position-aware rerank blending (75/25, 50/50, 25/75 by rank). Then migration to `google-genai` because `google-generativeai` was deprecated, and `USE_RERANKING=false` because the backend timed out at startup downloading the cross-encoder.
- Why: commit says RRF is "more robust to different score distributions" than weighted averaging (which min-max normalised each list first); `PLANNER.md` says the same. The "expected improvement" percentages in `1ad06bc` are estimates, not measurements. What QMD is isn't recorded (`PROJECT_STATUS.md` expands it as "Query-based Multi-modal Document understanding", which is unverified).

### Stage 4: The first eval suite (2026-02-01 to 02-02)

- Commits: [496ce3e](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/496ce3e), [4614fe7](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/4614fe7), [ba8c59f](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/ba8c59f), [47e38f2](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/47e38f2), [31f9579](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/31f9579).
- What: `backend/evaluation/` (similarity, ROUGE, retrieval metrics, LLM judge, reporters, upload-and-eval). Reference answers from Claude.ai. Changes run through it on 4 FX5U questions (result files committed): baseline MiniLM, reranker off 0.742; reranker on 0.570; reranker on with min-score guard skipped 0.779; `gemini-embedding-001` 768d 0.893; regex BM25 tokeniser, stop words, Jaccard dedup 0.897. Chunks moved from 1000/200 to 2500/500 in `496ce3e`. Semantic chunker added and left off. Query decomposition added and left on. All config defaults moved into `docker-compose.yml` with `os.environ[...]` in code.
- Why, with evidence:
  - Reranker fix: cross-encoder scores run about -10 to +10, so blended scores fell under the 0.3 guard and valid questions got "not enough information" (`PROJECT_STATUS.md`, `reranking_enabled_2026-02-01.json` at 0.570). The guard is skipped whenever reranking runs (see B4).
  - Gemini embeddings: biggest single gain in `496ce3e`; repeated across 3 datasets in `47e38f2` (FX5U 0.719 to 0.896, Atomic Habits 0.798 to 0.877, Separation 0.779 to 0.905). Caveat: similarity uses the pipeline's embedder, so each side was scored with its own model. ROUGE-L barely moved except FX5U; no judge ran.
  - Semantic chunking dropped: `4614fe7` says fixed-size "performs better on technical manuals with tables" (FX5U 0.897 vs 0.885). In `ba8c59f`'s files: Atomic Habits fixed 0.882 vs semantic 0.867, Separation 0.891 both (semantic higher ROUGE-L). Kept behind `USE_SEMANTIC_CHUNKING=false`; never re-tested against the later structure-aware chunker. Caveat: the FX5U fixed figure (0.897) is the 10:09 `bm25_dedup` run; the same fixed config re-run at 10:55 (`fx5u_fixed`) scored 0.772, so run-to-run noise on 4 questions exceeds the 0.012 gap. The semantic chunker (embedding breakpoints) and the stage 7 structure-aware chunker (regex layout detection, fixed-size fallback) are different things; the latter replaced plain fixed-size, not semantic.
  - Decomposition kept: FX5U 0.772 to 0.885, Atomic Habits +0.003, Separation +0.011 (`ba8c59f`).
  - Chunk size: why 2500 was chosen in `496ce3e` isn't recorded. A sweep on 02-02 (`PROJECT_STATUS.md`; files not in repo) confirmed 2500/500 at 0.893 against 0.782 to 0.846.
  - Config in compose: `47e38f2` title pairs it with a "clean eval baseline"; the API and eval read the same values.
- Dropped: semantic chunking as default; `QUERY_EXPANSION_WEIGHT`, `RRF_K_PARAMETER`, `RRF_TOP_BONUSES`, `MIN_CONFIDENCE_SCORE` env vars.

### Stage 5: Judge-driven tuning, bigger datasets (2026-02-02 to 02-12)

- Commits: [b273afa](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/b273afa), [70125f3](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/70125f3), [e191cba](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/e191cba), [b3d2bd6](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/b3d2bd6), [1e8a7a0](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/1e8a7a0), [068abf6](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/068abf6), [b2321aa](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/b2321aa), [6e606c5](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/6e606c5), [a961d4f](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/a961d4f), [345bd19](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/345bd19), [cc7454d](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/cc7454d), [fad9326](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/fad9326), [95ec1fa](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/95ec1fa).
- What and why:
  - The 02-02 judge baseline scored relevance 4.0, completeness 2.3 (`PROJECT_STATUS.md`). `b273afa` ran three rounds against completeness: structure tagging + query-type boost + noise filter; dynamic cutoff + few-shot prompt + temperature 0.4 + top-and-tail ordering; adaptive min-chunks + max 15 + "never claim absent" rule. Average completeness 2.00, 2.78, 3.17 (small sets; the FX5U round-3 run crashed, so 3.17 averages only Atomic Habits 4.00 and Separation 2.33). A separation question failed because an annexure table was never extracted.
  - Datasets to 80 questions (`b3d2bd6`): judge 4.49 average. API key moved out of compose (`e191cba`).
  - `068abf6`: pdfplumber with tables as Markdown, the 77-question multi-doc set, adaptive alpha. Adaptive alpha was added while `USE_RRF=true` was already the default, so it never affected the default pipeline (B1).
  - `1e8a7a0`: the first two multi-doc runs scored 2.88 and 2.85 because the eval resolved doc ids by fuzzy-matching titles (FX5U questions searched Atomic Habits; the result files retrieve only Atomic Habits chunks). Fixed to all-docs, with pdfplumber added in the same batch: 4.72 (`PROJECT_STATUS.md` only; no result file or history line). Same commit added `history.jsonl` and wired decomposition and adaptive alpha into the eval, where they had been silently missing.
  - `b2321aa`: one `RAGConfig` dataclass to end "the silent-missing-params class of bugs"; judge JSON mode; 4.45/5 after cleanup.
  - `6e606c5`: retry with backoff because 503/429 errors were landing in eval scores as error strings. `a961d4f`: exhaustive prompt, +0.46 completeness on FX5U. `345bd19`: interaction log, thumbs up/down. `cc7454d`: auto-routing, chat history in prompts, conversational eval.
  - 02-12: `fad9326` deleted the weighted-fusion branch and the `use_rrf` toggle, and removed top-and-tail ordering ("dubious with Gemini's 2M context"); `95ec1fa` switched alpha selection to raw scores, "equivalent quality, 2.3-3.0x faster" on 175 questions, consistent with alpha doing nothing.
- Dropped: weighted fusion, top-and-tail reordering, eval doc-id fuzzy matching.

### Stage 6: Latency pass (2026-02-18)

- Commits: [851520f](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/851520f), [764b0c8](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/764b0c8).
- What: `851520f` put the pre-cleanup (`94ac368`, 02-07) engine back with three minimal patches as a baseline (this also brought the weighted branch back temporarily). `764b0c8` applied nine steps: retry wrapper, logger, raw-score alpha, parallel alpha searches, batched variant embedding, parallel sub-questions, one combined classify+expand+sub-question call on flash-lite, prompt tweaks, `_retrieve()` refactor with streaming.
- Evidence (77 questions, `history.jsonl`): baseline 3.69, p50 23.2 s; nine steps with answers on `gemini-2.5-flash` 3.81, 16.3 s; nine steps with answers on flash-lite 3.67, 7.7 s (inferred from the next run's label "full flash model for answer generation"; the config records only `fast_model`). `764b0c8` shipped flash for answers.
- Note: all three runs had separation questions at about 2/5 (see stage 7).

### Stage 7: Structure-aware chunking (2026-02-18 to 02-19)

- Commits: [ffadc1b](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/ffadc1b), [aeea6d3](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/aeea6d3), [d64323a](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/d64323a).
- What: structure-first chunking (tables, lists, headers never split; prose by paragraph; fixed-size fallback), `[Document | Page | Section]` enriched text for embedding and BM25, ±1 neighbour fetch for structured chunks, removal of a whitespace collapse that flattened tables, DOCX/HTML/TXT, `USE_RRF` toggle removed for good, `--reingest` in the eval. Answer generation moved from `GEMINI_MODEL` to `GEMINI_FAST_MODEL` (flash-lite); the commit doesn't say why, the stage 6 runs are the only recorded evidence. BM25 matched to Qdrant points by id (`aeea6d3`).
- Evidence: structure-aware run 3.76, 5.3 s; with the separation PDF actually uploaded, 4.62, completeness 4.42, similarity 0.868, p50 5.1 s. `PROJECT_STATUS.md` attributes the separation jump (2.50 to 4.67) "primarily" to the upload; Atomic Habits 4.63 to 4.86, FX5U 4.33 to 4.29, against a 3.79 / 6.3 s "before" run that is not in `history.jsonl`. The p50 drop from ~17 s (post-cleanup run) to ~5 s most likely comes from the flash-lite switch in the same commit rather than chunking. So the mid-February 3.7 runs were an eval-environment problem, not a regression. NVC set generated by `d64323a`: 4.58.

### Stage 8: Auth and hardening (2026-02-19 to 02-21)

- Commits: [6d0ea31](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/6d0ea31), [2568d0a](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/2568d0a), [40577bb](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/40577bb), [909954c](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/909954c), [d281127](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/d281127), [2ce0e66](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/2ce0e66), [1505b49](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/1505b49), [a7a0fae](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/a7a0fae), [6c5a4be](https://github.com/tarangdeep-goel-by/doc-qa-platform/commit/6c5a4be).
- What and why: optional JWT auth, "single codebase for SaaS + B2C" (matches the two variants in the January plan). Rate limits, upload size and magic-byte checks, path traversal, stream timeout, non-root container, healthchecks, prod overlay, VPS deploy script. Dark UI then amber palette, "Add document" flow, retrieved chunks stored with feedback, 181 unit tests. Whether it was deployed isn't recorded.

### After

- **2026-10-11** Product and architecture README (PR #2, `02935e6`).

## 11. Decisions and trade-offs (as visible in code and commits)

- **Gemini embeddings over local MiniLM.** Measured +0.08 to +0.18 answer similarity on the small sets, though each side was scored with its own embedder, so the size of the gain is uncertain. Cost: every chunk and every query leaves the machine, and an API key is mandatory.
- **Local cross-encoder** rather than an API reranker. Free and private, but CPU-bound and serialised behind a lock.
- **BM25 in-process with a pickle** rather than Qdrant sparse vectors or a search engine. Simple; full rebuild on every upload/delete, whole corpus in memory, single process only.
- **RRF over weighted fusion.** Avoids calibrating BM25 and cosine scales. The alpha knob survived the switch without being wired back in.
- **Flash-lite for answers.** Latency over a small judge-score gain.
- **Chunks bounded by pages.** Exact page citations at the cost of cross-page content.
- **Compose as the only config source.** Fast failure on missing vars; the eval and the API read the same values.
- **Files and JSON for state.** Easy to inspect and back up, single-instance only.
- **Exhaustive prompt.** Chosen to lift judge completeness against long reference answers.

## 12. Bugs and limitations found while reading

- **B1. Adaptive alpha and `HYBRID_ALPHA` are no-ops.** `VectorStore.hybrid_search` accepts `alpha` but RRF never uses it. Alpha only mattered in the weighted-fusion branch, which RRF replaced as the default on 2026-01-29 and which was deleted on 2026-02-12 (briefly restored for the 02-18 pre-cleanup baseline, removed for good on 2026-02-19). Adaptive alpha itself was added on 2026-02-06, with `USE_RRF=true` already the default, so it never affected the default pipeline. `_search_with_alpha_selection` therefore runs three identical searches and picks 0.2 (the top fused score is always 1.0 after min-max normalisation, so all three tie and the first wins). It adds latency and nothing else. The 2026-02-12 benchmark showing "equivalent quality" between reranker-scored and raw-score alpha selection is consistent with this.
- **B2. BM25-only hits are discarded.** In `_reciprocal_rank_fusion` a BM25 result contributes only if its point id is already in the vector top 20. Keyword search re-orders semantic candidates but cannot add new ones, which undercuts the main reason to have BM25 (exact part numbers, rare terms).
- **B3. Score scales mixed in position-aware blending.** A 0-1 normalised retrieval score is blended with an unbounded cross-encoder logit, so the "75% retrieval" weight for the top 3 mostly acts as damping of the logit rather than a trust weighting.
- **B4. Low-confidence guard disabled in default config.** The min-score check is skipped whenever reranking ran, so with defaults the system always answers if any chunk was retrieved.
- **B5. Citation numbering for decomposed answers.** Each sub-answer cites `[Source N]` against its own source list; the synthesised answer keeps those numbers, but the returned `sources` are a merged, deduped list. Citations in decomposed answers can point to the wrong source.
- **B6. Follow-ups are retrieved without history.** Chat history is used in the prompt but not in retrieval or query rewriting, so "what about the second one?" is embedded as-is.
- **B7. Retrieval metrics are always zero** because no dataset has `expected_sources`.
- **B8. `GEMINI_MODEL` is labelled the main generation model** in older docs but only the judge and dataset generator use it.
- **B9. Duplicate check is by filename.** Same content under a different name is indexed twice; a different file with the same name is rejected.
- **B10. Tables are appended to the end of each page** by the pdfplumber path, separated from their surrounding text, and the same table text can appear twice (once flattened by `extract_text`, once as Markdown).
- **B11. Production overlay** exposes only the API with `CORS_ORIGINS="*"`; the frontend has no production build or host. `deploy.sh` clones a placeholder URL.
- **B12. Root clutter.** `IMPLEMENTATION_COMPLETE.md`, `IMPLEMENTATION_PLAN.md`, `PLANNER.md`, `PROGRESS.md`, `TODO.md`, several testing guides and `PROJECT_STATUS.md` are planning logs with partly stale details (e.g. "top-and-tail reordering", which is no longer in the code).
- No OCR, no image understanding, no per-user document isolation (documents are global; chats are per user).
- BM25 rebuild and Gemini embedding run inline in the upload request, so large documents block the request.

## 13. Open questions for Tarang

- What were the source documents chosen for (FX5U manual, Atomic Habits, separation letter, NVC), and was any of this used by anyone else?
- Was the SaaS/B2C auth split aimed at a real deployment?
- What is QMD in the commit message, for attribution?
- Why the gap between February and the October README?
