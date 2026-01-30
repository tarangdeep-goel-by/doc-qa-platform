# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Information

**GitHub Repository**: https://github.com/tarangdeep-goel-by/doc-qa-platform
**Owner**: tarangdeep-goel-by
**Part of**: Document Q&A Platform (multi-repo project)

## Development Commands

```bash
# Install dependencies
npm install

# Development server (http://localhost:3000)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

**Note**: Backend API must be running on port 8000 for API calls to work (proxied via Vite).

## Architecture Overview

### State Management - Zustand Store

**Single source of truth**: `src/store/appStore.ts`

The app uses a centralized Zustand store for all application state. Key patterns:

1. **No local component state for server data** - All documents, chats, and messages live in the store
2. **Optimistic updates** - User messages added immediately, then replaced with server response
3. **Auto-reload on mutations** - After document upload/delete, store refreshes document list
4. **Toast notifications** - Success/error feedback via react-hot-toast

**Store structure**:
```typescript
{
  chats: Chat[]              // All user chats
  activeChat: Chat | null    // Currently open chat
  documents: Document[]      // All uploaded documents
  messages: ChatMessage[]    // Messages for activeChat only
  loading: boolean           // Global loading state
  error: string | null       // Global error state
}
```

**Key actions**:
- `loadChats()` - Fetch all chats from API
- `loadDocuments()` - Fetch all documents from API
- `setActiveChat(chatId)` - Load chat + messages
- `createChat(name, docIds)` - Create new chat with document filter
- `sendMessage(question)` - Send message in active chat (optimistic update)
- `uploadDocument(file)` - Upload PDF with duplicate detection
- `deleteDocument(docId)` - Delete doc + update chats that reference it

### API Client - Type-Safe Fetch Wrapper

**Location**: `src/api/client.ts`

All API calls go through typed functions. No direct fetch calls in components.

**Pattern**:
```typescript
export async function functionName(params): Promise<Type> {
  const response = await fetch(`${API_BASE}/endpoint`, { ... })
  if (!response.ok) {
    throw new Error('Human-readable error')
  }
  return response.json()
}
```

**Endpoints**:
- `GET /api/query/documents` - List documents
- `POST /api/query/ask` - Ask question (legacy, not used in chat flow)
- `GET /api/chats` - List all chats
- `POST /api/chats` - Create chat
- `GET /api/chats/:id` - Get chat + messages
- `PATCH /api/chats/:id` - Rename chat
- `DELETE /api/chats/:id` - Delete chat
- `POST /api/chats/:id/ask` - Ask question in chat
- `POST /api/admin/upload` - Upload document
- `DELETE /api/admin/documents/:id` - Delete document

### Routing - React Router v7

**Pattern**: Layout wraps all pages, loads data on mount

```
/ (AppLayout)
├── / (WelcomeScreen) - Chat list + new chat button
├── /chat/:chatId (ChatInterface) - Chat conversation
└── /documents (DocumentsPage) - Document management
```

**AppLayout** (`src/layouts/AppLayout.tsx`):
- Loads chats and documents on mount
- Renders sidebar (chat list, new chat, documents link)
- Outlet for page content

### Component Architecture

**Component categories**:

1. **Pages** (`src/pages/`) - Route-level components
   - `DocumentsPage.tsx` - Document upload/delete management

2. **Layouts** (`src/layouts/`) - Shared page structure
   - `AppLayout.tsx` - Sidebar + content wrapper

3. **Features** (`src/components/`)
   - `chat/` - Chat interface, messages, header
   - `sidebar/` - Sidebar, chat list items
   - `modals/` - New chat modal, upload modal
   - `welcome/` - Welcome screen

4. **Shared** (`src/components/`) - Reusable UI
   - `SourceCitation.tsx` - Source with relevance score
   - `DocumentSelector.tsx` - Multi-select document filter
   - `MessageInput.tsx` - Question input with submit

### Design System - Editorial Aesthetic

**Core philosophy**: Magazine-style typography and spacing, serif fonts, asymmetric layouts

**Color palette** (Tailwind config):
- `cream` (#faf9f7) - Background, warm and inviting
- `ink` (#1a1a2e) - Primary text, deep blue-black
- `burgundy` (#8b4049) - Accents, CTAs, links

**Typography**:
- `font-serif` (Fraunces) - Display headings, elegant and bold
- `font-body` (Literata) - Long-form content, optimized for reading
- `font-sans` (Inter Variable) - UI elements, clean and modern

**Fluid sizing** (responsive without breakpoints):
- Font sizes: `text-fluid-{xs|sm|base|lg|xl|2xl|3xl}`
- Spacing: `fluid-{xs|sm|md|lg|xl|2xl}`
- Uses `clamp(min, preferred, max)` for smooth scaling

**Example**:
```jsx
<h1 className="font-serif text-fluid-3xl text-ink">
  {/* Scales from 1.875rem to 2.625rem */}
