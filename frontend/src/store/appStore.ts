import { create } from 'zustand'
import toast from 'react-hot-toast'
import type { Chat, ChatMessage, Document } from '../types'
import * as api from '../api/client'

interface AppState {
  // Chats
  chats: Chat[]
  activeChat: Chat | null

  // Documents
  documents: Document[]

  // Messages for active chat
  messages: ChatMessage[]

  // Loading states
  loading: boolean
  error: string | null

  // Actions
  loadChats: () => Promise<void>
  loadDocuments: () => Promise<void>
  setActiveChat: (chatId: string) => Promise<void>
  createChat: (name: string, docIds: string[], autoRoute?: boolean) => Promise<Chat | null>
  deleteChat: (chatId: string) => Promise<void>
  renameChat: (chatId: string, name: string) => Promise<void>
  sendMessage: (question: string) => Promise<void>
  uploadDocument: (file: File) => Promise<void>
  deleteDocument: (docId: string) => Promise<void>
  removeChatDocument: (chatId: string, docId: string) => Promise<void>
  submitFeedback: (chatId: string, messageId: string, feedback: 'up' | 'down') => Promise<void>
  clearError: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  chats: [],
  activeChat: null,
  documents: [],
  messages: [],
  loading: false,
  error: null,

  // Load all chats
  loadChats: async () => {
    try {
      set({ loading: true, error: null })
      const chats = await api.fetchChats()
      set({ chats, loading: false })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load chats',
        loading: false
      })
    }
  },

  // Load documents
  loadDocuments: async () => {
    try {
      const documents = await api.fetchDocuments()
      set({ documents })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to load documents' })
    }
  },

  // Set active chat and load messages
  setActiveChat: async (chatId: string) => {
    try {
      set({ loading: true, error: null })
      const { chat, messages } = await api.fetchChat(chatId)
      set({
        activeChat: chat,
        messages,
        loading: false
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load chat',
        loading: false
      })
    }
  },

  // Create new chat
  createChat: async (name: string, docIds: string[], autoRoute: boolean = false) => {
    try {
      set({ loading: true, error: null })
      const newChat = await api.createChat(name, docIds, autoRoute)

      // Add to chat list
      set(state => ({
        chats: [newChat, ...state.chats],
        loading: false
      }))

      return newChat
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create chat',
        loading: false
      })
      return null
    }
  },

  // Delete chat
  deleteChat: async (chatId: string) => {
    try {
      set({ loading: true, error: null })

      // Check if deleting active chat
      const isActiveChat = get().activeChat?.id === chatId

      await api.deleteChat(chatId)

      // Remove from list
      set(state => {
        const newChats = state.chats.filter(c => c.id !== chatId)
        const newActiveChat = state.activeChat?.id === chatId ? null : state.activeChat

        return {
          chats: newChats,
          activeChat: newActiveChat,
          messages: newActiveChat ? state.messages : [],
          loading: false
        }
      })

      // Show success notification
      toast.success('Chat deleted successfully')

      // Navigate to home if active chat was deleted
      if (isActiveChat) {
        window.location.href = '/'
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete chat',
        loading: false
      })
      toast.error('Failed to delete chat')
    }
  },

  // Rename chat
  renameChat: async (chatId: string, name: string) => {
    try {
      set({ loading: true, error: null })
      const updatedChat = await api.renameChat(chatId, name)

      // Update in list and active chat
      set(state => ({
        chats: state.chats.map(c => c.id === chatId ? updatedChat : c),
        activeChat: state.activeChat?.id === chatId ? updatedChat : state.activeChat,
        loading: false
      }))
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to rename chat',
        loading: false
      })
    }
  },

  // Send message in active chat (streaming)
  sendMessage: async (question: string) => {
    const { activeChat } = get()

    if (!activeChat) {
      set({ error: 'Select a chat to send messages' })
      return
    }

    try {
      set({ loading: true, error: null })

      // Create user message immediately (optimistic)
      const userMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        chat_id: activeChat.id,
        role: 'user',
        content: question,
        timestamp: new Date().toISOString()
      }

      // Create assistant placeholder (empty content, will be filled by stream)
      const assistantPlaceholderId = `stream-${Date.now()}`
      const assistantPlaceholder: ChatMessage = {
        id: assistantPlaceholderId,
        chat_id: activeChat.id,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      }

      // Add both messages to UI
      set(state => ({
        messages: [...state.messages, userMessage, assistantPlaceholder]
      }))

      let accumulatedContent = ''

      await api.askInChatStream(activeChat.id, question, (event) => {
        switch (event.type) {
          case 'docs_routed':
            // Auto-routing resolved — update active chat with routed doc_ids
            set(state => {
              const updated = {
                ...state.activeChat!,
                doc_ids: event.doc_ids,
                auto_route: false,
              }
              return {
                activeChat: updated,
                chats: state.chats.map(c => c.id === updated.id ? { ...c, doc_ids: event.doc_ids, auto_route: false } : c),
              }
            })
            break

          case 'retrieval_done':
            // Attach sources to the assistant placeholder
            set(state => ({
              messages: state.messages.map(msg =>
                msg.id === assistantPlaceholderId
                  ? { ...msg, sources: event.sources }
                  : msg
              )
            }))
            break

          case 'chunk':
            accumulatedContent += event.content
            // Update assistant message content
            set(state => ({
              messages: state.messages.map(msg =>
                msg.id === assistantPlaceholderId
                  ? { ...msg, content: accumulatedContent }
                  : msg
              )
            }))
            break

          case 'done':
            // Update with server's message_id, set loading false
            set(state => ({
              messages: state.messages.map(msg =>
                msg.id === assistantPlaceholderId
                  ? { ...msg, id: event.message_id }
                  : msg
              ),
              loading: false
            }))

            // Auto-rename chat from first question if still default name
            if (activeChat.name === 'New Chat') {
              const autoName = question.length > 60
                ? question.slice(0, 57) + '...'
                : question
              get().renameChat(activeChat.id, autoName)
            }
            break

          case 'error':
            set(state => ({
              messages: state.messages.map(msg =>
                msg.id === assistantPlaceholderId
                  ? { ...msg, content: event.detail }
                  : msg
              ),
              loading: false
            }))
            break
        }
      })

      // Update chat in list (message_count increased)
      get().loadChats()

    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to send message',
        loading: false
      })
    }
  },

  // Upload document
  uploadDocument: async (file: File) => {
    try {
      // Check for duplicate by filename
      const existing = get().documents.find(d => d.title === file.name)
      if (existing) {
        const uploadDate = new Date(existing.upload_date).toLocaleDateString()
        throw new Error(
          `Document "${file.name}" already exists.\n\n` +
          `Uploaded: ${uploadDate}\n` +
          `Document ID: ${existing.doc_id}\n\n` +
          `You can use the existing document or rename your file.`
        )
      }

      // Upload to backend
      await api.uploadDocument(file)

      // Reload documents to get the new one
      await get().loadDocuments()

      toast.success('Document uploaded successfully')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to upload document'
      toast.error(message)
      throw error
    }
  },

  // Delete document
  deleteDocument: async (docId: string) => {
    try {
      await api.deleteDocument(docId)

      // Remove from state
      set(state => ({
        documents: state.documents.filter(d => d.doc_id !== docId)
      }))

      // Update any chats that reference this doc
      set(state => ({
        chats: state.chats.map(chat => ({
          ...chat,
          doc_ids: chat.doc_ids.filter(id => id !== docId)
        }))
      }))

      // If active chat used this doc, update it
      set(state => {
        if (state.activeChat && state.activeChat.doc_ids.includes(docId)) {
          return {
            activeChat: {
              ...state.activeChat,
              doc_ids: state.activeChat.doc_ids.filter(id => id !== docId)
            }
          }
        }
        return state
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete document'
      throw new Error(message)
    }
  },

  // Remove document from chat
  removeChatDocument: async (chatId: string, docId: string) => {
    // Save previous state for rollback
    const prevActiveChat = get().activeChat
    const prevChats = get().chats

    // Optimistic update
    set(state => {
      const updatedDocIds = (state.activeChat?.doc_ids || []).filter(id => id !== docId)
      return {
        activeChat: state.activeChat?.id === chatId
          ? { ...state.activeChat, doc_ids: updatedDocIds }
          : state.activeChat,
        chats: state.chats.map(c =>
          c.id === chatId ? { ...c, doc_ids: c.doc_ids.filter(id => id !== docId) } : c
        ),
      }
    })

    try {
      await api.removeChatDocument(chatId, docId)
    } catch (error) {
      // Revert on failure
      set({ activeChat: prevActiveChat, chats: prevChats })
      toast.error('Failed to remove document from chat')
    }
  },

  // Submit feedback on assistant message
  submitFeedback: async (chatId: string, messageId: string, feedback: 'up' | 'down') => {
    try {
      // Optimistic update
      set(state => ({
        messages: state.messages.map(msg =>
          msg.id === messageId ? { ...msg, feedback } : msg
        )
      }))
      await api.submitFeedback(chatId, messageId, feedback)
    } catch (error) {
      // Revert on failure
      set(state => ({
        messages: state.messages.map(msg =>
          msg.id === messageId ? { ...msg, feedback: undefined } : msg
        )
      }))
      toast.error('Failed to submit feedback')
    }
  },

  // Clear error
  clearError: () => set({ error: null })
}))
