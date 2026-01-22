# Multi-Chat Interface Implementation Plan

## Overview
Transform doc-qa-platform from single-chat to multi-session interface with improved citations and two deployment variants (B2B SaaS and D2C).

---

## Phase 1: Backend - Page Number Tracking ✅ COMPLETED

### Changes Made:
1. **document_processor.py** - Updated `extract_text_from_pdf` to return page_data list with page numbers
2. **chunker.py** - Added `chunk_with_page_tracking()` method to preserve page numbers
3. **models.py** - Added `page_num` field to DocumentChunk
4. **vector_store.py** - Payload now includes page_num
5. **schemas.py** - Added `page_num` to SourceInfo
6. **qa_engine.py** - Sources now include page_num from payload
7. **admin.py** - Upload flow uses new page tracking methods

**Result**: All chunks now have page number metadata stored in Qdrant.

---

## Phase 2: Backend - Chat Management ✅ COMPLETED

### Changes Made:
1. **models.py** - Added Chat and ChatMessage dataclasses
2. **chat_manager.py** - New ChatManager class for session management
   - Storage: `data/chats/{chat_id}/metadata.json` + `messages.json`
   - Methods: create_chat, get_chat, list_chats, add_message, delete_chat, rename_chat
3. **schemas.py** - Added chat schemas (CreateChatRequest, ChatResponse, etc.)
4. **chats.py** - New router with endpoints:
   - POST /api/chats - Create chat
   - GET /api/chats - List chats
   - GET /api/chats/{id} - Get chat details
   - PATCH /api/chats/{id} - Rename chat
   - DELETE /api/chats/{id} - Delete chat
   - POST /api/chats/{id}/ask - Ask question in chat context
5. **qa_engine.py** - Updated to accept optional chat_history parameter
6. **main.py** - Initialize ChatManager and register chats router
7. **admin.py** - Added PDF serving endpoint: GET /api/admin/documents/{doc_id}/file

**Result**: Backend supports multi-chat sessions with document associations and persistence.

---

## Phase 3: Frontend - Multi-Chat Interface (B2B Version) 🔄 IN PROGRESS

### Completed:
- ✅ Installed dependencies: zustand, react-router-dom, lucide-react, date-fns

### Remaining Tasks:

#### 3.1 State Management
- **Create**: `src/store/appStore.ts`
- Zustand store with:
  - Chats management (create, list, delete, setActive)
  - Messages management
  - Documents state
  - API integration

#### 3.2 Layout Components
- **Create**: `src/layouts/AppLayout.tsx` - Main shell with sidebar + content area
- **Create**: `src/components/sidebar/AppSidebar.tsx` - Chat list + new chat button
- **Create**: `src/components/sidebar/ChatListItem.tsx` - Individual chat item

#### 3.3 Chat Components
- **Create**: `src/components/chat/ChatInterface.tsx` - Main chat view (refactor from App)
- **Create**: `src/components/chat/ChatHeader.tsx` - Document selector + chat title
- **Create**: `src/components/welcome/WelcomeScreen.tsx` - Empty state
- **Update**: `src/components/ChatMessage.tsx` - Show page numbers instead of chunk text
- **Update**: `src/components/SourceCitation.tsx` - Clickable page links

#### 3.4 Services & Types
- **Create**: `src/services/chatsService.ts` - Chat API methods
- **Update**: `src/types/index.ts` - Add Chat and Message interfaces
- **Update**: `src/api/client.ts` - Add chat endpoints

#### 3.5 Routing
- **Update**: `src/App.tsx` - Add React Router
- Routes:
  - `/` - Welcome screen (no active chat)
  - `/chat/:chatId` - Chat interface

#### 3.6 Citation Behavior
- Implement: `openDocumentAtPage(docId, pageNum)`
- Opens PDF in new tab with anchor: `/api/admin/documents/{doc_id}/file#page={pageNum}`

---

## Phase 4: D2C Variant (Future)

### Approach:
1. Clone `frontend/` to `frontend-d2c/`
2. Add upload components:
   - `DocumentUploader.tsx` - Drag-drop upload
   - `DocumentLibrary.tsx` - User's doc list
   - `DocumentCard.tsx` - Doc item with delete
3. Enable upload UI in interface
4. Same backend (no changes needed)

---

## Implementation Status

### ✅ Completed (Sprints 1-2):
- Backend page number tracking
- Backend chat management
- PDF serving endpoint
- Frontend dependencies installed

### 🔄 In Progress (Sprint 3):
- Frontend multi-chat interface

### ⏳ Remaining:
- Frontend state management
- Frontend UI components
- Frontend routing
- Testing page tracking
- Testing multi-chat interface
- D2C variant (Phase 4)

---

## Testing Plan

### Page Number Tracking
1. Re-upload a test PDF
2. Ask question and verify sources show page numbers
3. Check Qdrant payload includes page_num

### Chat Persistence
1. Create multiple chats
2. Send messages to each
3. Refresh browser - verify chats persist
4. Switch between chats - verify messages stay separate

### Citations
1. Click source citation
2. Verify PDF opens in new tab
3. Verify page anchor works (Chrome/Edge)

---

## Key Design Decisions

1. **Citation Behavior**: Open PDF in new tab with `#page=N` anchor
2. **Document Selection**: Per-chat (each chat has associated doc_ids)
3. **Build Priority**: B2B first, then D2C
4. **D2C Document Scope**: User-global library (reuse docs across chats)
5. **Chat Naming**: Auto-generate from first question (allow rename later)

---

## File Changes Summary

### Backend Files Modified:
- `backend/src/document_processor.py`
- `backend/src/chunker.py`
- `backend/src/vector_store.py`
- `backend/src/models.py`
- `backend/src/qa_engine.py`
- `backend/api/schemas.py`
- `backend/api/routers/admin.py`
- `backend/api/routers/query.py`
- `backend/api/main.py`

### Backend Files Created:
- `backend/src/chat_manager.py`
- `backend/api/routers/chats.py`

### Frontend Files (To Be Created):
- `src/store/appStore.ts`
- `src/layouts/AppLayout.tsx`
- `src/components/sidebar/AppSidebar.tsx`
- `src/components/sidebar/ChatListItem.tsx`
- `src/components/chat/ChatInterface.tsx`
- `src/components/chat/ChatHeader.tsx`
- `src/components/welcome/WelcomeScreen.tsx`
- `src/services/chatsService.ts`

### Frontend Files (To Be Modified):
- `src/App.tsx`
- `src/components/ChatMessage.tsx`
- `src/components/SourceCitation.tsx`
- `src/types/index.ts`
- `src/api/client.ts`
- `package.json` ✅

---

## Next Steps

1. Create Zustand store (`appStore.ts`)
2. Create layout components (`AppLayout`, `AppSidebar`)
3. Refactor existing chat UI into `ChatInterface.tsx`
4. Add routing with React Router
5. Update citation components for page numbers
6. Test end-to-end with re-uploaded documents
7. Create D2C variant (Phase 4)
