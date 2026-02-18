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

    useImperativeHandle(ref, () => ({
      scrollToSource: (index: number) => {
        if (!isExpanded) {
          setIsExpanded(true)
        }
        setTimeout(() => {
          const element = sourceRefs.current.get(index)
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
            element.classList.add('bg-ink/8')
            setTimeout(() => {
              element.classList.remove('bg-ink/8')
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
      <div className="mt-10">
        {/* Section label with divider — matches the "Related search results" style */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-3 w-full group cursor-pointer"
        >
          <p className="font-sans text-xs text-ink/40 tracking-wide uppercase flex-shrink-0">
            Sources ({sources.length})
          </p>
          <div className="flex-1 h-px bg-glass-border" />
          {isExpanded ? (
            <ChevronUp className="w-3.5 h-3.5 text-ink/30" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-ink/30" />
          )}
        </button>

        {/* Source cards — vertical list with dividers */}
        {isExpanded && (
          <div className="mt-4">
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
                  className="py-4 border-b border-glass-border last:border-b-0
                    cursor-pointer group/source transition-colors duration-300 rounded-sm -mx-2 px-2"
                  title="Click to open document"
                >
                  {/* Type label + page */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-sans text-xs text-ink/40">
                      Source {idx + 1}
                    </span>
                    {source.page_num && (
                      <>
                        <span className="text-ink/15">·</span>
                        <span className="font-sans text-xs text-ink/40">
                          Page {source.page_num}
                        </span>
                      </>
                    )}
                    <span className="text-ink/15">·</span>
                    <span className="font-sans text-xs text-ink/30">
                      {relevance}% match
                    </span>
                  </div>

                  {/* Document title */}
                  <div className="flex items-center gap-2">
                    <h4 className="font-sans text-sm text-ink font-medium group-hover/source:text-burgundy transition-colors">
                      {source.doc_title}
                    </h4>
                    <ExternalLink className="w-3 h-3 text-ink/20 opacity-0 group-hover/source:opacity-100 transition-opacity flex-shrink-0" />
                  </div>

                  {/* Chunk preview if available */}
                  {source.text && (
                    <p className="font-sans text-sm text-ink/50 mt-1 line-clamp-2 leading-relaxed">
                      {source.text.slice(0, 180)}{source.text.length > 180 ? '...' : ''}
                    </p>
                  )}
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
