import type { Document, Chat, ChatMessage, Source } from '../types'
import { useAuthStore } from '../store/authStore'

const API_BASE = '/api'

// --- Auth-aware fetch wrapper ---

let refreshPromise: Promise<boolean> | null = null

function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function authFetch(input: RequestInfo, init?: RequestInit): Promise<Response> {
  const headers = { ...getAuthHeaders(), ...(init?.headers || {}) }
  let response = await fetch(input, { ...init, headers })

  // Skip 401 refresh in B2C mode
  if (response.status === 401 && useAuthStore.getState().authRequired) {
    // Attempt single refresh (mutex to prevent races)
    if (!refreshPromise) {
      refreshPromise = useAuthStore.getState().refresh()
    }
    const ok = await refreshPromise
    refreshPromise = null

    if (ok) {
      const retryHeaders = { ...getAuthHeaders(), ...(init?.headers || {}) }
      response = await fetch(input, { ...init, headers: retryHeaders })
    } else {
      // Redirect to login
      window.location.href = '/login'
      throw new Error('Session expired')
    }
  }

  return response
}

// --- Document API ---

export async function fetchDocuments(): Promise<Document[]> {
  const response = await authFetch(`${API_BASE}/query/documents`)
  if (!response.ok) {
    throw new Error('Failed to fetch documents')
  }
  const data = await response.json()
  return data.documents
}

// --- Chat API ---

export async function createChat(name: string, docIds: string[], autoRoute: boolean = false): Promise<Chat> {
  const response = await authFetch(`${API_BASE}/chats`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      doc_ids: docIds,
      auto_route: autoRoute,
    }),
  })

  if (!response.ok) {
    throw new Error('Failed to create chat')
  }

  return response.json()
}

export async function fetchChats(): Promise<Chat[]> {
  const response = await authFetch(`${API_BASE}/chats`)
  if (!response.ok) {
    throw new Error('Failed to fetch chats')
  }
  const data = await response.json()
  return data.chats
}

export async function fetchChat(chatId: string): Promise<{ chat: Chat; messages: ChatMessage[] }> {
  const response = await authFetch(`${API_BASE}/chats/${chatId}`)
  if (!response.ok) {
    throw new Error('Failed to fetch chat')
  }
  return response.json()
}

export async function renameChat(chatId: string, name: string): Promise<Chat> {
  const response = await authFetch(`${API_BASE}/chats/${chatId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })

  if (!response.ok) {
    throw new Error('Failed to rename chat')
  }

  return response.json()
}

export async function deleteChat(chatId: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/chats/${chatId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Failed to delete chat')
  }
}

export interface ChatDeleteResult {
  chat_id: string
  success: boolean
  message: string
}

export interface BulkDeleteChatsResponse {
  results: ChatDeleteResult[]
  total: number
  successful: number
  failed: number
}

export async function bulkDeleteChats(chatIds: string[]): Promise<BulkDeleteChatsResponse> {
  const response = await authFetch(`${API_BASE}/chats/bulk-delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_ids: chatIds }),
  })

  if (!response.ok) {
    throw new Error('Failed to bulk delete chats')
  }

  return response.json()
}

export async function updateChatDocuments(chatId: string, docIds: string[]): Promise<Chat> {
  const response = await authFetch(`${API_BASE}/chats/${chatId}/documents`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_ids: docIds }),
  })

  if (!response.ok) {
    throw new Error('Failed to update chat documents')
  }

  return response.json()
}

export async function removeChatDocument(chatId: string, docId: string): Promise<Chat> {
  const response = await authFetch(`${API_BASE}/chats/${chatId}/documents/${docId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Failed to remove document from chat')
  }

  return response.json()
}

export type StreamEvent =
  | { type: 'docs_routed'; doc_ids: string[]; doc_names: string[] }
  | { type: 'retrieval_done'; sources: Source[] }
  | { type: 'chunk'; content: string }
  | { type: 'done'; message_id: string }
  | { type: 'error'; detail: string }

export async function askInChatStream(
  chatId: string,
  question: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await authFetch(`${API_BASE}/chats/${chatId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })

  if (!response.ok) {
    throw new Error('Failed to ask question in chat')
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Parse SSE lines
    const lines = buffer.split('\n')
    buffer = lines.pop() || '' // Keep incomplete line in buffer

    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.startsWith('data: ')) {
        try {
          const data = JSON.parse(trimmed.slice(6))
          onEvent(data as StreamEvent)
        } catch {
          // Skip malformed lines
        }
      }
    }
  }

  // Process any remaining buffer
  if (buffer.trim().startsWith('data: ')) {
    try {
      const data = JSON.parse(buffer.trim().slice(6))
      onEvent(data as StreamEvent)
    } catch {
      // Skip
    }
  }
}

// Feedback
export async function submitFeedback(
  chatId: string,
  messageId: string,
  feedback: 'up' | 'down'
): Promise<{ success: boolean }> {
  const response = await authFetch(`${API_BASE}/chats/${chatId}/messages/${messageId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback }),
  })
  if (!response.ok) {
    throw new Error('Failed to submit feedback')
  }
  return response.json()
}

// Document management functions

export async function uploadDocument(file: File): Promise<{ doc_id: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await authFetch(`${API_BASE}/admin/upload`, {
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
  const response = await authFetch(`${API_BASE}/admin/documents/${docId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Failed to delete document')
  }
}

export interface DocumentDeleteResult {
  doc_id: string
  success: boolean
  message: string
}

export interface BulkDeleteResponse {
  results: DocumentDeleteResult[]
  total: number
  successful: number
  failed: number
}

export async function bulkDeleteDocuments(docIds: string[]): Promise<BulkDeleteResponse> {
  const response = await authFetch(`${API_BASE}/admin/documents/bulk-delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_ids: docIds }),
  })

  if (!response.ok) {
    throw new Error('Failed to bulk delete documents')
  }

  return response.json()
}

// Utility function to open document at specific page
export function openDocumentAtPage(docId: string, pageNum: number): void {
  const url = `${API_BASE}/admin/documents/${docId}/file#page=${pageNum}`
  window.open(url, '_blank')
}