</h1>

<div className="space-y-fluid-md">
  {/* Gap scales from 1rem to 1.375rem */}
</div>
```

## Key Design Patterns

### 1. Chat Message Rendering

**Asymmetric layout**:
- User messages: Right-aligned, smaller, ink text
- Assistant messages: Full-width, larger, body font
- Sources: Below assistant message, expandable

**Implementation**: `src/components/chat/ChatMessageItem.tsx`

### 2. Document Filtering in Chats

Each chat has a fixed `doc_ids` array set at creation. Questions in that chat only search those documents.

**Flow**:
1. User clicks "New Chat"
2. Modal shows document selector (multi-select)
3. User selects documents + names chat
4. `createChat(name, docIds)` creates chat with filter
5. All questions in that chat use those doc_ids

**Missing documents**: If a document in `doc_ids` gets deleted, chat shows warning with missing doc names.

### 3. Optimistic Message Updates

When sending a message:
1. Immediately add user message to UI (`temp-${Date.now()}` ID)
2. Call API
3. Add assistant response when received
4. No loading spinner for user message (instant feedback)

**Code**: `src/store/appStore.ts` - `sendMessage()`

### 4. Error Handling

**Pattern**: Try/catch → Set error in store → Toast notification

```typescript
try {
  await api.uploadDocument(file)
  toast.success('Document uploaded successfully')
} catch (error) {
  const message = error instanceof Error ? error.message : 'Generic error'
  toast.error(message)
  throw error // Re-throw if caller needs to handle
}
```

### 5. Duplicate Detection

**Documents**: Check for duplicate filename before upload (frontend)
- If found, show detailed error: upload date, doc_id, suggestion to rename

**Backend also validates** with 409 status code (fallback)

## TypeScript Patterns

### Type Definitions

**Location**: `src/types/index.ts`

**Key types**:
- `Document` - Document metadata (matches backend schema)
- `Chat` - Chat with doc_ids filter
- `ChatMessage` - Message with role (user/assistant)
- `Source` - Retrieved chunk with relevance score
- `QueryResponse` - Legacy response (not used in chat flow)

### Type Safety in API Calls

**Pattern**: Always type function return values

```typescript
// Good
export async function fetchChats(): Promise<Chat[]> {
  // ...
}

// Bad
export async function fetchChats() {
  // Returns any
}
```

## Component Development Guidelines

### When to use Zustand vs Props

**Use Zustand for**:
- Server data (documents, chats, messages)
- Global UI state (loading, error)
- Actions that mutate server state

**Use Props for**:
- Presentational data (text, icons, colors)
- Event handlers passed from parent
- Component-specific UI state (hover, focus)

### Modal Pattern

**Location**: `src/components/modals/`

**Pattern**: Controlled visibility via parent state

```typescript
const [isOpen, setIsOpen] = useState(false)

<NewChatModal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  onSuccess={(chat) => {
    navigate(`/chat/${chat.id}`)
    setIsOpen(false)
  }}
/>
```

### Toast Notifications

**When to show**:
- Success: Document upload, chat delete, chat rename
- Error: All API failures, duplicate documents

**Pattern**:
```typescript
import toast from 'react-hot-toast'

// Success
toast.success('Action completed')

