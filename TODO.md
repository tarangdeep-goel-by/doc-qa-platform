# TODO - Multi-Chat Interface Implementation

**Status**: Sprint 3 - Frontend Implementation
**Last Updated**: 2026-01-21

---

## Current Sprint: Frontend Multi-Chat Interface

### State Management
- [ ] Create `src/store/appStore.ts`
  - Define state interface (chats, messages, documents, activeChat)
  - Implement actions (createChat, deleteChat, sendMessage, etc.)
  - Add API integration with error handling

### Layout Components
- [ ] Create `src/layouts/AppLayout.tsx`
  - Sidebar + main content area layout
  - Responsive design (mobile collapsible sidebar)

- [ ] Create `src/components/sidebar/AppSidebar.tsx`
  - Chat list (sorted by updated_at)
  - "New Chat" button
  - Active chat highlighting

- [ ] Create `src/components/sidebar/ChatListItem.tsx`
  - Chat name display
  - Message count badge
  - Last updated time
  - Delete button

### Chat Components
- [ ] Create `src/components/chat/ChatInterface.tsx`
  - Refactor from current App.tsx
  - Use activeChat from store
  - Message list + input area

- [ ] Create `src/components/chat/ChatHeader.tsx`
  - Chat name with edit capability
  - Document selector showing chat's doc_ids
  - Chat actions (rename, delete)

- [ ] Create `src/components/welcome/WelcomeScreen.tsx`
  - Empty state when no chat selected
  - "Create your first chat" prompt
  - Quick start guide

### Update Existing Components
- [ ] Update `src/components/ChatMessage.tsx`
  - Replace chunk_text preview with page number
  - Format: "Page {page_num}"
  - Show source count per document

- [ ] Update `src/components/SourceCitation.tsx`
  - Add clickable "View source →" link
  - Implement openDocumentAtPage(docId, pageNum)
  - Opens: `/api/admin/documents/{doc_id}/file#page={page_num}`

### Services & API
- [ ] Create `src/services/chatsService.ts`
  - createChat(name, docIds)
  - listChats()
  - getChat(chatId)
  - renameChat(chatId, name)
  - deleteChat(chatId)
  - askInChat(chatId, question, topK)

- [ ] Update `src/api/client.ts`
  - Add BASE_URL for chat endpoints
  - Add error handling utilities

### Types & Interfaces
- [ ] Update `src/types/index.ts`
  - Add Chat interface
  - Add ChatMessage interface
  - Update Source interface with page_num
  - Add API response types

### Routing
- [ ] Update `src/App.tsx`
  - Add React Router setup
  - Define routes (/, /chat/:chatId)
  - Wrap with BrowserRouter

- [ ] Create route components
  - Home route → WelcomeScreen or redirect to first chat
  - Chat route → ChatInterface with chatId param

### Utilities
- [ ] Create `src/utils/sourceViewer.ts`
  - openDocumentAtPage(docId: string, pageNum: number)
  - window.open with PDF + anchor

---

## Testing Tasks

### Manual Testing
- [ ] Re-upload test PDF to get page numbers in database
- [ ] Create 3 test chats with different doc selections
- [ ] Send messages to each chat
- [ ] Verify chat list updates correctly
- [ ] Verify switching between chats loads correct messages
- [ ] Refresh browser → verify persistence
- [ ] Click source citation → verify PDF opens at correct page
- [ ] Test rename chat functionality
- [ ] Test delete chat functionality
- [ ] Test with no documents selected (empty chat)

### Edge Cases
- [ ] No chats exist (show welcome screen)
- [ ] No documents uploaded (show message)
- [ ] No sources found for query
- [ ] Long chat names (truncate in UI)
- [ ] Many chats (test scrolling in sidebar)
- [ ] Large documents (test page number display)

---

## Phase 4: D2C Variant (Future Sprint)

- [ ] Clone frontend directory to frontend-d2c
- [ ] Create `DocumentUploader.tsx` component
  - Drag-drop file upload
  - Progress indicator
  - Success/error feedback

- [ ] Create `DocumentLibrary.tsx` component
  - List user's uploaded documents
  - Delete functionality
  - Document details (pages, size, etc.)

- [ ] Create `DocumentCard.tsx` component
  - Document preview
  - Metadata display
  - Actions (view, delete)

- [ ] Add upload UI to main interface
  - Upload button in sidebar or header
  - Modal or page for document management

- [ ] Update package.json scripts
  - Add separate dev/build scripts for B2B vs D2C

---

## Documentation Tasks

- [ ] Update main README.md with multi-chat features
- [ ] Add screenshots of new UI
- [ ] Document API endpoints in CLAUDE.md
- [ ] Add troubleshooting section for common issues
- [ ] Update PROJECT_STATUS.md with completion status

---

## Optimization Tasks (Post-MVP)

- [ ] Add loading skeletons for chat list
- [ ] Add optimistic UI updates (instant feedback)
- [ ] Cache chat messages in localStorage
- [ ] Add infinite scroll for long message lists
- [ ] Add search/filter for chats
- [ ] Add keyboard shortcuts (Ctrl+K for new chat, etc.)
- [ ] Add markdown support in messages
- [ ] Add copy button for answers
- [ ] Add export chat history feature

---

## Bug Fixes / Improvements

- [ ] Handle case where chat has empty doc_ids array
- [ ] Add proper error boundaries in React components
- [ ] Add retry logic for failed API calls
- [ ] Add debounce for search/filter inputs
- [ ] Add confirmation dialog before deleting chat
- [ ] Add toast notifications for success/error
- [ ] Improve mobile responsiveness
- [ ] Add dark mode toggle (if needed)

---

## Notes

- Backend is fully functional and tested via /docs API explorer
- Frontend structure follows ai-data-analyst-v2 pattern (proven architecture)
- Focus on B2B variant first (simpler, no upload UI needed)
- D2C variant is a clone + add upload components
- Use lucide-react for icons (already installed)
- Use date-fns for timestamp formatting (already installed)
