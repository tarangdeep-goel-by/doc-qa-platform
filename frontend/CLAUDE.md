# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
npm install       # Install dependencies
npm run dev       # Dev server (http://localhost:3000)
npm run build     # Production build
npm run preview   # Preview production build
```

Backend API must be running on port 8000 (proxied via Vite).

## Architecture

### State Management — Zustand Store

Single source of truth: `src/store/appStore.ts`

- No local component state for server data — all documents, chats, messages in the store
- Optimistic updates for user messages (instant feedback, no spinner)
- Auto-reload on mutations (upload/delete refreshes lists)

Key actions: `loadChats()`, `loadDocuments()`, `setActiveChat(chatId)`, `createChat(name, docIds)`, `sendMessage(question)`, `uploadDocument(file)`, `deleteDocument(docId)`

### Auth — Dual Mode Support

Frontend adapts to backend auth mode (detected via `/health` → `auth_required`):

- **B2C mode**: No login, all routes accessible
- **SaaS mode**: Login required, role-based route protection

Auth components:
- `src/components/auth/LoginPage.tsx` — JWT login form
- `src/components/auth/RequireAuth.tsx` — route guard, redirects to login
- `src/components/auth/RequireRole.tsx` — role-based access (admin/client)

Auth state lives in `appStore` — `user`, `isAuthenticated`, `login()`, `logout()`, `refreshToken()`.

### API Client

`src/api/client.ts` — typed fetch wrapper. All API calls go through here, no direct fetch in components.

In SaaS mode, client attaches `Authorization: Bearer <token>` header and handles token refresh on 401.

### Routing — React Router v7

```
/ (AppLayout)
├── /              (WelcomeScreen) — chat list + new chat
├── /chat/:chatId  (ChatInterface) — chat conversation
└── /documents     (DocumentsPage) — document management
```

`AppLayout` loads chats and documents on mount, renders sidebar + outlet.

### Component Structure

```
src/
├── components/
│   ├── auth/       — LoginPage, RequireAuth, RequireRole
│   ├── chat/       — ChatInterface, ChatMessageItem, ChatHeader, NewChatScreen
│   ├── sidebar/    — AppSidebar, ChatListItem
│   ├── modals/     — NewChatModal, UploadModal
│   ├── markdown/   — MarkdownContent, CitationLink
│   └── welcome/    — WelcomeScreen
├── layouts/        — AppLayout
├── pages/          — DocumentsPage
├── store/          — appStore.ts
├── api/            — client.ts
└── types/          — index.ts
```

## Design System — Dark Glass

Dark theme with glass morphism surfaces and purple/cyan accents.

**Color tokens** (in `tailwind.config.js`, semantic names kept from legacy):
- `cream` → `#09090b` (page background, near-black)
- `cream-dark` → `#18181b` (surface/card background)
- `ink` → `#f0f0f0` (primary text, light)
- `ink-light` → `#a1a1aa` (secondary text)
- `burgundy` → `#a78bfa` (accents/CTAs — actually purple/violet)
- `burgundy-light/dark` → `#c4b5fd` / `#8b5cf6`
- `cyan` → `#67e8f9` (secondary accent)
- `glass` → `rgba(255,255,255, 0.04-0.10)` (glass surfaces, borders, hovers)

**Typography**:
- `font-serif` (Fraunces) — display headings
- `font-sans` (Inter Variable) — UI elements
- `font-body` (Literata) — long-form content
- Fluid sizing: `text-fluid-{xs|sm|base|lg|xl|2xl|3xl}` via `clamp()`

**Glass surface pattern**:
```jsx
<div className="bg-glass border border-glass-border rounded-lg hover:bg-glass-hover">
```

Uses `@tailwindcss/typography` plugin with `prose-invert` for dark markdown rendering.

## Key Patterns

### Chat Flow
Each chat has fixed `doc_ids` set at creation. All questions in that chat search only those documents.

### Streaming Responses
`POST /api/chats/{chat_id}/ask` returns SSE stream. Frontend reads `EventSource`-style and appends chunks to the message in real-time.

### Document Filtering
New chat modal shows multi-select document picker. Missing documents (deleted after chat creation) show warnings.

### Toast Notifications
`react-hot-toast` — success on mutations, error on all API failures.

## Adding a New Feature

1. Add types to `src/types/index.ts`
2. Add API function to `src/api/client.ts`
3. Add store action to `src/store/appStore.ts` (if needed)
4. Use in component via `useAppStore()`
