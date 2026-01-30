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

        # Get configuration from request or environment variables
        use_hybrid = query.use_hybrid if query.use_hybrid is not None else _str_to_bool(os.getenv("USE_HYBRID_SEARCH", "true"))
        hybrid_alpha = query.hybrid_alpha if query.hybrid_alpha is not None else float(os.getenv("HYBRID_ALPHA", "0.5"))
        use_reranking = query.use_reranking if query.use_reranking is not None else _str_to_bool(os.getenv("USE_RERANKING", "true"))
        use_query_expansion = query.use_query_expansion if query.use_query_expansion is not None else _str_to_bool(os.getenv("USE_QUERY_EXPANSION", "false"))
        use_rrf = query.use_rrf if query.use_rrf is not None else _str_to_bool(os.getenv("USE_RRF", "true"))
        rerank_blending = query.rerank_blending if query.rerank_blending is not None else os.getenv("RERANKER_BLENDING", "position_aware")

        # Run RAG pipeline with validated doc_ids and configuration
        result = qa_engine.answer_question(
            question=query.question,
            top_k=query.top_k,
            doc_ids=doc_ids,
            use_hybrid=use_hybrid,
            hybrid_alpha=hybrid_alpha,
            use_reranking=use_reranking,
            use_query_expansion=use_query_expansion,
            use_rrf=use_rrf,
            rerank_blending=rerank_blending
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
