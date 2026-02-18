import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { parseCitations } from '../../utils/citationParser'
import { CitationLink } from './CitationLink'
import type { Source } from '../../types'

interface Props {
  content: string
  sources?: Source[]
  onCitationClick: (index: number) => void
}

export function MarkdownContent({ content, sources = [], onCitationClick }: Props) {
  const cleanedContent = parseCitations(content, sources)

  const getTextContent = (children: React.ReactNode): string => {
    if (typeof children === 'string') return children
    if (typeof children === 'number') return String(children)
    if (Array.isArray(children)) return children.map(getTextContent).join('')
    if (React.isValidElement(children)) {
      return getTextContent(children.props.children)
    }
    return ''
  }

  const processChildren = (children: React.ReactNode, keyPrefix = ''): React.ReactNode => {
    if (typeof children === 'string') {
      const regex = /\[\[(\d+)\]\]/g
      const parts: React.ReactNode[] = []
      let lastIndex = 0
      let match: RegExpExecArray | null

      while ((match = regex.exec(children)) !== null) {
        if (match.index > lastIndex) {
          parts.push(children.slice(lastIndex, match.index))
        }
        const index = parseInt(match[1])
        parts.push(
          <CitationLink key={`${keyPrefix}-cite-${index}-${match.index}`} index={index} onClick={onCitationClick} />
        )
        lastIndex = regex.lastIndex
      }

      if (lastIndex < children.length) {
        parts.push(children.slice(lastIndex))
      }

      return parts.length > 0 ? parts : children
    }

    if (Array.isArray(children)) {
      return children.map((child, idx) => processChildren(child, `${keyPrefix}-${idx}`))
    }

    if (React.isValidElement(children)) {
      return React.cloneElement(children, {
        ...children.props,
        children: processChildren(children.props.children, keyPrefix),
      })
    }

    return children
  }

  // Wrapper that injects citation processing into any element
  const withCitations = (Tag: string) =>
    ({ children, ...props }: React.HTMLAttributes<HTMLElement> & { node?: unknown }) => {
      const { node: _node, ...htmlProps } = props as Record<string, unknown>
      const text = getTextContent(children as React.ReactNode)
      const processed = text.includes('[[') ? processChildren(children as React.ReactNode, Tag) : children
      return React.createElement(Tag, htmlProps, processed)
    }

  return (
    <div className="
      prose prose-invert prose-sm max-w-none
      prose-headings:font-sans prose-headings:text-ink prose-headings:tracking-tight
      prose-h2:text-lg prose-h2:font-semibold prose-h2:mt-6 prose-h2:mb-3 prose-h2:border-b prose-h2:border-glass-border prose-h2:pb-2
      prose-h3:text-base prose-h3:font-semibold prose-h3:mt-5 prose-h3:mb-2
      prose-p:font-sans prose-p:text-ink/85 prose-p:leading-[1.75] prose-p:my-2.5
      prose-ul:font-sans prose-ul:my-3 prose-ul:space-y-1.5
      prose-ol:font-sans prose-ol:my-3 prose-ol:space-y-1.5
      prose-li:text-ink/85 prose-li:leading-[1.7] prose-li:pl-1
      prose-strong:text-ink prose-strong:font-semibold
      prose-em:text-ink/75 prose-em:italic
      prose-code:text-cyan prose-code:bg-cyan/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:font-mono prose-code:text-sm prose-code:before:content-none prose-code:after:content-none
      prose-a:text-burgundy prose-a:no-underline hover:prose-a:underline
      prose-table:my-4 prose-table:text-sm
      prose-th:bg-glass prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:font-semibold prose-th:text-ink/80 prose-th:border-b prose-th:border-glass-border
      prose-td:px-3 prose-td:py-2 prose-td:border-b prose-td:border-glass-border prose-td:text-ink/80
      prose-hr:border-glass-border prose-hr:my-5
      prose-blockquote:border-l-burgundy/30 prose-blockquote:bg-burgundy/5 prose-blockquote:py-1 prose-blockquote:text-ink/70
    ">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: withCitations('p'),
          li: withCitations('li'),
          td: withCitations('td'),
          th: withCitations('th'),
          // Clean table wrapper
          table: ({ children, ...props }) => (
            <div className="overflow-x-auto rounded-lg border border-glass-border my-4">
              <table {...props} className="min-w-full">{children}</table>
            </div>
          ),
        }}
      >
        {cleanedContent}
      </ReactMarkdown>
    </div>
  )
}
