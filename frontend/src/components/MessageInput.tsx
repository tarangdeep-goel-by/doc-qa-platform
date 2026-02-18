import { useState, FormEvent, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'

interface Props {
  onSubmit: (question: string) => void
  disabled: boolean
}

export function MessageInput({ onSubmit, disabled }: Props) {
  const [question, setQuestion] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (question.trim() && !disabled) {
      onSubmit(question.trim())
      setQuestion('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="flex items-end gap-3 rounded-xl border border-glass-border bg-glass backdrop-blur-sm focus-within:border-burgundy/30 transition-colors">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask a question about your documents..."
          className="flex-1 resize-none font-sans text-fluid-base text-ink placeholder:text-ink/25 bg-transparent focus:outline-none px-4 py-3 min-h-[2.75rem] max-h-40 disabled:opacity-50 disabled:cursor-not-allowed"
          rows={1}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement
            target.style.height = 'auto'
            target.style.height = Math.min(target.scrollHeight, 160) + 'px'
          }}
        />
        <button
          type="submit"
          disabled={disabled || !question.trim()}
          className="flex-shrink-0 p-2.5 m-1.5 rounded-lg
            bg-burgundy text-cream hover:bg-burgundy-dark
            disabled:bg-ink/10 disabled:text-ink/25 disabled:cursor-not-allowed
            transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <p className="font-sans text-[0.65rem] text-ink/25 mt-1.5 text-center">
        Enter to send · Shift+Enter for new line
      </p>
    </form>
  )
}
