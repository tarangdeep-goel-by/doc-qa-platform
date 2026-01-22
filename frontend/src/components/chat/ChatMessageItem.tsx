import { User, Bot } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import type { ChatMessage } from '../../types'
import { SourceCitation } from '../SourceCitation'

interface Props {
  message: ChatMessage
}

export function ChatMessageItem({ message }: Props) {
  const isUser = message.role === 'user'
  const timeAgo = formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })

  return (
    <div className={`flex gap-fluid-md ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-burgundy/10 flex items-center justify-center">
          <Bot className="w-5 h-5 text-burgundy" />
        </div>
      )}

      {/* Message content */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block p-fluid-md rounded-xl ${
            isUser
              ? 'bg-burgundy text-cream'
              : 'bg-ink/5 text-ink'
          }`}
        >
          <p className="font-sans text-fluid-base whitespace-pre-wrap">
            {message.content}
          </p>
        </div>

        {/* Sources for assistant messages */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-fluid-sm space-y-2">
            <p className="font-sans text-fluid-xs text-ink/50 uppercase tracking-wider">
              Sources
            </p>
            <div className="space-y-1">
              {message.sources.map((source, idx) => (
                <SourceCitation key={idx} source={source} index={idx} />
              ))}
            </div>
          </div>
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
