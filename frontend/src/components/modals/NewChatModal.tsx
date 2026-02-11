import { useState, useRef } from 'react'
import { X, Upload, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { useAppStore } from '../../store/appStore'

interface Props {
  onClose: () => void
  onChatCreated: (chatId: string) => void
}

export function NewChatModal({ onClose, onChatCreated }: Props) {
  const { documents, createChat, uploadDocument, loadDocuments } = useAppStore()
  const [name, setName] = useState('')
  const [selectedDocs, setSelectedDocs] = useState<string[]>([])
  const [autoRoute, setAutoRoute] = useState(true)
  const [loading, setLoading] = useState(false)

  // Inline upload state
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    setLoading(true)
    const chatName = name.trim() || 'New Chat'
    const useAutoRoute = selectedDocs.length === 0 && autoRoute && documents.length > 0
    const chat = await createChat(chatName, selectedDocs, useAutoRoute)
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

  const handleInlineUpload = async (file: File) => {
    const allowedExtensions = ['.pdf', '.docx', '.html', '.htm', '.txt']
    const hasValidExt = allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext))
    if (!hasValidExt) {
      setUploadError(`Unsupported file type. Allowed: ${allowedExtensions.join(', ')}`)
      return
    }
    if (file.size / (1024 * 1024) > 50) {
      setUploadError('File too large. Maximum 50MB.')
      return
    }

    setUploading(true)
    setUploadError(null)
    setUploadSuccess(null)

    try {
      await uploadDocument(file)
      await loadDocuments()

      // Auto-select the newly uploaded doc
      const updated = useAppStore.getState().documents
      const newDoc = updated.find(d => d.title === file.name)
      if (newDoc && !selectedDocs.includes(newDoc.doc_id)) {
        setSelectedDocs(prev => [...prev, newDoc.doc_id])
      }

      setUploadSuccess(file.name)
      setTimeout(() => setUploadSuccess(null), 3000)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
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
                Chat Name <span className="text-ink/40">(optional — auto-named from first question)</span>
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
                  No documents available. Upload one below to get started.
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
                          {doc.chunk_count} sections • {doc.file_size_mb} MB
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

              {/* Auto-route option — shown when no docs manually selected */}
              {selectedDocs.length === 0 && documents.length > 0 && (
                <label className="flex items-center gap-2 mt-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRoute}
                    onChange={(e) => setAutoRoute(e.target.checked)}
                  />
                  <span className="font-sans text-fluid-xs text-ink/70">
                    Auto-detect relevant documents from your first question
                  </span>
                </label>
              )}
            </div>

            {/* Upload document tile */}
            <div>
              <label className="block font-sans text-fluid-sm text-ink/70 mb-2">
                Upload New Document
              </label>
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
                onDragLeave={(e) => { e.preventDefault(); setIsDragging(false) }}
                onDrop={(e) => {
                  e.preventDefault()
                  setIsDragging(false)
                  const file = e.dataTransfer.files[0]
                  if (file) handleInlineUpload(file)
                }}
                onClick={() => !uploading && fileInputRef.current?.click()}
                className={`
                  w-full border-2 border-dashed rounded-lg p-fluid-lg flex items-center gap-4 cursor-pointer transition-all
                  ${isDragging
                    ? 'border-burgundy bg-burgundy/5'
                    : 'border-ink/15 hover:border-burgundy/40 hover:bg-ink/[0.02]'
                  }
                  ${uploading ? 'pointer-events-none opacity-60' : ''}
                `}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.html,.htm,.txt"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleInlineUpload(file)
                  }}
                  className="hidden"
                  disabled={uploading}
                />

                <div className="flex-shrink-0">
                  {uploading ? (
                    <Loader2 className="w-8 h-8 text-burgundy animate-spin" />
                  ) : (
                    <Upload className={`w-8 h-8 ${isDragging ? 'text-burgundy' : 'text-ink/30'}`} />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  {uploading ? (
                    <p className="font-sans text-fluid-sm text-ink/70">Uploading and processing...</p>
                  ) : (
                    <>
                      <p className="font-sans text-fluid-sm text-ink font-medium">
                        Drop a file here or click to browse
                      </p>
                      <p className="font-sans text-fluid-xs text-ink/50">
                        PDF, DOCX, HTML, TXT
                      </p>
                    </>
                  )}
                </div>
              </div>

              {uploadSuccess && (
                <div className="flex items-center gap-2 mt-2">
                  <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  <p className="font-sans text-fluid-xs text-emerald-700">
                    Uploaded &amp; selected: {uploadSuccess}
                  </p>
                </div>
              )}

              {uploadError && (
                <div className="flex items-center gap-2 mt-2">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                  <p className="font-sans text-fluid-xs text-red-600 whitespace-pre-line">
                    {uploadError}
                  </p>
                </div>
              )}
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
              disabled={loading}
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
