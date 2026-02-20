import { useState, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X, Upload, AlertCircle, Loader2 } from 'lucide-react'
import { useAppStore } from '../../store/appStore'
import { useAuthStore } from '../../store/authStore'

interface BaseProps {
  onClose: () => void
}

interface CreateModeProps extends BaseProps {
  mode?: 'create'
  onChatCreated: (chatId: string) => void
  initialSelectedDocs?: never
  onDocsSelected?: never
}

interface PickDocsModeProps extends BaseProps {
  mode: 'pick-docs'
  onDocsSelected: (docIds: string[]) => void
  initialSelectedDocs?: string[]
  onChatCreated?: never
}

type Props = CreateModeProps | PickDocsModeProps

export function NewChatModal(props: Props) {
  const { onClose, mode = 'create' } = props
  const { documents, createChat, uploadDocument, loadDocuments } = useAppStore()
  const isAdmin = useAuthStore(s => s.user?.role === 'admin')
  const [name, setName] = useState('')
  const [selectedDocs, setSelectedDocs] = useState<string[]>(
    props.mode === 'pick-docs' ? (props.initialSelectedDocs ?? []) : []
  )
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

    if (mode === 'pick-docs') {
      props.onDocsSelected!(selectedDocs)
      return
    }

    setLoading(true)
    const chatName = name.trim() || 'New Chat'
    const useAutoRoute = selectedDocs.length === 0 && autoRoute && documents.length > 0
    const chat = await createChat(chatName, selectedDocs, useAutoRoute)
    setLoading(false)

    if (chat) {
      props.onChatCreated!(chat.id)
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

  const title = mode === 'pick-docs' ? 'Add Knowledge' : 'Create New Chat'
  const submitLabel = mode === 'pick-docs'
    ? (selectedDocs.length > 0 ? `Done (${selectedDocs.length})` : 'Done')
    : (loading ? 'Creating...' : 'Create Chat')

  return createPortal(
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
      <div className="bg-cream-dark border border-glass-border rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between p-fluid-lg border-b border-glass-border">
          <h2 className="font-sans text-fluid-xl text-ink">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-glass-hover rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-ink/60" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-fluid-lg space-y-fluid-lg">
            {/* Chat name — create mode only */}
            {mode === 'create' && (
              <div>
                <label className="block font-sans text-fluid-sm text-ink/70 mb-2">
                  Chat Name <span className="text-ink/40">(optional — auto-named from first question)</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Research on ML algorithms"
                  className="w-full px-fluid-md py-fluid-sm border border-glass-border bg-glass rounded-lg focus:outline-none focus:ring-2 focus:ring-burgundy/30 font-sans text-fluid-base text-ink"
                  autoFocus
                />
              </div>
            )}

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
                <p className="font-sans text-fluid-sm text-ink/50 p-fluid-md border border-glass-border rounded-lg">
                  No documents available. Upload one below to get started.
                </p>
              ) : (
                <div className="space-y-1 max-h-60 overflow-y-auto border border-glass-border rounded-lg p-fluid-sm">
                  {documents.map(doc => (
                    <label
                      key={doc.doc_id}
                      className="flex items-center gap-3 p-2 md:p-fluid-sm rounded-lg hover:bg-glass-hover cursor-pointer min-h-[44px]"
                    >
                      <input
                        type="checkbox"
                        checked={selectedDocs.includes(doc.doc_id)}
                        onChange={() => toggleDoc(doc.doc_id)}
                        className="w-4 h-4 flex-shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-sans text-fluid-sm text-ink font-medium truncate">
                          {doc.title}
                        </p>
                        <p className="font-sans text-fluid-xs text-ink/50">
                          {doc.chunk_count} sections &bull; {doc.file_size_mb} MB
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

              {/* Auto-route option — create mode, no docs selected */}
              {mode === 'create' && selectedDocs.length === 0 && documents.length > 0 && (
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

            {/* Upload document tile — admin only */}
            {isAdmin && <div>
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
                  w-full border-2 border-dashed rounded-lg p-fluid-lg flex items-center gap-4 cursor-pointer transition-all duration-200
                  ${isDragging
                    ? 'border-burgundy bg-burgundy/5 dropzone-active'
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
                    <Upload className={`w-8 h-8 transition-all duration-200 ${isDragging ? 'text-burgundy scale-110' : 'text-ink/30'}`} />
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
                <div className="flex items-center gap-2 mt-2 animate-slide-up">
                  <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 20 20" fill="none">
                    <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="1.5" className="text-emerald-600" />
                    <path
                      d="M6 10.5l2.5 2.5L14 7.5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="text-emerald-600 animate-check-draw"
                      strokeDasharray="24"
                      strokeDashoffset="24"
                    />
                  </svg>
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
            </div>}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-fluid-lg border-t border-glass-border">
            <button
              type="button"
              onClick={onClose}
              className="px-fluid-lg py-2.5 md:py-fluid-sm border border-ink/20 rounded-lg hover:bg-glass-hover transition-colors font-sans text-fluid-sm min-h-[44px]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-fluid-lg py-2.5 md:py-fluid-sm bg-burgundy text-cream rounded-lg hover:bg-burgundy/90 transition-colors font-sans text-fluid-sm disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
            >
              {submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  )
}
