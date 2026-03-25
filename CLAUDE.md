# caAI — Indian Tax Law RAG System

## Project Overview
RAG-based Q&A system for Indian tax law (Income Tax Act, GST Act, TDS rates). Answers questions with citations to specific sections, confidence scoring, and disclaimers.

## Architecture
- **Backend**: Python FastAPI at `backend/` — RAG pipeline, pgvector retrieval, Claude API generation
- **Frontend**: Next.js 16 at `frontend/` — Chat UI, rate lookup tables, citation cards
- **Database**: PostgreSQL + pgvector (local via Docker Compose, prod on VPS)
- **LLM**: Claude Sonnet (`claude-sonnet-4-6`) via Anthropic SDK
- **Embeddings**: OpenAI `text-embedding-3-small` (1536 dims)

## Key Commands
```bash
# Local dev
docker compose up -d                          # Start PostgreSQL + pgvector
cd backend && pip install -r requirements.txt  # Install backend deps
cd backend && uvicorn app.main:app --reload    # Run backend
cd frontend && npm install && npm run dev      # Run frontend

# Database
cd backend && alembic upgrade head             # Run migrations
cd backend && python scripts/seed_db.py        # Seed rate tables

# Ingestion
cd backend && python scripts/ingest_income_tax.py  # Ingest Income Tax Act
cd backend && python scripts/ingest_gst.py         # Ingest GST Act

# Tests
cd backend && pytest                           # Run backend tests

# Production
docker compose -f docker-compose.prod.yml up -d --build
```

## Code Conventions
- Backend: Python 3.12+, async/await everywhere, Pydantic for validation
- Frontend: TypeScript strict, Next.js App Router, shadcn/ui components
- API: All endpoints versioned under `/api/v1/`
- Streaming: SSE for chat responses, final event contains citations + confidence
- Logging: structlog for structured JSON logs

## Environment Variables
See `backend/.env.example` for required variables:
- `DATABASE_URL` — PostgreSQL connection string
- `ANTHROPIC_API_KEY` — Claude API key
- `OPENAI_API_KEY` — For embeddings only
