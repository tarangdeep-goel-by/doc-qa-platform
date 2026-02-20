import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Menu, BookPlus, X } from 'lucide-react'
import { useAppStore } from '../../store/appStore'
import { useUIStore } from '../../store/uiStore'
import { MessageInput } from '../MessageInput'
import { NewChatModal } from '../modals/NewChatModal'

export function NewChatScreen() {
  const navigate = useNavigate()
  const { documents, createChat } = useAppStore()
  const openSidebar = useUIStore(s => s.openSidebar)
  const [sending, setSending] = useState(false)
  const [selectedDocs, setSelectedDocs] = useState<string[]>([])
  const [showDocPicker, setShowDocPicker] = useState(false)

  const handleSend = async (question: string) => {
    setSending(true)
    try {
      const autoRoute = selectedDocs.length === 0 && documents.length > 0
      const chat = await createChat(question.slice(0, 60), selectedDocs, autoRoute)
      if (chat) {
        navigate(`/chat/${chat.id}`, { state: { initialQuestion: question } })
      }
    } finally {
      setSending(false)
    }
  }

  const removeDoc = (docId: string) => {
    setSelectedDocs(prev => prev.filter(id => id !== docId))
  }

  const selectedDocNames = selectedDocs
    .map(id => documents.find(d => d.doc_id === id)?.title)
    .filter(Boolean) as string[]

  return (
    <div className="relative flex-1 flex flex-col items-center justify-center px-4 md:px-6">
      <button
        onClick={openSidebar}
        className="md:hidden absolute top-4 left-4 p-1 text-ink/60 hover:text-ink transition-colors"
        aria-label="Open sidebar"
      >
        <Menu className="w-5 h-5" />
      </button>
      <div className="w-full max-w-2xl animate-drift-up">
        <h1 className="font-sans text-fluid-2xl text-ink font-medium text-center mb-2">
          What do you want to know?
        </h1>
        <p className="font-sans text-sm text-ink/40 text-center mb-8">
          Ask a question about your documents
        </p>
        <MessageInput onSubmit={handleSend} disabled={sending} />

        {/* Add Knowledge CTA + selected doc pills */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setShowDocPicker(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-dashed border-ink/20 text-ink/50 hover:border-burgundy/40 hover:text-burgundy transition-colors font-sans text-fluid-xs"
          >
            <BookPlus className="w-3.5 h-3.5" />
            Add Knowledge
          </button>
          {selectedDocNames.map((name, i) => (
            <span
              key={selectedDocs[i]}
              className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-burgundy/10 border border-burgundy/20 text-burgundy font-sans text-fluid-xs max-w-[12rem] md:max-w-none animate-pop-in"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <span className="truncate">{name}</span>
              <button
                type="button"
                onClick={() => removeDoc(selectedDocs[i])}
                className="p-1 -mr-1 rounded-full hover:bg-burgundy/20 text-burgundy/50 hover:text-burgundy transition-colors flex-shrink-0"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      </div>

      {showDocPicker && (
        <NewChatModal
          mode="pick-docs"
          initialSelectedDocs={selectedDocs}
          onDocsSelected={(docIds) => {
            setSelectedDocs(docIds)
            setShowDocPicker(false)
          }}
          onClose={() => setShowDocPicker(false)}
        />
      )}
    </div>
  )
}
