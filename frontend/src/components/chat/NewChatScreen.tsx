import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../../store/appStore'
import { MessageInput } from '../MessageInput'

export function NewChatScreen() {
  const navigate = useNavigate()
  const { documents, createChat } = useAppStore()
  const [sending, setSending] = useState(false)

  const handleSend = async (question: string) => {
    setSending(true)
    try {
      const autoRoute = documents.length > 0
      const chat = await createChat(question.slice(0, 60), [], autoRoute)
      if (chat) {
        // Navigate to the chat — sendMessage will be called after mount
        navigate(`/chat/${chat.id}`, { state: { initialQuestion: question } })
      }
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-2xl">
        <h1 className="font-sans text-fluid-2xl text-ink font-medium text-center mb-2">
          What do you want to know?
        </h1>
        <p className="font-sans text-sm text-ink/40 text-center mb-8">
          Ask a question about your documents
        </p>
        <MessageInput onSubmit={handleSend} disabled={sending} />
      </div>
    </div>
  )
}
