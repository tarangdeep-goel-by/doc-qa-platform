import { useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useAppStore } from '../../store/appStore'
import { ChatHeader } from './ChatHeader'
import { ChatMessageItem } from './ChatMessageItem'
import { MessageInput } from '../MessageInput'
import { AlertCircle } from 'lucide-react'

export function ChatInterface() {
  const { chatId } = useParams()
  const { activeChat, messages, loading, setActiveChat, sendMessage } = useAppStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load chat when chatId changes
  useEffect(() => {
    if (chatId) {
      setActiveChat(chatId)
    }
  }, [chatId, setActiveChat])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!activeChat) {
    return (
      <div className="flex-1 flex items-center justify-center p-fluid-2xl">
        <p className="font-sans text-fluid-lg text-ink/50">Loading chat...</p>
      </div>
    )
  }

  const handleSend = async (question: string) => {
    await sendMessage(question)
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Header */}
      <ChatHeader chat={activeChat} />

      {/* Deleted Documents Warning */}
      {activeChat.missing_documents && activeChat.missing_documents.length > 0 && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-fluid-md mx-fluid-lg mt-fluid-md">
          <div className="flex items-start gap-fluid-sm">
            <AlertCircle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-sans text-fluid-sm text-yellow-700 font-medium">
                {activeChat.missing_documents.length} document(s) from this chat have been deleted
              </p>
              {activeChat.available_documents && activeChat.available_documents.length > 0 ? (
                <p className="font-sans text-fluid-sm text-yellow-700 mt-fluid-xs">
                  Questions will use the {activeChat.available_documents.length} remaining document(s): {' '}
                  {activeChat.available_documents.map(d => d.title).join(', ')}
                </p>
              ) : (
                <p className="font-sans text-fluid-sm text-yellow-700 mt-fluid-xs">
                  This chat has no documents available. Consider adding new documents or archiving this chat.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-fluid-lg py-fluid-md">
        <div className="max-w-4xl mx-auto space-y-fluid-lg">
          {messages.length === 0 ? (
            <div className="py-fluid-2xl text-center">
              <h2 className="font-serif text-fluid-2xl text-ink mb-fluid-md">
                Start a conversation
              </h2>
              <p className="font-sans text-fluid-base text-ink/60">
                {activeChat.doc_ids.length > 0
                  ? `Ask questions about ${activeChat.doc_ids.length} selected document${activeChat.doc_ids.length === 1 ? '' : 's'}`
                  : 'Ask questions about all available documents'
                }
              </p>
            </div>
          ) : (
            messages.map(msg => (
              <ChatMessageItem key={msg.id} message={msg} />
            ))
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-ink/10 bg-cream/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-fluid-lg py-fluid-md">
          <MessageInput
            onSubmit={handleSend}
            disabled={loading}
          />
        </div>
      </div>
    </div>
  )
}
