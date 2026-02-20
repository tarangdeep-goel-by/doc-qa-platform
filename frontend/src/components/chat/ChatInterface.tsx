import { useEffect, useRef } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import { useAppStore } from '../../store/appStore'
import { ChatHeader } from './ChatHeader'
import { ChatMessageItem } from './ChatMessageItem'
import { MessageInput } from '../MessageInput'
import { AlertCircle } from 'lucide-react'

export function ChatInterface() {
  const { chatId } = useParams()
  const location = useLocation()
  const { activeChat, messages, loading, setActiveChat, sendMessage } = useAppStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const initialQuestionSent = useRef(false)

  // Load chat and optionally send initial question (single effect to avoid races)
  useEffect(() => {
    if (!chatId) return
    let cancelled = false

    const init = async () => {
      await setActiveChat(chatId)
      if (cancelled) return

      const navState = location.state as { initialQuestion?: string } | null
      if (navState?.initialQuestion && !initialQuestionSent.current) {
        initialQuestionSent.current = true
        window.history.replaceState({}, '')
        sendMessage(navState.initialQuestion)
      }
    }

    init()
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (!activeChat) {
    return (
      <div className="flex-1 flex items-center justify-center p-fluid-2xl">
        <p className="font-sans text-fluid-lg text-ink/50">Loading chat...</p>
      </div>
    )
  }

  const filteredMessages = messages.filter(msg => !(msg.id.startsWith('stream-') && !msg.content))

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Header */}
      <ChatHeader chat={activeChat} />

      {/* Deleted Documents Warning */}
      {activeChat.missing_documents && activeChat.missing_documents.length > 0 && (
        <div className="bg-yellow-900/20 border-l-4 border-yellow-400 p-fluid-md mx-4 md:mx-8 mt-fluid-md rounded-r">
          <div className="flex items-start gap-fluid-sm">
            <AlertCircle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-sans text-fluid-sm text-yellow-300 font-medium">
                {activeChat.missing_documents.length} {activeChat.missing_documents.length === 1 ? 'document has' : 'documents have'} been deleted from this chat
              </p>
              {activeChat.available_documents && activeChat.available_documents.length > 0 ? (
                <p className="font-sans text-fluid-sm text-yellow-300 mt-fluid-xs">
                  Questions will use the {activeChat.available_documents.length} remaining document{activeChat.available_documents.length === 1 ? '' : 's'}: {' '}
                  {activeChat.available_documents.map(d => d.title).join(', ')}
                </p>
              ) : (
                <p className="font-sans text-fluid-sm text-yellow-300 mt-fluid-xs">
                  This chat has no documents available. Add new documents to continue using this chat.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-4 md:px-6 md:py-6">
          {messages.length === 0 ? (
            <div className="py-fluid-2xl text-center">
              <h2 className="font-sans text-fluid-2xl text-ink mb-fluid-md">
                Start a conversation
              </h2>
              <p className="font-sans text-fluid-base text-ink/50">
                {activeChat.auto_route
                  ? 'Ask a question and relevant documents will be automatically selected'
                  : activeChat.doc_ids.length > 0
                    ? `Ask questions about ${activeChat.doc_ids.length} selected document${activeChat.doc_ids.length === 1 ? '' : 's'}`
                    : 'Ask questions about all available documents'
                }
              </p>
            </div>
          ) : (
            filteredMessages.map((msg, idx) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                prevMessage={idx > 0 ? filteredMessages[idx - 1] : undefined}
              />
            ))
          )}

          {/* Typing indicator */}
          {loading && (!messages.length || messages[messages.length - 1].role !== 'assistant' || !messages[messages.length - 1].content) && (
            <div className="flex items-center gap-2 mt-4 text-ink/40">
              <span className="w-1.5 h-1.5 rounded-full bg-ink/30 animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-ink/30 animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-ink/30 animate-bounce [animation-delay:300ms]" />
            </div>
          )}

          <div ref={messagesEndRef} className="h-8" />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-glass-border">
        <div className="max-w-3xl mx-auto px-4 py-3 md:px-6 md:py-4">
          <MessageInput
            onSubmit={sendMessage}
            disabled={loading}
          />
        </div>
      </div>
    </div>
  )
}
