import { useRef, useState } from 'react'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import type { ChatMessage } from '../../types'
import { SourcesBadge, type SourcesBadgeRef } from '../SourcesBadge'
import { MarkdownContent } from '../markdown/MarkdownContent'
import { useAppStore } from '../../store/appStore'

interface Props {
  message: ChatMessage
  prevMessage?: ChatMessage
}

export function ChatMessageItem({ message, prevMessage }: Props) {
  const isUser = message.role === 'user'
  const submitFeedback = useAppStore(s => s.submitFeedback)
  const sourcesBadgeRef = useRef<SourcesBadgeRef>(null)

  const handleCitationClick = (index: number) => {
    sourcesBadgeRef.current?.scrollToSource(index - 1)
  }

  const isStreaming = message.id.startsWith('stream-')
  const showFeedback = !isUser && !isStreaming && message.content.length > 0

  const [poppedBtn, setPoppedBtn] = useState<'up' | 'down' | null>(null)

  const handleFeedback = (fb: 'up' | 'down') => {
    if (message.feedback === fb) return
    setPoppedBtn(fb)
    setTimeout(() => setPoppedBtn(null), 250)
    submitFeedback(message.chat_id, message.id, fb)
  }

  if (isUser) {
    return (
      <div className="flex justify-end mt-6 mb-2 animate-slide-up">
        <div className="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-br-sm bg-burgundy/15 border border-burgundy/20">
          <p className="font-sans text-sm text-ink leading-relaxed">
            {message.content}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`mt-2 mb-4 animate-slide-up ${isStreaming ? 'streaming-cursor' : ''}`}>
      <MarkdownContent
        content={message.content}
        sources={message.sources}
        onCitationClick={handleCitationClick}
      />

      {message.sources && message.sources.length > 0 && (
        <SourcesBadge ref={sourcesBadgeRef} sources={message.sources} />
      )}

      {showFeedback && (
        <div className="flex items-center gap-1 mt-3">
          <button
            onClick={() => handleFeedback('up')}
            className={`p-1.5 rounded-md transition-colors ${
              poppedBtn === 'up' ? 'animate-feedback-pop' : ''
            } ${
              message.feedback === 'up'
                ? 'text-emerald-400 bg-emerald-400/10'
                : 'text-ink/20 hover:text-ink/50 hover:bg-glass-hover'
            }`}
            title="Helpful"
          >
            <ThumbsUp className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => handleFeedback('down')}
            className={`p-1.5 rounded-md transition-colors ${
              poppedBtn === 'down' ? 'animate-feedback-pop' : ''
            } ${
              message.feedback === 'down'
                ? 'text-red-400 bg-red-400/10'
                : 'text-ink/20 hover:text-ink/50 hover:bg-glass-hover'
            }`}
            title="Not helpful"
          >
            <ThumbsDown className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
