import { useEffect, useState } from 'react'
import { FileText, Upload, Trash2, ExternalLink, MessageSquare } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAppStore } from '../store/appStore'
import { UploadModal } from '../components/modals/UploadModal'
import * as api from '../api/client'
import type { Document } from '../types'

export function DocumentsPage() {
  const navigate = useNavigate()
  const { documents, loadDocuments, deleteDocument } = useAppStore()
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set())
  const [isBulkDeleting, setIsBulkDeleting] = useState(false)

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleDelete = async (doc: Document) => {
    const chatWarning = doc.chat_count > 0
      ? `\n\nWarning: This document is used in ${doc.chat_count} chat(s).`
      : ''

    if (!confirm(`Delete "${doc.title}"?${chatWarning}\n\nThis will remove the document and all its chunks.`)) {
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

  const handleBulkDelete = async () => {
    if (selectedDocs.size === 0) return

    const totalChats = documents
      .filter(doc => selectedDocs.has(doc.doc_id))
      .reduce((sum, doc) => sum + doc.chat_count, 0)

    const chatWarning = totalChats > 0
      ? `\n\nWarning: ${totalChats} chat(s) will be affected.`
      : ''

    if (!confirm(`Delete ${selectedDocs.size} document(s)?${chatWarning}\n\nThis action cannot be undone.`)) {
      return
    }

    setIsBulkDeleting(true)
    try {
      const response = await api.bulkDeleteDocuments(Array.from(selectedDocs))

      if (response.successful > 0) {
        toast.success(`${response.successful} document(s) deleted successfully`)
      }

      if (response.failed > 0) {
        toast.error(`${response.failed} document(s) failed to delete`)
      }

      // Reload documents
      await loadDocuments()
      setSelectedDocs(new Set())
    } catch (error) {
      toast.error('Bulk delete failed')
    } finally {
      setIsBulkDeleting(false)
    }
  }

  const toggleSelection = (docId: string) => {
    const newSelection = new Set(selectedDocs)
    if (newSelection.has(docId)) {
      newSelection.delete(docId)
    } else {
      newSelection.add(docId)
    }
    setSelectedDocs(newSelection)
  }

  const selectAll = () => {
    if (selectedDocs.size === documents.length) {
      setSelectedDocs(new Set())
    } else {
      setSelectedDocs(new Set(documents.map(doc => doc.doc_id)))
    }
  }

  const handleView = (doc: Document) => {
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
        <div className="flex items-center gap-4">
          <h1 className="font-display text-fluid-2xl text-ink font-semibold">
            Documents
          </h1>
          {documents.length > 0 && (
            <span className="text-fluid-sm text-ink/60">
              {documents.length} total
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {selectedDocs.size > 0 && (
            <button
              onClick={handleBulkDelete}
              disabled={isBulkDeleting}
              className="flex items-center gap-2 px-fluid-md py-fluid-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" />
              <span className="font-sans text-fluid-sm font-medium">
                Delete {selectedDocs.size}
              </span>
            </button>
          )}
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-2 px-fluid-md py-fluid-sm bg-burgundy text-paper rounded-lg hover:bg-burgundy/90 transition-colors"
          >
            <Upload className="w-4 h-4" />
            <span className="font-sans text-fluid-sm font-medium">Upload</span>
          </button>
        </div>
      </div>

      {/* Bulk Actions Bar */}
      {documents.length > 0 && (
        <div className="px-fluid-lg py-fluid-sm border-b border-ink/10 bg-ink/5">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={selectedDocs.size === documents.length}
              onChange={selectAll}
              className="w-4 h-4 rounded border-ink/20 text-burgundy focus:ring-burgundy"
            />
            <span className="text-fluid-sm text-ink/70">
              {selectedDocs.size === documents.length ? 'Deselect all' : 'Select all'}
            </span>
          </label>
        </div>
      )}

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
              const isSelected = selectedDocs.has(doc.doc_id)

              return (
                <div
                  key={doc.doc_id}
                  className={`
                    border border-ink/10 rounded-lg p-fluid-md hover:border-burgundy/30 transition-colors
                    ${isDeleting || isBulkDeleting ? 'opacity-50 pointer-events-none' : ''}
                    ${isSelected ? 'bg-burgundy/5 border-burgundy/30' : ''}
                  `}
                >
                  <div className="flex items-start gap-fluid-md">
                    {/* Checkbox */}
                    <div className="flex items-start pt-1">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelection(doc.doc_id)}
                        className="w-4 h-4 rounded border-ink/20 text-burgundy focus:ring-burgundy"
                      />
                    </div>

                    {/* Document Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-fluid-xs">
                        <FileText className="w-5 h-5 text-burgundy flex-shrink-0" />
                        <h3 className="font-sans text-fluid-base text-ink font-semibold truncate">
                          {doc.title}
                        </h3>
                      </div>

                      <div className="flex items-center gap-fluid-md text-fluid-sm text-ink/60 mb-fluid-xs">
                        <span>{formatFileSize(doc.file_size_mb)}</span>
                        <span>•</span>
                        <span>{doc.chunk_count} chunks</span>
                        <span>•</span>
                        <span>{uploadDate}</span>
                      </div>

                      {/* Chat Usage */}
                      {doc.chat_count > 0 && (
                        <div className="flex items-center gap-2 mt-2">
                          <MessageSquare className="w-4 h-4 text-burgundy/70" />
                          <span className="text-fluid-xs text-burgundy/70 font-medium">
                            Used in {doc.chat_count} chat{doc.chat_count > 1 ? 's' : ''}
                          </span>
                          {doc.chats.length > 0 && (
                            <div className="flex gap-1 flex-wrap">
                              {doc.chats.slice(0, 3).map(chat => (
                                <button
                                  key={chat.id}
                                  onClick={() => navigate(`/chat/${chat.id}`)}
                                  className="px-2 py-0.5 bg-burgundy/10 hover:bg-burgundy/20 text-burgundy text-fluid-xs rounded transition-colors"
                                  title={`Go to ${chat.name}`}
                                >
                                  {chat.name}
                                </button>
                              ))}
                              {doc.chats.length > 3 && (
                                <span className="text-fluid-xs text-ink/50">
                                  +{doc.chats.length - 3} more
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      )}
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
