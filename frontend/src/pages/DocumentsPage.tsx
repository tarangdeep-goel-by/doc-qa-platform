import { useEffect, useState } from 'react'
import { FileText, Upload, Trash2, ExternalLink } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import { useAppStore } from '../store/appStore'
import { UploadModal } from '../components/modals/UploadModal'
import type { Document } from '../types'

export function DocumentsPage() {
  const { documents, loadDocuments, deleteDocument } = useAppStore()
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleDelete = async (doc: Document) => {
    if (!confirm(`Delete "${doc.title}"?\n\nThis will remove the document and all its chunks. Chats using this document will be updated.`)) {
      return
    }

    setDeletingId(doc.doc_id)
    try {
      await deleteDocument(doc.doc_id)
      toast.success('Document deleted successfully')
    } catch (error) {
      toast.error('Failed to delete document')
    } finally {
      setDeletingId(null)
    }
  }

  const handleView = (doc: Document) => {
    // Open document in new tab
    window.open(`/api/admin/documents/${doc.doc_id}/file`, '_blank')
  }

  const formatFileSize = (mb: number) => {
    if (mb < 1) {
      return `${(mb * 1024).toFixed(0)} KB`
    }
    return `${mb.toFixed(1)} MB`
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-fluid-lg py-fluid-md border-b border-ink/10">
        <h1 className="font-display text-fluid-2xl text-ink font-semibold">
          Documents
        </h1>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-fluid-md py-fluid-sm bg-burgundy text-paper rounded-lg hover:bg-burgundy/90 transition-colors"
        >
          <Upload className="w-4 h-4" />
          <span className="font-sans text-fluid-sm font-medium">Upload</span>
        </button>
      </div>

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto">
        {documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-fluid-lg py-fluid-2xl">
            <FileText className="w-16 h-16 text-ink/20 mb-fluid-md" />
            <h2 className="font-display text-fluid-xl text-ink font-semibold mb-fluid-xs">
              No documents yet
            </h2>
            <p className="font-sans text-fluid-sm text-ink/60 text-center max-w-md mb-fluid-lg">
              Upload your first document to start asking questions. Supported formats: PDF
            </p>
            <button
              onClick={() => setShowUploadModal(true)}
              className="flex items-center gap-2 px-fluid-lg py-fluid-md bg-burgundy text-paper rounded-lg hover:bg-burgundy/90 transition-colors"
            >
              <Upload className="w-5 h-5" />
              <span className="font-sans text-fluid-base font-medium">Upload Document</span>
            </button>
          </div>
        ) : (
          <div className="px-fluid-lg py-fluid-md space-y-fluid-md">
            {documents.map(doc => {
              const uploadDate = formatDistanceToNow(new Date(doc.upload_date), { addSuffix: true })
              const isDeleting = deletingId === doc.doc_id

              return (
                <div
                  key={doc.doc_id}
                  className={`
                    border border-ink/10 rounded-lg p-fluid-md hover:border-burgundy/30 transition-colors
                    ${isDeleting ? 'opacity-50 pointer-events-none' : ''}
                  `}
                >
                  <div className="flex items-start justify-between gap-fluid-md">
                    {/* Document Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-fluid-xs">
                        <FileText className="w-5 h-5 text-burgundy flex-shrink-0" />
                        <h3 className="font-sans text-fluid-base text-ink font-semibold truncate">
                          {doc.title}
                        </h3>
                      </div>

                      <div className="flex items-center gap-fluid-md text-fluid-sm text-ink/60">
                        <span>{formatFileSize(doc.file_size_mb)}</span>
                        <span>•</span>
                        <span>{doc.chunk_count} chunks</span>
                        <span>•</span>
                        <span>{uploadDate}</span>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => handleView(doc)}
                        className="p-2 hover:bg-ink/5 rounded-lg transition-colors"
                        title="View document"
                      >
                        <ExternalLink className="w-4 h-4 text-ink/60" />
                      </button>
                      <button
                        onClick={() => handleDelete(doc)}
                        className="p-2 hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Delete document"
                        disabled={isDeleting}
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <UploadModal onClose={() => setShowUploadModal(false)} />
      )}
    </div>
  )
}
