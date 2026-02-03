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
  const { cleanedContent } = parseCitations(content, sources)

  // Helper to extract text from React children recursively
  const getTextContent = (children: React.ReactNode): string => {
    if (typeof children === 'string') return children
    if (typeof children === 'number') return String(children)
    if (Array.isArray(children)) return children.map(getTextContent).join('')
    if (React.isValidElement(children)) {
      return getTextContent(children.props.children)
    }
    return ''
  }

  // Helper to process children recursively and replace [[N]] with CitationLink
  const processChildren = (children: React.ReactNode, keyPrefix = ''): React.ReactNode => {
    if (typeof children === 'string') {
      // Process string for citations
      const regex = /\[\[(\d+)\]\]/g
      const parts: React.ReactNode[] = []
      let lastIndex = 0
      let match: RegExpExecArray | null

      while ((match = regex.exec(children)) !== null) {
        // Add text before match
        if (match.index > lastIndex) {
          parts.push(children.slice(lastIndex, match.index))
        }

        // Add CitationLink
        const index = parseInt(match[1])
        parts.push(
          <CitationLink key={`${keyPrefix}-cite-${index}-${match.index}`} index={index} onClick={onCitationClick} />
        )

        lastIndex = regex.lastIndex
      }

      // Add remaining text
      if (lastIndex < children.length) {
        parts.push(children.slice(lastIndex))
      }

      return parts.length > 0 ? parts : children
    }

    if (Array.isArray(children)) {
      return children.map((child, idx) => processChildren(child, `${keyPrefix}-${idx}`))
    }

    if (React.isValidElement(children)) {
      // Clone element and recursively process its children
      return React.cloneElement(children, {
        ...children.props,
        children: processChildren(children.props.children, keyPrefix),
      })
    }

    return children
  }

  return (
    <div className="prose prose-sm max-w-none
      prose-headings:font-serif prose-headings:text-ink
      prose-p:font-body prose-p:text-ink prose-p:leading-relaxed
      prose-ul:font-body prose-ol:font-body prose-li:text-ink
      prose-strong:text-ink prose-strong:font-semibold
      prose-em:text-ink prose-em:italic
      prose-code:text-burgundy prose-code:bg-burgundy/5 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:text-sm
      prose-a:text-burgundy prose-a:no-underline hover:prose-a:underline"
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children, ...props }) => {
            const text = getTextContent(children)
            return <p {...props}>{text.includes('[[') ? processChildren(children, 'p') : children}</p>
          },
          li: ({ children, ...props }) => {
            const text = getTextContent(children)
            return <li {...props}>{text.includes('[[') ? processChildren(children, 'li') : children}</li>
          },
        }}
      >
        {cleanedContent}
      </ReactMarkdown>
    </div>
  )
}
