import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useAppStore } from '../../store/appStore'

interface Props {
  onClose: () => void
  onChatCreated: (chatId: string) => void
}

export function NewChatModal({ onClose, onChatCreated }: Props) {
  const { documents, createChat } = useAppStore()
  const [name, setName] = useState('')
  const [selectedDocs, setSelectedDocs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      alert('Please enter a chat name')
      return
    }

    setLoading(true)
    const chat = await createChat(name.trim(), selectedDocs)
    setLoading(false)

    if (chat) {
      onChatCreated(chat.id)
    }
  }

  const toggleDoc = (docId: string) => {
    setSelectedDocs(prev =>
      prev.includes(docId)
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    )
  }

  const selectAll = () => {
    setSelectedDocs(documents.map(d => d.doc_id))
  }

  const clearAll = () => {
    setSelectedDocs([])
  }

  return (
    <div className="fixed inset-0 bg-ink/20 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-cream rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-fluid-lg border-b border-ink/10">
          <h2 className="font-serif text-fluid-xl text-ink">Create New Chat</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-ink/5 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-ink/60" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-fluid-lg space-y-fluid-lg">
            {/* Chat name */}
            <div>
              <label className="block font-sans text-fluid-sm text-ink/70 mb-2">
                Chat Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Research on ML algorithms"
                className="w-full px-fluid-md py-fluid-sm border border-ink/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-burgundy/30 font-sans text-fluid-base"
                autoFocus
              />
            </div>

            {/* Document selection */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block font-sans text-fluid-sm text-ink/70">
                  Select Documents
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={selectAll}
                    className="font-sans text-fluid-xs text-burgundy hover:underline"
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    onClick={clearAll}
                    className="font-sans text-fluid-xs text-burgundy hover:underline"
                  >
                    Clear
                  </button>
                </div>
              </div>

              {documents.length === 0 ? (
                <p className="font-sans text-fluid-sm text-ink/50 p-fluid-md border border-ink/10 rounded-lg">
                  No documents available. Please upload documents first.
                </p>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto border border-ink/10 rounded-lg p-fluid-sm">
                  {documents.map(doc => (
                    <label
                      key={doc.doc_id}
                      className="flex items-start gap-3 p-fluid-sm rounded-lg hover:bg-ink/5 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedDocs.includes(doc.doc_id)}
                        onChange={() => toggleDoc(doc.doc_id)}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-sans text-fluid-sm text-ink font-medium truncate">
                          {doc.title}
                        </p>
                        <p className="font-sans text-fluid-xs text-ink/50">
                          {doc.chunk_count} chunks • {doc.file_size_mb} MB
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              )}

              <p className="font-sans text-fluid-xs text-ink/50 mt-2">
                {selectedDocs.length === 0
                  ? 'Select documents to search, or leave empty to search all'
                  : `${selectedDocs.length} document${selectedDocs.length === 1 ? '' : 's'} selected`
                }
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-fluid-lg border-t border-ink/10">
            <button
              type="button"
              onClick={onClose}
              className="px-fluid-lg py-fluid-sm border border-ink/20 rounded-lg hover:bg-ink/5 transition-colors font-sans text-fluid-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-fluid-lg py-fluid-sm bg-burgundy text-cream rounded-lg hover:bg-burgundy/90 transition-colors font-sans text-fluid-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Chat'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
