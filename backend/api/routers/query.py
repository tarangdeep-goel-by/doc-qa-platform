"""User query endpoints for Q&A."""

from fastapi import APIRouter, HTTPException, Request

from api.schemas import (
    QueryRequest,
    QueryResponse,
    SourceInfo,
    DocumentListResponse,
    DocumentInfo
)

router = APIRouter()


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

        # Run RAG pipeline with validated doc_ids
        result = qa_engine.answer_question(
            question=query.question,
            top_k=query.top_k,
            doc_ids=doc_ids
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
    """List documents available for querying (same as admin endpoint)."""
    document_store = request.app.state.document_store

    docs = document_store.list_documents()

    document_infos = [
        DocumentInfo(
            doc_id=doc.doc_id,
            title=doc.title,
            upload_date=doc.upload_date,
            file_size_mb=doc.file_size_mb,
            chunk_count=doc.chunk_count,
            format=doc.format
        )
        for doc in docs
    ]

    return DocumentListResponse(documents=document_infos)
