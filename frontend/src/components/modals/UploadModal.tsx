import { useState, useRef } from 'react'
import { X, Upload, FileText, AlertCircle, Loader2 } from 'lucide-react'
import { useAppStore } from '../../store/appStore'

interface Props {
  onClose: () => void
}

export function UploadModal({ onClose }: Props) {
  const { uploadDocument } = useAppStore()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    // Check file type by extension
    const allowedExtensions = ['.pdf', '.docx', '.html', '.htm', '.txt']
    const fileName = file.name.toLowerCase()
    const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext))
    if (!hasValidExtension) {
      return `Unsupported file type. Allowed: ${allowedExtensions.join(', ')}`
    }

    // Check file size (max 50MB)
    const maxSizeMB = 50
    const fileSizeMB = file.size / (1024 * 1024)
    if (fileSizeMB > maxSizeMB) {
      return `File too large (${fileSizeMB.toFixed(1)} MB). Maximum size is ${maxSizeMB} MB`
    }

    return null
  }

  const handleFileSelect = (file: File) => {
    setError(null)
    setSuccess(false)

    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      return
    }

    setSelectedFile(file)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const file = e.dataTransfer.files[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setUploading(true)
    setError(null)

    try {
      await uploadDocument(selectedFile)
      setSuccess(true)

      // Close modal after short delay
      setTimeout(() => {
        onClose()
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload document')
    } finally {
      setUploading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024)
    if (mb < 1) {
      return `${(bytes / 1024).toFixed(0)} KB`
    }
    return `${mb.toFixed(1)} MB`
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
      <div className="bg-cream-dark border border-glass-border rounded-xl shadow-2xl max-w-xl w-full animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between p-fluid-lg border-b border-glass-border">
          <h2 className="font-sans text-fluid-xl text-ink">Upload Document</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-glass-hover rounded-lg transition-colors"
            disabled={uploading}
          >
            <X className="w-5 h-5 text-ink/60" />
          </button>
        </div>

        {/* Content */}
        <div className="p-fluid-lg space-y-fluid-lg">
          {/* Drag & Drop Area */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-lg p-fluid-2xl text-center cursor-pointer transition-all duration-200
              ${isDragging
                ? 'border-burgundy bg-burgundy/5 dropzone-active'
                : 'border-ink/20 hover:border-burgundy/50 hover:bg-glass-hover'
              }
              ${uploading ? 'pointer-events-none opacity-50' : ''}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.html,.htm,.txt"
              onChange={handleFileInputChange}
              className="hidden"
              disabled={uploading}
            />

            <Upload className={`w-12 h-12 mx-auto mb-fluid-md transition-all duration-200 ${isDragging ? 'text-burgundy scale-110' : 'text-ink/40'}`} />

            <p className="font-sans text-fluid-base text-ink font-medium mb-fluid-xs">
              {isDragging ? 'Drop your document here' : 'Drag & drop your document here'}
            </p>
            <p className="font-sans text-fluid-sm text-ink/60">
              PDF, DOCX, HTML, TXT • Maximum 50MB
            </p>
          </div>

          {/* Selected File */}
          {selectedFile && (
            <div className="flex items-start gap-3 p-fluid-md border border-glass-border rounded-lg bg-glass">
              <FileText className="w-5 h-5 text-burgundy flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="font-sans text-fluid-sm text-ink font-medium truncate">
                  {selectedFile.name}
                </p>
                <p className="font-sans text-fluid-xs text-ink/60">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
              {!uploading && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setSelectedFile(null)
                    setError(null)
                  }}
                  className="p-1 hover:bg-ink/10 rounded transition-colors"
                >
                  <X className="w-4 h-4 text-ink/60" />
                </button>
              )}
            </div>
          )}

          {/* Uploading Spinner */}
          {uploading && (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-burgundy animate-spin" />
              <span className="font-sans text-fluid-sm text-ink/70">Uploading and processing...</span>
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="flex items-center gap-2 p-fluid-md bg-green-900/20 border border-green-700 rounded-lg animate-slide-up">
              <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="1.5" className="text-green-400" />
                <path
                  d="M6 10.5l2.5 2.5L14 7.5"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="text-green-400 animate-check-draw"
                  strokeDasharray="24"
                  strokeDashoffset="24"
                />
              </svg>
              <p className="font-sans text-fluid-sm text-green-300">
                Document uploaded successfully
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="flex items-start gap-2 p-fluid-md bg-red-900/20 border border-red-700 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-sans text-fluid-sm text-red-300 whitespace-pre-line">
                  {error}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-fluid-lg border-t border-glass-border">
          <button
            type="button"
            onClick={onClose}
            disabled={uploading}
            className="px-fluid-lg py-fluid-sm border border-ink/20 rounded-lg hover:bg-glass-hover transition-colors font-sans text-fluid-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploading || success}
            className="px-fluid-lg py-fluid-sm bg-burgundy text-cream rounded-lg hover:bg-burgundy/90 transition-colors font-sans text-fluid-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>
    </div>
  )
}
