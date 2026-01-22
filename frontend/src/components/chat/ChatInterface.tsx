import { useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useAppStore } from '../../store/appStore'
import { ChatHeader } from './ChatHeader'
import { ChatMessageItem } from './ChatMessageItem'
import { MessageInput } from '../MessageInput'

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
