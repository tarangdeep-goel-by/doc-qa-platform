export interface ChatUsageInfo {
  id: string
  name: string
}

export interface Document {
  doc_id: string
  title: string
  upload_date: string
  file_size_mb: number
  chunk_count: number
  format: string
  chat_count: number
  chats: ChatUsageInfo[]
}

export interface Source {
  doc_id: string
  doc_title: string
  chunk_text: string
  score: number
  page_num?: number
}

export interface QueryResponse {
  question: string
  answer: string
  sources: Source[]
  retrieved_count: number
}

export interface Message {
  id: string
  type: 'question' | 'answer'
  content: string
  sources?: Source[]
  timestamp: Date
  filteredDocs?: string[]
}

export interface Chat {
  id: string
  name: string
  doc_ids: string[]
  created_at: string
  updated_at: string
  message_count: number
  missing_documents?: string[]
  available_documents?: { doc_id: string; title: string }[]
}

export interface ChatMessage {
  id: string
  chat_id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: Source[]
  filtered_docs?: string[]
}