// Error (multi-line)
toast.error('Error title\n\nDetail line 1\nDetail line 2')
```

## Styling Conventions

### Tailwind Class Order

**Recommended order**:
1. Layout (flex, grid, block)
2. Sizing (w-, h-, max-w-)
3. Spacing (p-, m-, space-)
4. Typography (font-, text-, leading-)
5. Colors (bg-, text-, border-)
6. Effects (shadow-, rounded-, opacity-)
7. States (hover:, focus:, active:)

### Fluid Typography Usage

**When to use**:
- Headings: `text-fluid-{xl|2xl|3xl}`
- Body text: `text-fluid-{base|lg}`
- Small text: `text-fluid-{xs|sm}`

**When NOT to use**:
- Fixed UI elements (buttons, badges)
- Icons
- Precise alignment requirements

### Color Usage

**Backgrounds**:
- Page: `bg-cream`
- Cards/Panels: `bg-white` or `bg-cream-dark`
- Hover: `hover:bg-cream-dark`

**Text**:
- Primary: `text-ink`
- Secondary: `text-ink/70`
- Links/CTAs: `text-burgundy`

**Borders**:
- Subtle: `border-ink/10`
- Emphasis: `border-burgundy`

## Common Development Tasks

### Adding a New API Endpoint

1. Add types to `src/types/index.ts`
2. Add function to `src/api/client.ts`
3. Add action to `src/store/appStore.ts` (if needed)
4. Use in component via `useAppStore()`

### Adding a New Page

1. Create component in `src/pages/`
2. Add route to `src/App.tsx`
3. Add navigation link to sidebar/header

### Modifying the Design System

**Colors**: Edit `tailwind.config.js` → `theme.extend.colors`

**Typography**: Edit `tailwind.config.js` → `theme.extend.fontFamily`

**Fluid sizes**: Edit `tailwind.config.js` → `theme.extend.fontSize` or `theme.extend.spacing`

### Testing API Integration

1. Start backend: `cd ../backend && python run_api.py`
2. Start frontend: `npm run dev`
3. Upload test document via UI
4. Create chat with that document
5. Ask questions and verify responses

## Performance Considerations

### Bundle Size

**Current dependencies** (keep minimal):
- React + React DOM
- React Router
- Zustand (tiny state management)
- Tailwind (purged in production)
- lucide-react (tree-shakable icons)

**Avoid adding**:
- Large UI libraries (Material-UI, Ant Design)
- Moment.js (use date-fns for small tasks)
- Lodash (use native JS methods)

### Vite Build Optimization

**Already configured**:
- Automatic code splitting
- Tree shaking
- CSS purging via Tailwind

**Production build size**: ~150KB gzipped (target)

### API Call Optimization

**Current optimizations**:
- Documents/chats loaded once on mount
- Messages loaded only when chat opens
- No polling (future: consider WebSockets for live updates)

## Troubleshooting

### "API request failed"

1. Check backend is running: `http://localhost:8000/docs`
2. Check proxy config in `vite.config.ts`
3. Inspect network tab for actual error

### "Document upload fails silently"

1. Check file size (backend may have limits)
2. Check file format (PDF only currently)
3. Check backend logs for processing errors

### "Chat not loading messages"

1. Check `activeChat` in store (may be null)
2. Verify `setActiveChat(chatId)` was called
3. Check network tab for `/api/chats/:id` response

### "Styles not updating"

1. Restart dev server (Tailwind purge cache issue)
2. Check class name is in `content` paths (tailwind.config.js)
3. Verify class exists in Tailwind (check docs)

## Future Enhancements

**Phase 1: UX Improvements**
- Keyboard shortcuts (Cmd+K for new chat)
- Markdown rendering in answers
- Code syntax highlighting
- Copy to clipboard buttons

**Phase 2: Advanced Features**
- Dark mode toggle
- Export chat to PDF/Markdown
- Search within chat history
- Streaming responses (chunked generation)

**Phase 3: Collaboration**
- Share chat with read-only link
- User authentication
- Multi-user document access

**Phase 4: Performance**
- Virtual scrolling for long chats
- Lazy load chat list
- Service worker for offline access
- WebSocket for real-time updates
