import { useState, useRef } from 'react'
import { X, Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react'
import { useAppStore } from '../../store/appStore'

interface Props {
  onClose: () => void
}

export function UploadModal({ onClose }: Props) {
  const { uploadDocument } = useAppStore()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    // Check file type
    if (file.type !== 'application/pdf') {
      return 'Only PDF files are supported'
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
    setProgress(0)
    setError(null)

    try {
      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      await uploadDocument(selectedFile)

      clearInterval(progressInterval)
      setProgress(100)
      setSuccess(true)

      // Close modal after short delay
      setTimeout(() => {
        onClose()
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload document')
      setProgress(0)
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
    <div className="fixed inset-0 bg-ink/20 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-cream rounded-xl shadow-2xl max-w-xl w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-fluid-lg border-b border-ink/10">
          <h2 className="font-serif text-fluid-xl text-ink">Upload Document</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-ink/5 rounded-lg transition-colors"
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
              border-2 border-dashed rounded-lg p-fluid-2xl text-center cursor-pointer transition-all
              ${isDragging
                ? 'border-burgundy bg-burgundy/5'
                : 'border-ink/20 hover:border-burgundy/50 hover:bg-ink/5'
              }
              ${uploading ? 'pointer-events-none opacity-50' : ''}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileInputChange}
              className="hidden"
              disabled={uploading}
            />

            <Upload className={`w-12 h-12 mx-auto mb-fluid-md ${isDragging ? 'text-burgundy' : 'text-ink/40'}`} />

            <p className="font-sans text-fluid-base text-ink font-medium mb-fluid-xs">
              {isDragging ? 'Drop your PDF here' : 'Drag & drop your PDF here'}
            </p>
            <p className="font-sans text-fluid-sm text-ink/60">
              or click to browse • Maximum 50MB
            </p>
          </div>

          {/* Selected File */}
          {selectedFile && (
            <div className="flex items-start gap-3 p-fluid-md border border-ink/10 rounded-lg bg-ink/5">
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

          {/* Progress Bar */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-sans text-fluid-sm text-ink/70">Uploading and processing...</span>
                <span className="font-sans text-fluid-sm text-ink/70 font-medium">{progress}%</span>
              </div>
              <div className="h-2 bg-ink/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-burgundy transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="flex items-center gap-2 p-fluid-md bg-green-50 border border-green-200 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
              <p className="font-sans text-fluid-sm text-green-800">
                Document uploaded successfully!
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="flex items-start gap-2 p-fluid-md bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-sans text-fluid-sm text-red-800 whitespace-pre-line">
                  {error}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-fluid-lg border-t border-ink/10">
          <button
            type="button"
            onClick={onClose}
            disabled={uploading}
            className="px-fluid-lg py-fluid-sm border border-ink/20 rounded-lg hover:bg-ink/5 transition-colors font-sans text-fluid-sm disabled:opacity-50 disabled:cursor-not-allowed"
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
