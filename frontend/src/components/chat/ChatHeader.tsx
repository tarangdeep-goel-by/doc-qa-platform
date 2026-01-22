import { FileText } from 'lucide-react'
import type { Chat } from '../../types'
import { useAppStore } from '../../store/appStore'

interface Props {
  chat: Chat
}

export function ChatHeader({ chat }: Props) {
  const { documents } = useAppStore()

  // Get selected document titles
  const selectedDocs = documents.filter(d => chat.doc_ids.includes(d.doc_id))

  return (
    <header className="border-b border-ink/10 bg-cream/80 backdrop-blur-sm">
      <div className="max-w-4xl mx-auto px-fluid-lg py-fluid-md">
        <h1 className="font-serif text-fluid-2xl text-ink font-medium mb-2">
          {chat.name}
        </h1>

        {/* Document filter info */}
        {chat.doc_ids.length > 0 ? (
          <div className="flex items-center gap-2 flex-wrap">
            <FileText className="w-4 h-4 text-ink/40" />
            <span className="font-sans text-fluid-sm text-ink/60">
              Searching in:
            </span>
            <div className="flex items-center gap-2 flex-wrap">
              {selectedDocs.map((doc, idx) => (
                <span key={doc.doc_id}>
                  <span className="font-sans text-fluid-sm text-burgundy">
                    {doc.title}
                  </span>
                  {idx < selectedDocs.length - 1 && (
                    <span className="text-ink/40 mx-1">•</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-ink/40" />
            <span className="font-sans text-fluid-sm text-ink/60">
              Searching in all documents
            </span>
          </div>
        )}
      </div>
    </header>
  )
}
