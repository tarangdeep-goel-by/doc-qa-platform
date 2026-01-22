# Document Q&A Frontend

User-facing chat interface for the Document Q&A Platform.

## Design Philosophy

Editorial-inspired interface with refined typography and sophisticated spacing. Combines magazine-style layouts with modern interaction patterns.

### Key Features

- **Chat Interface**: Clean conversation flow with questions and AI-generated answers
- **Document Filtering**: Select specific documents or search across all
- **Source Citations**: Every answer includes relevant source excerpts with relevance scores
- **Editorial Typography**: Fraunces (display), Literata (body), Inter (UI)
- **Responsive Design**: Fluid typography and spacing that adapts to screen size

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

The dev server runs on `http://localhost:3000` and proxies API requests to `http://localhost:8000`.

## Tech Stack

- **React 18** + TypeScript
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling
- **Google Fonts** - Fraunces, Literata, Inter

## Project Structure

```
src/
├── components/
│   ├── ChatMessage.tsx       # Question and answer display
│   ├── DocumentSelector.tsx  # Multi-select document filter
│   ├── MessageInput.tsx      # Question input with submit
│   └── SourceCitation.tsx    # Individual source display
├── types/
│   └── index.ts              # TypeScript definitions
├── api/
│   └── client.ts             # API client functions
├── App.tsx                   # Main application
├── main.tsx                  # Entry point
└── index.css                 # Global styles + Tailwind
```

## API Integration

Connects to backend API at `/api`:

- `GET /api/query/documents` - List available documents
- `POST /api/query/ask` - Submit question with optional doc_ids filter

## Design System

### Colors

- **Cream** (`#faf9f7`) - Background
- **Ink** (`#1a1a2e`) - Primary text
- **Burgundy** (`#8b4049`) - Accents and CTAs

### Typography Scale

Uses fluid typography with `clamp()` for responsive sizing:

- Display: `fluid-3xl` (1.875rem - 2.625rem)
- Heading: `fluid-2xl` (1.5rem - 2rem)
- Body: `fluid-lg` (1.125rem - 1.375rem)
- Small: `fluid-sm` (0.875rem - 1rem)

### Spacing Scale

Fluid spacing that breathes on larger screens:

- `fluid-xs`: 0.5rem - 0.625rem
- `fluid-sm`: 0.75rem - 1rem
- `fluid-md`: 1rem - 1.375rem
- `fluid-lg`: 1.5rem - 2rem
- `fluid-xl`: 2rem - 2.75rem
- `fluid-2xl`: 3rem - 4.125rem

## Development

### Prerequisites

- Node.js 18+
- Backend API running on port 8000

### Environment

No environment variables needed - API proxy configured in `vite.config.ts`.

### Hot Reload

Vite provides instant hot module replacement. Save any file and see changes immediately.

## Building for Production

```bash
npm run build
```

Outputs to `dist/` directory. Serve with any static host:

```bash
npm run preview
```

## Design Decisions

**Why editorial aesthetic?**
- Document Q&A is fundamentally about reading and understanding text
- Editorial design prioritizes readability and hierarchy
- Differentiates from typical "AI chat" interfaces

**Why serif fonts?**
- Answers feel more authoritative and considered
- Better readability for longer content
- Creates warm, scholarly atmosphere

**Why asymmetric layout?**
- Questions right-aligned, answers left-aligned full-width
- Creates visual rhythm and conversation flow
- Prevents monotonous centered layouts

**Why show relevance scores?**
- Transparency in search results
- Users can judge source quality
- Shown subtly (not as metrics) to avoid overwhelming

## Future Enhancements

- [ ] Conversation history persistence
- [ ] Export conversation to PDF/Markdown
- [ ] Keyboard shortcuts
- [ ] Dark mode
- [ ] Streaming responses
- [ ] Highlight matching text in sources
