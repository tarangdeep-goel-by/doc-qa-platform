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

Auth state lives in `src/store/authStore.ts` (not `appStore`) — `user`, `isAuthenticated`, `login()`, `logout()`, `refresh()`. Auth API calls are in `src/api/authClient.ts`. UI state is in `src/store/uiStore.ts`.

### API Client

`src/api/client.ts` — typed fetch wrapper. All API calls go through here, no direct fetch in components.

In SaaS mode, client attaches `Authorization: Bearer <token>` header and handles token refresh on 401.

### Routing — React Router v7

```
/login            (LoginPage)
/ (AppLayout)
├── /              (NewChatScreen) — first question creates a chat (auto-routed if no docs selected)
├── /chat/:chatId  (ChatInterface) — chat conversation
└── /documents     (DocumentsPage) — document management (admin, or client with CLIENT_DOCUMENT_VIEW)
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
├── store/          — appStore.ts, authStore.ts, uiStore.ts
├── api/            — client.ts, authClient.ts
├── utils/          — citationParser.ts
└── types/          — index.ts
```

## Design System — Dark, Warm Amber

Dark theme with glass surfaces and amber/teal accents (the purple "dark glass" palette was replaced by a warm amber one on 2026-02-21).

**Color tokens** (in `tailwind.config.js`, semantic names kept from legacy):
- `cream` → `#0c0a09` (page background, near-black)
- `cream-dark` → `#1c1917` (surface/card background)
- `ink` → `#f5f0ea` (primary text, light)
- `ink-light` → `#a8a29e` (secondary text)
- `burgundy` → `#d97706` (accents/CTAs — actually amber)
- `burgundy-light/dark` → `#f59e0b` / `#b45309`
- `cyan` → `#5eead4` (secondary accent — actually teal)
- `glass` → `rgba(245,240,234, 0.03-0.10)` (glass surfaces, borders, hovers)

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
Each chat has `doc_ids` (empty = all documents). If created with `auto_route` and no documents selected, the backend picks documents by BM25 on the first question and saves them to the chat. Documents can be changed later via `PUT /api/chats/{id}/documents`.

### Streaming Responses
`POST /api/chats/{chat_id}/ask` returns SSE stream. Frontend reads the stream with `fetch` + `response.body.getReader()` (in `src/api/client.ts`) and appends chunks to the message in real-time.

### Document Filtering
New chat modal shows multi-select document picker. Missing documents (deleted after chat creation) show warnings.

### Toast Notifications
`react-hot-toast` — success on mutations, error on all API failures.

## Adding a New Feature

1. Add types to `src/types/index.ts`
2. Add API function to `src/api/client.ts`
3. Add store action to `src/store/appStore.ts` (if needed)
4. Use in component via `useAppStore()`
