"""User query endpoints for Q&A."""

import os
from fastapi import APIRouter, HTTPException, Request

from api.schemas import (
    QueryRequest,
    QueryResponse,
    SourceInfo,
    DocumentListResponse,
    DocumentInfo
)

router = APIRouter()


def _str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ("true", "1", "yes")


@router.post("/ask", response_model=QueryResponse)
async def ask_question(http_request: Request, query: QueryRequest):
    """
    Ask a question about uploaded documents.

    Uses RAG pipeline to retrieve relevant chunks and generate answer.
    """
    qa_engine = http_request.app.state.qa_engine
    document_store = http_request.app.state.document_store

    try:
        # Validate doc_ids if provided
        doc_ids = None
        if query.doc_ids:
            valid_doc_ids = [
                doc_id for doc_id in query.doc_ids
                if document_store.get_document(doc_id) is not None
            ]

            if not valid_doc_ids:
                return QueryResponse(
                    question=query.question,
                    answer="The specified documents are not available.",
                    sources=[],
                    retrieved_count=0
                )

            doc_ids = valid_doc_ids

        # Get configuration from environment variables
        top_k = int(os.environ["TOP_K_RESULTS"])
        use_hybrid = _str_to_bool(os.environ["USE_HYBRID_SEARCH"])
        hybrid_alpha = float(os.environ["HYBRID_ALPHA"])
        use_reranking = _str_to_bool(os.environ["USE_RERANKING"])
        use_query_expansion = _str_to_bool(os.environ["USE_QUERY_EXPANSION"])
        use_rrf = _str_to_bool(os.environ["USE_RRF"])
        rerank_blending = os.environ["RERANKER_BLENDING"]
        use_query_decomposition = _str_to_bool(os.environ["USE_QUERY_DECOMPOSITION"])
        use_adaptive_alpha = _str_to_bool(os.environ.get("USE_ADAPTIVE_ALPHA", "true"))

        # Run RAG pipeline with validated doc_ids and configuration
        result = qa_engine.answer_question(
            question=query.question,
            top_k=top_k,
            doc_ids=doc_ids,
            use_hybrid=use_hybrid,
            hybrid_alpha=hybrid_alpha,
            use_reranking=use_reranking,
            use_query_expansion=use_query_expansion,
            use_rrf=use_rrf,
            rerank_blending=rerank_blending,
            use_query_decomposition=use_query_decomposition,
            use_adaptive_alpha=use_adaptive_alpha
        )

        # Convert sources to schema format
        sources = [
            SourceInfo(
                doc_id=source["doc_id"],
                doc_title=source["doc_title"],
                chunk_text=source["chunk_text"],
                score=source["score"],
                page_num=source.get("page_num")
            )
            for source in result["sources"]
        ]

        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            sources=sources,
            retrieved_count=result["retrieved_count"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_available_documents(request: Request):
    """List documents available for querying with chat usage information."""
    document_store = request.app.state.document_store
    chat_manager = request.app.state.chat_manager

    docs = document_store.list_documents()
    all_chats = chat_manager.list_chats()

    document_infos = []
    for doc in docs:
        # Find chats that use this document
        from api.schemas import ChatUsageInfo
        doc_chats = [
            ChatUsageInfo(id=chat.id, name=chat.name)
            for chat in all_chats
            if doc.doc_id in chat.doc_ids
        ]

        document_infos.append(
            DocumentInfo(
                doc_id=doc.doc_id,
                title=doc.title,
                upload_date=doc.upload_date,
                file_size_mb=doc.file_size_mb,
                chunk_count=doc.chunk_count,
                format=doc.format,
                chat_count=len(doc_chats),
                chats=doc_chats
            )
        )

    return DocumentListResponse(documents=document_infos)
