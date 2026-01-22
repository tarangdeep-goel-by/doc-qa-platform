import { ExternalLink } from 'lucide-react'
import type { Source } from '../types'
import { openDocumentAtPage } from '../api/client'

interface Props {
  source: Source
  index: number
}

export function SourceCitation({ source, index }: Props) {
  // Convert score to percentage for display
  const relevance = Math.round(source.score * 100)

  const handleOpenSource = () => {
    if (source.page_num) {
      openDocumentAtPage(source.doc_id, source.page_num)
    }
  }

  return (
    <div className="group p-fluid-sm border border-ink/10 rounded-lg hover:border-burgundy/30 transition-colors">
      <div className="flex items-baseline gap-2 mb-1">
        <span className="font-sans text-fluid-xs text-burgundy font-medium">
          [{index + 1}]
        </span>
        <h4 className="font-serif text-fluid-sm text-ink font-medium flex-1">
          {source.doc_title}
        </h4>
        <span className="font-sans text-fluid-xs text-ink/40">
          {relevance}% match
        </span>
      </div>

      <div className="pl-5">
        {/* Page number with clickable link */}
        {source.page_num ? (
          <div className="flex items-center gap-2">
            <span className="font-sans text-fluid-sm text-ink/60">
              Page {source.page_num}
            </span>
            <button
              onClick={handleOpenSource}
              className="inline-flex items-center gap-1 font-sans text-fluid-xs text-burgundy hover:underline"
              title={`Open ${source.doc_title} at page ${source.page_num}`}
            >
              View source
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <p className="font-body text-fluid-sm text-ink/70 leading-relaxed">
            {source.chunk_text}
          </p>
        )}
      </div>
    </div>
  )
}
