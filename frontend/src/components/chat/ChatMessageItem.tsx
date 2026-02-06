import { useRef } from 'react'
import { User, Bot } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import type { ChatMessage } from '../../types'
import { SourcesBadge, type SourcesBadgeRef } from '../SourcesBadge'
import { MarkdownContent } from '../markdown/MarkdownContent'

interface Props {
  message: ChatMessage
}

export function ChatMessageItem({ message }: Props) {
  const isUser = message.role === 'user'
  // Backend sends UTC timestamps without Z suffix — append Z so JS parses as UTC
  const utcTimestamp = message.timestamp.endsWith('Z') ? message.timestamp : message.timestamp + 'Z'
  const timeAgo = formatDistanceToNow(new Date(utcTimestamp), { addSuffix: true })

  // Ref for SourcesBadge (for scrolling on citation click)
  const sourcesBadgeRef = useRef<SourcesBadgeRef>(null)

  const handleCitationClick = (index: number) => {
    // Call scrollToSource on SourcesBadge (0-indexed)
    sourcesBadgeRef.current?.scrollToSource(index - 1)
  }

  return (
    <div className={`flex gap-fluid-md ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan/10 flex items-center justify-center">
          <Bot className="w-5 h-5 text-cyan" />
        </div>
      )}

      {/* Message content */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block p-fluid-md rounded-xl ${
            isUser
              ? 'bg-burgundy text-cream'
              : 'bg-cyan/10 text-ink'
          }`}
        >
          {isUser ? (
            <p className="font-sans text-fluid-base whitespace-pre-wrap">
              {message.content}
            </p>
          ) : (
            <MarkdownContent
              content={message.content}
              sources={message.sources}
              onCitationClick={handleCitationClick}
            />
          )}
        </div>

        {/* Sources for assistant messages */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourcesBadge ref={sourcesBadgeRef} sources={message.sources} />
        )}

        {/* Timestamp */}
        <p className="font-sans text-fluid-xs text-ink/40 mt-2">
          {timeAgo}
        </p>
      </div>

      {/* Avatar for user */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-ink/10 flex items-center justify-center">
          <User className="w-5 h-5 text-ink/60" />
        </div>
      )}
    </div>
  )
}
