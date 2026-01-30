# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Information

**GitHub Repository**: https://github.com/tarangdeep-goel-by/doc-qa-platform
**Owner**: tarangdeep-goel-by

## What This Is

A production-ready full-stack RAG (Retrieval Augmented Generation) platform for document Q&A. Upload PDFs, ask questions, get AI-powered answers with source citations.

**Architecture**: React frontend + FastAPI backend + Qdrant vector DB + Google Gemini

## Quick Start

```bash
# 1. Start services
docker-compose up -d

# 2. Start backend
cd backend && python run_api.py

# 3. Start frontend (separate terminal)
cd frontend && npm run dev

# Access UI: http://localhost:3000
# Access API: http://localhost:8000/docs
```

## Project Structure

```
doc-qa-platform/
├── frontend/          # React + TypeScript UI
│   └── CLAUDE.md      # Frontend architecture & patterns
├── backend/           # FastAPI + RAG pipeline
│   └── CLAUDE.md      # Backend architecture & patterns
├── PROJECT_STATUS.md  # Recent changes & roadmap
└── README.md          # User documentation
```

## High-Level Architecture

```
┌─────────────────────────────────────────┐
│   React Frontend (Port 3000)            │
│   • Zustand state management            │
│   • Tailwind CSS design system          │
│   • Type-safe API client                │
└─────────────────────────────────────────┘
              ↓ HTTP/REST
┌─────────────────────────────────────────┐
│   FastAPI Backend (Port 8000)           │
│   • Document ingestion pipeline         │
│   • Advanced RAG pipeline               │
│   • Multi-chat system                   │
└─────────────────────────────────────────┘
    ↓                        ↓
┌─────────┐            ┌─────────┐
│ Qdrant  │            │ Gemini  │
│ Vector  │            │   LLM   │
│   DB    │            │   API   │
└─────────┘            └─────────┘
```

## Testing

```bash
# Backend: 136 automated tests
docker-compose run --rm test

# Frontend: No test suite yet
```

## Tech Stack Summary

**Frontend**: React 18, TypeScript, Zustand, React Router, Tailwind CSS, Vite

**Backend**: FastAPI, Qdrant, sentence-transformers, Google Gemini 2.5, BM25, cross-encoder reranking, PyPDF2, Pytest

## Where to Find Detailed Information

### Frontend Development
👉 **See `frontend/CLAUDE.md`** for:
- Component architecture
- Zustand state management patterns
- Design system (editorial aesthetic)
- API client implementation
- Development commands
- Troubleshooting

### Backend Development
👉 **See `backend/CLAUDE.md`** for:
- RAG pipeline architecture (query expansion, hybrid search, reranking)
- Document processing pipeline
- Chat management system
- Testing strategy (136 tests)
- Environment configuration
- Performance optimization
- Development commands
- Troubleshooting

### Project Status & Changes
👉 **See `PROJECT_STATUS.md`** for:
- Recent feature implementations
- Completed features
- Current status
- Next steps
- Known issues

### User Documentation
👉 **See `README.md`** for:
- Installation instructions
- Usage examples
- API endpoints
- Configuration options

## Common Cross-Cutting Tasks

### Adding a New Feature

1. **Plan**: Determine if frontend, backend, or both
2. **Backend first** (if needed):
   - Add endpoint to appropriate router
   - Update Pydantic schemas
   - Add tests
   - See `backend/CLAUDE.md` for details
3. **Frontend second**:
   - Update API client types
   - Add store actions if needed
   - Build UI components
   - See `frontend/CLAUDE.md` for details

### Debugging End-to-End

1. **Check backend logs**: `docker-compose logs backend`
2. **Check frontend console**: Browser DevTools
3. **Check network tab**: See actual API requests/responses
4. **Check Qdrant**: http://localhost:6333/dashboard

### Working on Frontend Only

You can develop the frontend independently using the running backend:
```bash
# Terminal 1: Keep backend running
docker-compose up -d

# Terminal 2: Frontend development
cd frontend && npm run dev
```

### Working on Backend Only

You can test the backend independently via API docs:
```bash
# Start services
docker-compose up -d
cd backend && python run_api.py

# Test via Swagger UI
open http://localhost:8000/docs
```

## Key Design Decisions

**Why Zustand?** - Minimal boilerplate, no context providers, perfect for React

**Why Qdrant?** - Self-hosted, production-ready, handles millions of vectors

**Why Gemini?** - Large context window (1M+ tokens), fast, cheap, good instruction following

**Why hybrid search?** - Combines semantic (vector) + keyword (BM25) for better recall

**Why multi-chat system?** - Users want to organize conversations by topic/document

## Important Files

- `.env.example` (backend) - Environment variable template
- `docker-compose.yml` - Service orchestration
- `backend/requirements.txt` - Python dependencies
- `frontend/package.json` - Node dependencies
- `backend/tests/` - 136 automated tests

## Troubleshooting Quick Reference

**"Nothing works":**
```bash
docker-compose down && docker-compose up -d
cd backend && python run_api.py
cd frontend && npm run dev
```

**"Backend tests failing":**
```bash
docker-compose ps  # Ensure all services running
docker-compose logs backend
```

**"Frontend can't reach API":**
- Check backend is running: http://localhost:8000/health
- Check proxy config in `frontend/vite.config.ts`

**"Qdrant connection failed":**
```bash
docker logs doc-qa-qdrant
docker-compose restart qdrant
```

## Development Workflow

1. **Before starting**: Read `PROJECT_STATUS.md` for current state
2. **During development**: Refer to `frontend/CLAUDE.md` or `backend/CLAUDE.md`
3. **After changes**: Update `PROJECT_STATUS.md` if significant
4. **Before committing**: Run backend tests: `docker-compose run --rm test`
5. **After committing**: Push to GitHub: `git push origin main`

## Access Points

- Frontend UI: http://localhost:3000
- API Docs: http://localhost:8000/docs
- API Health: http://localhost:8000/health
- Qdrant Dashboard: http://localhost:6333/dashboard

---

**Remember**: This file is the overview. Detailed implementation guidance lives in:
- `frontend/CLAUDE.md` - React, TypeScript, Tailwind patterns
- `backend/CLAUDE.md` - FastAPI, RAG, testing patterns
