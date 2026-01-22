import { MessageSquare, FileText, Sparkles } from 'lucide-react'

export function WelcomeScreen() {
  return (
    <div className="flex-1 flex items-center justify-center p-fluid-2xl">
      <div className="max-w-2xl text-center">
        <div className="mb-fluid-xl">
          <MessageSquare className="w-16 h-16 text-burgundy mx-auto mb-fluid-md" />
          <h1 className="font-serif text-fluid-3xl text-ink mb-fluid-md">
            Welcome to Document Q&A
          </h1>
          <p className="font-sans text-fluid-lg text-ink/70 leading-relaxed">
            Ask questions about your documents using AI-powered semantic search
            and natural language understanding.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-fluid-lg mb-fluid-xl">
          <div className="p-fluid-lg border border-ink/10 rounded-xl">
            <FileText className="w-8 h-8 text-burgundy mb-fluid-sm" />
            <h3 className="font-sans text-fluid-base text-ink font-medium mb-2">
              Multi-Document Search
            </h3>
            <p className="font-sans text-fluid-sm text-ink/60">
              Each chat can search across multiple documents or focus on specific ones.
            </p>
          </div>

          <div className="p-fluid-lg border border-ink/10 rounded-xl">
            <Sparkles className="w-8 h-8 text-burgundy mb-fluid-sm" />
            <h3 className="font-sans text-fluid-base text-ink font-medium mb-2">
              Context-Aware Answers
            </h3>
            <p className="font-sans text-fluid-sm text-ink/60">
              Get detailed answers with citations showing exact page numbers.
            </p>
          </div>
        </div>

        <div className="p-fluid-lg bg-burgundy/5 border border-burgundy/20 rounded-xl">
          <h3 className="font-sans text-fluid-base text-ink font-medium mb-2">
            Get Started
          </h3>
          <p className="font-sans text-fluid-sm text-ink/70">
            Click "New Chat" in the sidebar to create a chat session and start asking questions.
          </p>
        </div>
      </div>
    </div>
  )
}
