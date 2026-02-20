import { useState } from 'react'
import { FileText, Menu, X, BookPlus } from 'lucide-react'
import type { Chat } from '../../types'
import { useAppStore } from '../../store/appStore'
import { useUIStore } from '../../store/uiStore'
import { NewChatModal } from '../modals/NewChatModal'

interface Props {
  chat: Chat
}

export function ChatHeader({ chat }: Props) {
  const { documents, removeChatDocument, updateChatDocuments } = useAppStore()
  const openSidebar = useUIStore(s => s.openSidebar)
  const [showDocPicker, setShowDocPicker] = useState(false)

  // Get selected document titles
  const selectedDocs = documents.filter(d => chat.doc_ids.includes(d.doc_id))
  const canRemove = selectedDocs.length > 1

  return (
    <header className="border-b border-glass-border bg-cream-dark">
      <div className="max-w-4xl mx-auto px-4 md:px-fluid-lg py-fluid-md">
        <div className="flex items-center gap-3 mb-2">
          <button
            onClick={openSidebar}
            className="md:hidden p-1 -ml-1 text-ink/60 hover:text-ink transition-colors"
            aria-label="Open sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h1 className="font-serif text-fluid-2xl text-ink font-medium">
            {chat.name}
          </h1>
        </div>

        {/* Document filter info */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <FileText className="w-4 h-4 text-ink/40 flex-shrink-0" />
          {chat.doc_ids.length > 0 ? (
            <>
              {selectedDocs.map((doc) => (
                <span
                  key={doc.doc_id}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-burgundy/10 border border-burgundy/20"
                >
                  <span className="font-sans text-fluid-xs text-burgundy truncate max-w-[10rem] md:max-w-[14rem]">
                    {doc.title}
                  </span>
                  {canRemove && (
                    <button
                      onClick={() => removeChatDocument(chat.id, doc.doc_id)}
                      className="p-1 -mr-0.5 rounded-full hover:bg-burgundy/20 text-burgundy/50 hover:text-burgundy transition-colors"
                      title={`Remove ${doc.title}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </span>
              ))}
            </>
          ) : (
            <span className="font-sans text-fluid-sm text-ink/60">
              Searching in all documents
            </span>
          )}
          <button
            onClick={() => setShowDocPicker(true)}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-dashed border-ink/20 text-ink/50 hover:border-burgundy/40 hover:text-burgundy transition-colors font-sans text-fluid-xs"
          >
            <BookPlus className="w-3.5 h-3.5" />
            Add Knowledge
          </button>
        </div>
      </div>

      {showDocPicker && (
        <NewChatModal
          mode="pick-docs"
          initialSelectedDocs={chat.doc_ids}
          onDocsSelected={(docIds) => {
            updateChatDocuments(chat.id, docIds)
            setShowDocPicker(false)
          }}
          onClose={() => setShowDocPicker(false)}
        />
      )}
    </header>
  )
}
