import { ExternalLink } from 'lucide-react'
import type { Source } from '../types'
import { openDocumentAtPage } from '../api/client'
import { forwardRef } from 'react'

interface Props {
  source: Source
  index: number
}

export const SourcePill = forwardRef<HTMLDivElement, Props>(
  ({ source, index }, ref) => {
    const relevance = Math.round(source.score * 100)

    const handleOpen = () => {
      if (source.page_num) {
        openDocumentAtPage(source.doc_id, source.page_num)
      }
    }

    return (
      <div
        ref={ref}
        id={`source-${index + 1}`}
        className="inline-flex items-center gap-2 px-3 py-1.5
          border border-ink/10 rounded-full
          hover:border-burgundy/30 hover:bg-burgundy/5
          transition-all duration-200
          group cursor-pointer"
        onClick={handleOpen}
        title={source.doc_title}
      >
        {/* Index badge */}
        <span className="font-sans text-xs text-burgundy font-medium">
          [{index + 1}]
        </span>

        {/* Title (truncated) */}
        <span className="font-serif text-sm text-ink font-medium truncate max-w-[200px]">
          {source.doc_title}
        </span>

        {/* Metadata */}
        <div className="flex items-center gap-2 text-xs text-ink/50 font-sans">
          <span>{relevance}%</span>
          {source.page_num && (
            <>
              <span>•</span>
              <span>p.{source.page_num}</span>
            </>
          )}
        </div>

        {/* Open icon */}
        <ExternalLink className="w-3 h-3 text-burgundy opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    )
  }
)

SourcePill.displayName = 'SourcePill'
