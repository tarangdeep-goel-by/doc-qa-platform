"""Admin endpoints for document management."""

import logging
import os
import time
import uuid

logger = logging.getLogger(__name__)
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Query, Depends
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
UPLOAD_RATE_LIMIT = os.environ.get("UPLOAD_RATE_LIMIT", "10/minute")

from api.schemas import (
    UploadResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    DeleteResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
    DocumentDeleteResult
)
from api.auth import require_admin, get_current_user
from api.helpers import build_document_list
from src.models import DocumentMetadata, DocumentChunk
from src.user_store import User
from src.document_processor import DocumentProcessor
from src.chunker import TextChunker
from src.semantic_chunker import SemanticChunker
from src.structure_detector import detect_structure

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
@limiter.limit(UPLOAD_RATE_LIMIT)
async def upload_document(request: Request, file: UploadFile = File(...), _: User = Depends(require_admin)):
    """
    Upload and process a document.

    Accepts: PDF, DOCX, HTML, TXT files
    Returns: Document ID and processing stats
    """
    start_time = time.time()

    # Validate file type
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.html', '.htm', '.txt'}
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Enforce upload size limit
    max_upload_mb = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50"))
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size: {max_upload_mb}MB")

    # Get app state
    embedder = request.app.state.embedder
    vector_store = request.app.state.vector_store
    document_store = request.app.state.document_store
    upload_dir = request.app.state.upload_dir
    chunk_size = request.app.state.chunk_size
    chunk_overlap = request.app.state.chunk_overlap

    # Check for duplicate by filename
    duplicate = document_store.find_by_filename(file.filename)

    if duplicate:
        raise HTTPException(
            status_code=409,  # Conflict
            detail={
                "error": "duplicate_document",
                "message": f"Document '{file.filename}' already exists",
                "existing_doc_id": duplicate.doc_id,
                "existing_upload_date": duplicate.upload_date,
                "suggestion": "Use the existing document or rename your file"
            }
        )

    # Generate document ID
    doc_id = str(uuid.uuid4())
    file_extension = ext.lstrip('.')
    saved_filename = f"{doc_id}.{file_extension}"
    file_path = os.path.join(upload_dir, saved_filename)

    try:
        # Read and validate file content
        content = await file.read()

        # Enforce size limit (in case Content-Length was missing/spoofed)
        if len(content) > max_upload_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File too large. Maximum size: {max_upload_mb}MB")

        # Validate magic bytes
        MAGIC_SIGNATURES = {
            '.pdf': [b'%PDF'],
            '.docx': [b'PK\x03\x04'],
            '.html': [b'<!DOCTYPE', b'<!doctype', b'<html', b'<HTML'],
            '.htm': [b'<!DOCTYPE', b'<!doctype', b'<html', b'<HTML'],
        }
        expected_sigs = MAGIC_SIGNATURES.get(ext.lower())
        if expected_sigs and not any(content.lstrip()[:16].startswith(sig) for sig in expected_sigs):
            raise HTTPException(status_code=400, detail="File content does not match expected format")

        # Save uploaded file
        logger.info(f"Saving file: {file.filename}")
        with open(file_path, "wb") as f:
            f.write(content)

        # Process document
        logger.info(f"Processing document: {file.filename}")
        use_pdfplumber = os.environ.get("USE_PDFPLUMBER", "false").lower() == "true"
        processor = DocumentProcessor()
        page_data, metadata = processor.process_document(file_path, file_extension, use_pdfplumber=use_pdfplumber)
        if use_pdfplumber:
            logger.info("Using pdfplumber for table-aware extraction")

        # Get file size
        file_size_mb = processor.get_file_size_mb(file_path)

        # Chunk text with page tracking (structure-aware by default)
        use_semantic = getattr(request.app.state, "use_semantic_chunking", False)
        if use_semantic:
            logger.info("Chunking text (semantic)...")
            chunker = SemanticChunker(embedder=embedder)
            chunk_data = chunker.chunk_with_page_tracking(page_data)
        else:
            logger.info("Chunking text (structure-aware)...")
            chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap, structure_aware=True)
            chunk_data = chunker.chunk_with_page_tracking(page_data)
        logger.info(f"Created {len(chunk_data)} chunks")

        if not chunk_data:
            raise ValueError("No text chunks created from document")

        # Create document chunks with section titles and enriched text
        doc_title = metadata.get('title') or file.filename
        chunks = []
        for i, chunk in enumerate(chunk_data):
            dc = DocumentChunk(
                text=chunk['text'],
                doc_id=doc_id,
                doc_title=doc_title,
                chunk_index=i,
                page_num=chunk['page_num'],
                section_title=chunk.get('section_title', ''),
                metadata=metadata,
            )
            dc.build_enriched_text()
            chunks.append(dc)

        # Generate embeddings using enriched text (includes context headers)
        logger.info("Generating embeddings...")
        chunk_texts = [c.enriched_text or c.text for c in chunks]
        embeddings = embedder.embed_texts(chunk_texts)
        logger.info(f"Generated {len(embeddings)} embeddings")

        # Detect structure in each chunk and enrich payload
        logger.info("Detecting chunk structures...")
        chunk_payloads = []
        structure_counts = {"table": 0, "list": 0, "specification": 0, "prose": 0, "mixed": 0}
        for c in chunks:
            payload = c.to_payload()
            structure = detect_structure(c.text)
            payload["structure"] = structure
            chunk_payloads.append(payload)
            structure_counts[structure["structure_type"]] = structure_counts.get(structure["structure_type"], 0) + 1
        logger.info(f"Structure types: {structure_counts}")

        # Store in Qdrant
        logger.info("Storing in Qdrant...")
        chunks_added = vector_store.add_document_chunks(chunk_payloads, embeddings)
        logger.info(f"Stored {chunks_added} chunks in Qdrant")

        # Save document metadata
        doc_metadata = DocumentMetadata(
            doc_id=doc_id,
            title=doc_title,
            filename=file.filename,
            file_path=file_path,
            format=file_extension,
            upload_date=datetime.now().isoformat(),
            file_size_mb=file_size_mb,
            chunk_count=len(chunk_data),
            total_pages=metadata.get('total_pages'),
            metadata=metadata
        )
        document_store.save_document(doc_metadata)

        processing_time = time.time() - start_time
        logger.info(f"Document processed successfully in {processing_time:.2f}s")

        return UploadResponse(
            doc_id=doc_id,
            title=doc_title,
            status="success",
            chunk_count=len(chunk_data),
            processing_time=round(processing_time, 2)
        )

    except Exception:
        # Cleanup on error
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.exception("Failed to process document")
        raise HTTPException(status_code=500, detail="Failed to process document")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(request: Request, _: User = Depends(require_admin)):
    """List all uploaded documents with chat usage information."""
    document_infos = build_document_list(
        request.app.state.document_store,
        request.app.state.chat_manager
    )
    return DocumentListResponse(documents=document_infos)


