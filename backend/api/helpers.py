"""Shared helper functions for API routers."""

from typing import List

from api.schemas import ChatUsageInfo, DocumentInfo


def build_document_list(document_store, chat_manager) -> List[DocumentInfo]:
    """Build document info list with chat associations.

    Used by both admin.py and query.py list endpoints.
    """
    docs = document_store.list_documents()
    all_chats = chat_manager.list_chats()

    document_infos = []
    for doc in docs:
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

    return document_infos
