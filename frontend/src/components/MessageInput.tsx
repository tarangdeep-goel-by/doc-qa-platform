import { useState, FormEvent, KeyboardEvent } from 'react'

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
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Ask a question about your documents..."
        className="w-full resize-none font-body text-fluid-base text-ink placeholder:text-ink/30 bg-transparent border-2 border-ink/10 focus:border-burgundy focus:outline-none px-fluid-md py-fluid-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        rows={3}
      />
      <div className="flex items-center justify-between mt-2">
        <span className="font-sans text-fluid-xs text-ink/40">
          Press Enter to send, Shift+Enter for new line
        </span>
        <button
          type="submit"
          disabled={disabled || !question.trim()}
          className="px-fluid-md py-fluid-xs font-sans text-fluid-sm text-cream bg-burgundy hover:bg-burgundy-dark disabled:bg-ink/20 disabled:cursor-not-allowed transition-colors uppercase tracking-wider"
        >
          {disabled ? 'Thinking...' : 'Ask'}
        </button>
      </div>
    </form>
  )
}
