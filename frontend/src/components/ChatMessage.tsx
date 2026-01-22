import type { Message } from '../types'
import { SourceCitation } from './SourceCitation'

interface Props {
  message: Message
}

export function ChatMessage({ message }: Props) {
  if (message.type === 'question') {
    return (
      <div className="flex justify-end mb-fluid-lg">
        <div className="max-w-2xl">
          <div className="text-right mb-2">
            <span className="font-sans text-fluid-xs text-ink/40 uppercase tracking-wider">
              You asked
            </span>
          </div>
          <div className="bg-ink/5 border-l-2 border-burgundy pl-fluid-md pr-fluid-sm py-fluid-sm">
            <p className="font-body text-fluid-base text-ink leading-relaxed">
              {message.content}
            </p>
            {message.filteredDocs && message.filteredDocs.length > 0 && (
              <div className="mt-2 pt-2 border-t border-ink/10">
                <span className="font-sans text-fluid-xs text-ink/40">
                  Searching in {message.filteredDocs.length} document
                  {message.filteredDocs.length > 1 ? 's' : ''}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mb-fluid-2xl">
      <div className="mb-3">
        <span className="font-sans text-fluid-xs text-ink/40 uppercase tracking-wider">
          Answer
        </span>
      </div>

      {/* Answer */}
      <div className="max-w-4xl">
        <div className="prose prose-lg max-w-none">
          <div
            className="font-body text-fluid-lg text-ink leading-relaxed"
            style={{ hyphens: 'auto' }}
          >
            {message.content.split('\n').map((paragraph, i) => (
              <p key={i} className="mb-4 last:mb-0">
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      </div>

      {/* Sources */}
      {message.sources && message.sources.length > 0 && (
        <div className="mt-fluid-xl pt-fluid-lg border-t border-ink/10">
          <h3 className="font-sans text-fluid-sm text-ink/60 uppercase tracking-wider mb-fluid-md">
            Sources ({message.sources.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-fluid-lg">
            {message.sources.map((source, i) => (
              <SourceCitation key={i} source={source} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
