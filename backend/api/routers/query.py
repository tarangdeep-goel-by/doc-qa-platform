"""User query endpoints for Q&A."""

from fastapi import APIRouter, HTTPException, Request

from api.schemas import (
    QueryRequest,
    QueryResponse,
    SourceInfo,
    DocumentListResponse,
)
from api.helpers import build_document_list

router = APIRouter()


@router.post("/ask", response_model=QueryResponse)
async def ask_question(http_request: Request, query: QueryRequest):
    """
    Ask a question about uploaded documents.

    Uses RAG pipeline to retrieve relevant chunks and generate answer.
    """
    qa_engine = http_request.app.state.qa_engine
    document_store = http_request.app.state.document_store
    rag_config = http_request.app.state.rag_config

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

        # Run RAG pipeline with validated doc_ids and configuration
        result = qa_engine.answer_question(
            question=query.question,
            **rag_config.to_answer_kwargs(doc_ids=doc_ids)
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
    document_infos = build_document_list(
        request.app.state.document_store,
        request.app.state.chat_manager
    )
    return DocumentListResponse(documents=document_infos)
