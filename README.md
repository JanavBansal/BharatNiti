# BharatNiti — Indian Tax Law Assistant

RAG-based Q&A system for Indian tax law. Answers questions about the Income Tax Act, GST, TDS rates, and deductions with citations to specific sections, confidence scoring, and disclaimers.

Built for India's 80M+ GST taxpayers and 7Cr+ ITR filers who ask the same tax questions repeatedly but can't afford a CA on retainer.

## Features

- **Cited answers** — Every response references specific sections from the Income Tax Act, CGST Act, Finance Acts, and CBDT circulars
- **Confidence scoring** — 3-signal scoring (retrieval similarity + source coherence + LLM self-assessment) with HIGH/MEDIUM/LOW badges
- **Tax calculator** — Income tax computation with old vs new regime comparison tables
- **Rate lookups** — Structured SQL-based TDS, GST, and income tax slab queries (no LLM hallucination)
- **Scope detection** — LLM-based classification rejects off-topic questions gracefully
- **11,000+ knowledge chunks** — 28 documents including IT Act 1961, CGST Act 2017, Finance Acts 2024-2026, IT Act 2025, and curated FAQ guides

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy async |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4, shadcn/ui |
| Database | PostgreSQL 16 + pgvector (HNSW index) |
| Embeddings | OpenAI `text-embedding-3-large` (3072 dims) |
| LLM | OpenAI `gpt-4o-mini` (swappable to Claude Sonnet) |
| Deployment | Docker Compose, Caddy reverse proxy, auto-SSL |

## Project Structure

```
BharatNiti/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # pydantic-settings
│   │   ├── api/v1/                  # REST endpoints
│   │   ├── core/                    # RAG pipeline, retriever, generator, confidence
│   │   ├── ingestion/               # PDF parser, section chunker, embedder
│   │   ├── db/                      # SQLAlchemy models, Alembic migrations
│   │   └── schemas/                 # Pydantic request/response models
│   ├── scripts/                     # Ingestion & seeding scripts
│   ├── data/
│   │   ├── raw/                     # Source PDFs (gitignored)
│   │   └── supplements/             # Curated knowledge text files
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/                     # Next.js App Router pages
│       ├── components/              # Chat UI, citation cards, rate tables
│       └── lib/                     # API client, hooks, types
├── docker-compose.yml               # Local dev (PostgreSQL + pgvector)
├── docker-compose.prod.yml          # Production (DB + backend + frontend + Caddy)
└── Caddyfile                        # Reverse proxy + auto-SSL
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 18+
- OpenAI API key

### 1. Clone & configure

```bash
git clone https://github.com/yourusername/BharatNiti.git
cd BharatNiti
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

### 2. Start database

```bash
docker compose up -d
```

### 3. Set up backend

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_db.py
python scripts/seed_db_v2.py
```

### 4. Ingest documents

Place source PDFs in `backend/data/raw/`, then:

```bash
python scripts/ingest_income_tax.py
python scripts/ingest_gst.py
python scripts/ingest_supplements.py
```

### 5. Run backend

```bash
uvicorn app.main:app --reload
```

### 6. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## API Endpoints

```
POST /api/v1/ask                    # RAG Q&A (SSE streaming)
GET  /api/v1/rates/tds              # TDS rate lookup
GET  /api/v1/rates/gst              # GST rate lookup
GET  /api/v1/rates/income-tax       # Income tax slab calculator
GET  /api/v1/health                 # DB status + chunk count
```

## Production Deployment

```bash
# On your VPS
docker compose -f docker-compose.prod.yml up -d --build
```

Caddy auto-provisions Let's Encrypt SSL. Set the `DOMAIN` env var for your domain.

## Environment Variables

See `backend/.env.example`:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `OPENAI_API_KEY` | Yes | For embeddings and LLM |
| `ANTHROPIC_API_KEY` | No | For Claude LLM (if switching from OpenAI) |

## Documents Ingested

- Income Tax Act, 1961 (5,814 chunks)
- Income Tax Act, 2025 — New Code (1,302 chunks)
- Income Tax Bill, 2025 (1,809 chunks)
- CGST Act, 2017 (462 chunks)
- IGST/UTGST Acts (62 chunks)
- Finance Acts 2024, 2025, 2026 (429 chunks)
- Income Tax Rules, 1962 (649 chunks)
- TDS/GST rate charts (552 chunks)
- 9 curated practical guides (133 chunks)

**Total: 11,293 chunks across 28 documents**

## Disclaimer

This is a tax law research tool, not a substitute for professional advice. Always consult a Chartered Accountant for decisions involving your finances. Every response includes a disclaimer.

## License

MIT
