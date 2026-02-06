import { useState, forwardRef, useImperativeHandle, useRef } from 'react'
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import type { Source } from '../types'
import { openDocumentAtPage } from '../api/client'

interface Props {
  sources: Source[]
}

export interface SourcesBadgeRef {
  scrollToSource: (index: number) => void
}

export const SourcesBadge = forwardRef<SourcesBadgeRef, Props>(
  ({ sources }, ref) => {
    const [isExpanded, setIsExpanded] = useState(false)
    const sourceRefs = useRef<Map<number, HTMLDivElement>>(new Map())

    // Expose scrollToSource method to parent via ref
    useImperativeHandle(ref, () => ({
      scrollToSource: (index: number) => {
        // Auto-expand if collapsed
        if (!isExpanded) {
          setIsExpanded(true)
        }

        // Scroll to source after a small delay (to allow expansion animation)
        setTimeout(() => {
          const element = sourceRefs.current.get(index)
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'nearest' })

            // Flash animation
            element.classList.add('ring-2', 'ring-burgundy', 'ring-offset-2')
            setTimeout(() => {
              element.classList.remove('ring-2', 'ring-burgundy', 'ring-offset-2')
            }, 2000)
          }
        }, isExpanded ? 0 : 150)
      },
    }))

    const handleSourceClick = (source: Source, event: React.MouseEvent) => {
      event.stopPropagation()
      if (source.page_num) {
        openDocumentAtPage(source.doc_id, source.page_num)
      }
    }

    return (
      <div className="mt-fluid-sm">
        {/* Compact badge */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="inline-flex items-center gap-1.5 px-2.5 py-1
            border border-burgundy/20 rounded-full
            bg-burgundy/5 hover:bg-burgundy/10
            transition-colors duration-200
            group"
        >
          <span className="font-sans text-xs text-burgundy font-medium">
            {sources.length} {sources.length === 1 ? 'source' : 'sources'}
          </span>
          {isExpanded ? (
            <ChevronUp className="w-3 h-3 text-burgundy" />
          ) : (
            <ChevronDown className="w-3 h-3 text-burgundy" />
          )}
        </button>

        {/* Expanded sources list */}
        {isExpanded && (
          <div className="mt-2 space-y-1.5 pl-2 border-l-2 border-burgundy/10">
            {sources.map((source, idx) => {
              const normalized = source.score >= 0 && source.score <= 1
                ? source.score
                : 1 / (1 + Math.exp(-source.score))
              const relevance = Math.round(normalized * 100)

              return (
                <div
                  key={idx}
                  ref={(el) => {
                    if (el) sourceRefs.current.set(idx, el)
                  }}
                  onClick={(e) => handleSourceClick(source, e)}
                  className="flex items-center gap-2 p-2 rounded-lg
                    hover:bg-burgundy/5 transition-colors duration-200
                    cursor-pointer group/source"
                  title="Click to open document"
                >
                  {/* Index */}
                  <span className="flex-shrink-0 font-sans text-xs text-burgundy font-medium">
                    [{idx + 1}]
                  </span>

                  {/* Document title */}
                  <span className="flex-1 font-serif text-sm text-ink font-medium truncate">
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
                  <ExternalLink className="w-3 h-3 text-burgundy opacity-0 group-hover/source:opacity-100 transition-opacity" />
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }
)

SourcesBadge.displayName = 'SourcesBadge'
