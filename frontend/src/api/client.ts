import type { Document, QueryResponse, Chat, ChatMessage } from '../types'

const API_BASE = '/api'

export async function fetchDocuments(): Promise<Document[]> {
  const response = await fetch(`${API_BASE}/query/documents`)
  if (!response.ok) {
    throw new Error('Failed to fetch documents')
  }
  const data = await response.json()
  return data.documents
}

export async function askQuestion(
  question: string,
  docIds?: string[]
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE}/query/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      doc_ids: docIds,
      top_k: 5,
    }),
  })

  if (!response.ok) {
    throw new Error('Failed to get answer')
  }

  return response.json()
}

// Chat API functions

export async function createChat(name: string, docIds: string[]): Promise<Chat> {
  const response = await fetch(`${API_BASE}/chats`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name,
      doc_ids: docIds,
    }),
  })

  if (!response.ok) {
    throw new Error('Failed to create chat')
  }

  return response.json()
}

export async function fetchChats(): Promise<Chat[]> {
  const response = await fetch(`${API_BASE}/chats`)
  if (!response.ok) {
    throw new Error('Failed to fetch chats')
  }
  const data = await response.json()
  return data.chats
}

export async function fetchChat(chatId: string): Promise<{ chat: Chat; messages: ChatMessage[] }> {
  const response = await fetch(`${API_BASE}/chats/${chatId}`)
  if (!response.ok) {
    throw new Error('Failed to fetch chat')
  }
  return response.json()
}

export async function renameChat(chatId: string, name: string): Promise<Chat> {
  const response = await fetch(`${API_BASE}/chats/${chatId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name }),
  })

  if (!response.ok) {
    throw new Error('Failed to rename chat')
  }

  return response.json()
}

export async function deleteChat(chatId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/chats/${chatId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Failed to delete chat')
  }
}

export async function askInChat(
  chatId: string,
  question: string,
  topK: number = 10
): Promise<ChatMessage> {
  const response = await fetch(`${API_BASE}/chats/${chatId}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      top_k: topK,
    }),
  })

  if (!response.ok) {
    throw new Error('Failed to ask question in chat')
  }

  const data = await response.json()
  return data.message
}

// Document management functions

export async function uploadDocument(file: File): Promise<{ doc_id: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/admin/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to upload document' }))

    // Handle duplicate error (409)
    if (response.status === 409 && errorData.detail) {
      const detail = typeof errorData.detail === 'object' ? errorData.detail : { message: errorData.detail }
      throw new Error(detail.message || 'Document already exists')
    }

    throw new Error(errorData.detail || 'Failed to upload document')
  }

  return response.json()
}

export async function deleteDocument(docId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/admin/documents/${docId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Failed to delete document')
  }
}

// Utility function to open document at specific page
export function openDocumentAtPage(docId: string, pageNum: number): void {
  const url = `${API_BASE}/admin/documents/${docId}/file#page=${pageNum}`
  window.open(url, '_blank')
}