@router.get("/documents/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(request: Request, doc_id: str, _: User = Depends(require_admin)):
    """Get detailed information about a document."""
    document_store = request.app.state.document_store

    doc = document_store.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetailResponse(
        doc_id=doc.doc_id,
        title=doc.title,
        filename=doc.filename,
        format=doc.format,
        upload_date=doc.upload_date,
        file_size_mb=doc.file_size_mb,
        chunk_count=doc.chunk_count,
        total_pages=doc.total_pages,
        metadata=doc.metadata
    )


@router.delete("/documents/{doc_id}", response_model=DeleteResponse)
async def delete_document(request: Request, doc_id: str, _: User = Depends(require_admin)):
    """Delete a document and its chunks from the system."""
    vector_store = request.app.state.vector_store
    document_store = request.app.state.document_store
    chat_manager = request.app.state.chat_manager

    # Get document metadata
    doc = document_store.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        # Delete from Qdrant
        logger.info(f"Deleting chunks from Qdrant for doc_id: {doc_id}")
        vector_store.delete_document(doc_id)

        # Delete file from disk
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
            logger.info(f"Deleted file: {doc.file_path}")

        # Delete metadata
        document_store.delete_document(doc_id)
        logger.info(f"Deleted document metadata: {doc_id}")

        # Count affected chats (but don't remove doc_ids - we want to show them as missing)
        all_chats = chat_manager.list_chats()
        chats_affected = sum(1 for chat in all_chats if doc_id in chat.doc_ids)

        message = f"Document '{doc.title}' deleted successfully"
        if chats_affected > 0:
            message += f". {chats_affected} chat(s) reference this document"

        return DeleteResponse(
            success=True,
            message=message
        )

    except Exception:
        logger.exception("Failed to delete document %s", doc_id)
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.post("/documents/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_documents(request: Request, bulk_request: BulkDeleteRequest, _: User = Depends(require_admin)):
    """
    Delete multiple documents at once.

    Returns status for each document deletion attempt.
    """
    vector_store = request.app.state.vector_store
    document_store = request.app.state.document_store
    chat_manager = request.app.state.chat_manager

    results = []
    successful = 0
    failed = 0

    for doc_id in bulk_request.doc_ids:
        try:
            # Get document metadata
            doc = document_store.get_document(doc_id)

            if not doc:
                results.append(DocumentDeleteResult(
                    doc_id=doc_id,
                    success=False,
                    message="Document not found"
                ))
                failed += 1
                continue

            # Delete from Qdrant
            vector_store.delete_document(doc_id)

            # Delete file from disk
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)

            # Delete metadata
            document_store.delete_document(doc_id)

            # Count affected chats
            all_chats = chat_manager.list_chats()
            chats_affected = sum(1 for chat in all_chats if doc_id in chat.doc_ids)

            message = f"'{doc.title}' deleted"
            if chats_affected > 0:
                message += f" ({chats_affected} chat(s) affected)"

            results.append(DocumentDeleteResult(
                doc_id=doc_id,
                success=True,
                message=message
            ))
            successful += 1

        except Exception:
            logger.exception("Failed to delete document %s in bulk", doc_id)
            results.append(DocumentDeleteResult(
                doc_id=doc_id,
                success=False,
                message="Delete failed"
            ))
            failed += 1

    return BulkDeleteResponse(
        results=results,
        total=len(bulk_request.doc_ids),
        successful=successful,
        failed=failed
    )


@router.get("/documents/{doc_id}/file")
async def download_document(request: Request, doc_id: str, _: User = Depends(get_current_user)):
    """
    Serve the document file.

    Can be opened in browser with #page=N anchor for specific pages.
    Any authenticated user can access (clients need for source links).
    """
    document_store = request.app.state.document_store

    doc = document_store.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # Ensure file is within upload directory (prevent path traversal)
    upload_dir = os.path.abspath(request.app.state.upload_dir)
    file_path = os.path.abspath(doc.file_path)
    if not file_path.startswith(upload_dir):
        raise HTTPException(status_code=403, detail="Access denied")

    MEDIA_TYPES = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'html': 'text/html',
        'htm': 'text/html',
        'txt': 'text/plain',
    }
    media_type = MEDIA_TYPES.get(doc.format, 'application/octet-stream')

    return FileResponse(
        doc.file_path,
        media_type=media_type,
        filename=doc.filename
    )


@router.get("/interactions")
async def get_interactions(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    chat_id: Optional[str] = Query(default=None),
    _: User = Depends(require_admin),
):
    """Get recent Q&A interactions."""
    interaction_logger = request.app.state.interaction_logger
    return interaction_logger.get_interactions(limit=limit, chat_id=chat_id)


@router.get("/feedback")
async def get_feedback(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    chat_id: Optional[str] = Query(default=None),
    feedback: Optional[str] = Query(default=None, pattern="^(up|down)$"),
    _: User = Depends(require_admin),
):
    """Get feedback entries."""
    feedback_store = request.app.state.feedback_store
    return feedback_store.get_feedback(
        limit=limit, chat_id=chat_id, feedback_filter=feedback
    )
