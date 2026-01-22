import { useEffect, useState } from 'react'
import type { Document } from '../types'
import { fetchDocuments } from '../api/client'

interface Props {
  selectedDocs: string[]
  onChange: (docIds: string[]) => void
}

export function DocumentSelector({ selectedDocs, onChange }: Props) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDocuments()
      .then(setDocuments)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const toggleDoc = (docId: string) => {
    if (selectedDocs.includes(docId)) {
      onChange(selectedDocs.filter((id) => id !== docId))
    } else {
      onChange([...selectedDocs, docId])
    }
  }

  const selectAll = () => {
    if (selectedDocs.length === documents.length) {
      onChange([])
    } else {
      onChange(documents.map((d) => d.doc_id))
    }
  }

  const selectedCount = selectedDocs.length
  const totalCount = documents.length

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="group w-full text-left border-b border-ink/10 pb-fluid-xs hover:border-burgundy/30 transition-colors"
      >
        <div className="flex items-baseline justify-between">
          <span className="text-fluid-sm font-sans text-ink/60 uppercase tracking-wider">
            Search in
          </span>
          <span className="text-fluid-xs text-ink/40">
            {selectedCount === 0
              ? `All documents (${totalCount})`
              : selectedCount === totalCount
              ? `All documents (${totalCount})`
              : `${selectedCount} of ${totalCount} selected`}
          </span>
        </div>
        <div className="mt-1 text-fluid-base font-serif text-ink group-hover:text-burgundy transition-colors">
          {loading ? (
            'Loading...'
          ) : selectedCount === 0 || selectedCount === totalCount ? (
            'All documents'
          ) : (
            <span className="line-clamp-1">
              {documents
                .filter((d) => selectedDocs.includes(d.doc_id))
                .map((d) => d.title)
                .join(', ')}
            </span>
          )}
        </div>
      </button>

      {isOpen && !loading && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute left-0 right-0 top-full mt-2 z-20 bg-cream border border-ink/10 shadow-lg max-h-80 overflow-y-auto">
            <div className="sticky top-0 bg-cream border-b border-ink/10 p-fluid-sm">
              <button
                onClick={selectAll}
                className="text-fluid-sm text-burgundy hover:text-burgundy-dark font-sans uppercase tracking-wider"
              >
                {selectedCount === totalCount ? 'Deselect all' : 'Select all'}
              </button>
            </div>
            <div className="divide-y divide-ink/5">
              {documents.map((doc) => {
                const isSelected = selectedDocs.includes(doc.doc_id)
                return (
                  <label
                    key={doc.doc_id}
                    className="block p-fluid-sm hover:bg-ink/5 cursor-pointer group transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleDoc(doc.doc_id)}
                        className="mt-1 w-4 h-4 accent-burgundy"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="font-serif text-fluid-base text-ink group-hover:text-burgundy transition-colors">
                          {doc.title}
                        </div>
                        <div className="mt-1 flex gap-3 text-fluid-xs text-ink/50 font-sans">
                          <span>{doc.chunk_count} chunks</span>
                          <span>•</span>
                          <span>{doc.file_size_mb.toFixed(1)} MB</span>
                          <span>•</span>
                          <span>{doc.format.toUpperCase()}</span>
                        </div>
                      </div>
                    </div>
                  </label>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
