"""Ingest supplement text files into the RAG system.

These are curated, practical-language knowledge files that fill gaps
in the raw statutory PDFs (HRA calculations, capital gains guide, etc).

Chunks on ## headers for clean topic-based splitting.
"""

import asyncio
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog
import tiktoken
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import async_session
from app.db.models import Chunk, Document
from app.ingestion.embedder import embed_texts
from app.ingestion.metadata_enricher import enrich_metadata
from app.ingestion.section_chunker import extract_cross_refs

logger = structlog.get_logger()
_encoder = tiktoken.get_encoding("cl100k_base")

SUPPLEMENTS_DIR = Path(__file__).resolve().parent.parent / "data" / "supplements"

# Metadata for each supplement file
SUPPLEMENT_DOCS = {
    "hra_exemption.txt": {
        "title": "HRA Exemption Guide — Section 10(13A)",
        "doc_type": "guide",
    },
    "capital_gains_comprehensive.txt": {
        "title": "Capital Gains Taxation Guide — Sections 111A, 112, 112A, 54, 54EC, 54F",
        "doc_type": "guide",
    },
    "deductions_80c_to_80u.txt": {
        "title": "Income Tax Deductions Guide — Sections 80C to 80U (Chapter VI-A)",
        "doc_type": "guide",
    },
    "gst_practical_guide.txt": {
        "title": "GST Practical Guide — Registration, ITC, RCM, Exports, Composition",
        "doc_type": "guide",
    },
    "tds_comprehensive.txt": {
        "title": "TDS Comprehensive Guide — Sections 192 to 194Q",
        "doc_type": "guide",
    },
    "itr_filing_guide.txt": {
        "title": "ITR Filing Guide — Forms, Deadlines, Penalties, Advance Tax",
        "doc_type": "guide",
    },
    "new_vs_old_regime.txt": {
        "title": "Old vs New Tax Regime Comparison — AY 2025-26 and AY 2026-27",
        "doc_type": "guide",
    },
    "budget_2024_2025_changes.txt": {
        "title": "Budget 2024 & 2025 Key Tax Changes",
        "doc_type": "circular",
    },
    "common_tax_faqs.txt": {
        "title": "Common Indian Tax FAQs — 50 Frequently Asked Questions",
        "doc_type": "guide",
    },
}


def chunk_text_file(text: str, max_tokens: int = 800, min_tokens: int = 100) -> list[dict]:
    """Split text on ## headers into chunks.

    Each ## header becomes a new chunk. Chunks too small merge with previous.
    Chunks too large split on ### sub-headers or paragraph breaks.
    """
    # Split on ## headers (keep the header with its content)
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract section info from header
        header_match = re.match(r"^##\s+(.+?)(?:\n|$)", section)
        if header_match:
            raw_title = header_match.group(1).strip()
            # Try to extract section number
            sec_num_match = re.search(r"Section\s+(\d+[A-Z]*(?:\(\d+[A-Z]?\))?)", raw_title)
            section_number = sec_num_match.group(1) if sec_num_match else None
            section_title = raw_title
        else:
            section_number = None
            section_title = "Introduction"

        tokens = len(_encoder.encode(section))

        if tokens <= max_tokens:
            chunks.append({
                "content": section,
                "section_number": section_number,
                "section_title": section_title,
                "token_count": tokens,
                "cross_refs": extract_cross_refs(section),
            })
        else:
            # Split on ### sub-headers or double newlines
            sub_parts = re.split(r"(?=^### |\n\n(?=[A-Z]))", section, flags=re.MULTILINE)
            buffer = ""
            for part in sub_parts:
                part = part.strip()
                if not part:
                    continue
                test = (buffer + "\n\n" + part).strip() if buffer else part
                test_tokens = len(_encoder.encode(test))
                if test_tokens <= max_tokens:
                    buffer = test
                else:
                    if buffer:
                        chunks.append({
                            "content": buffer,
                            "section_number": section_number,
                            "section_title": section_title,
                            "token_count": len(_encoder.encode(buffer)),
                            "cross_refs": extract_cross_refs(buffer),
                        })
                    buffer = part
            if buffer:
                chunks.append({
                    "content": buffer,
                    "section_number": section_number,
                    "section_title": section_title,
                    "token_count": len(_encoder.encode(buffer)),
                    "cross_refs": extract_cross_refs(buffer),
                })

    # Merge tiny chunks
    merged = []
    for chunk in chunks:
        if merged and chunk["token_count"] < min_tokens:
            prev = merged[-1]
            new_content = prev["content"] + "\n\n" + chunk["content"]
            prev["content"] = new_content
            prev["token_count"] = len(_encoder.encode(new_content))
            prev["cross_refs"] = list(set(prev["cross_refs"] + chunk["cross_refs"]))
        else:
            merged.append(chunk)

    return merged


async def ingest_supplement(db: AsyncSession, filename: str, meta: dict) -> int:
    """Ingest a single supplement text file."""
    filepath = SUPPLEMENTS_DIR / filename
    if not filepath.exists():
        logger.warning("supplement.missing", file=filename)
        return 0

    text = filepath.read_text(encoding="utf-8")

    # Check if already ingested
    result = await db.execute(
        sa_text("SELECT id FROM documents WHERE title = :t"),
        {"t": meta["title"]},
    )
    existing = result.scalar()
    if existing:
        # Delete old chunks and document for re-ingestion
        await db.execute(sa_text("DELETE FROM chunks WHERE document_id = :did"), {"did": existing})
        await db.execute(sa_text("DELETE FROM documents WHERE id = :did"), {"did": existing})
        await db.flush()
        logger.info("supplement.replaced", title=meta["title"])

    # Chunk the text
    chunks = chunk_text_file(text)
    logger.info("supplement.chunked", file=filename, chunks=len(chunks))

    if not chunks:
        return 0

    # Embed
    all_texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(all_texts)

    # Create document record
    doc = Document(
        id=uuid.uuid4(),
        title=meta["title"],
        doc_type=meta["doc_type"],
        version="2025-26",
        effective_date=datetime(2025, 4, 1, tzinfo=timezone.utc),
        is_current=True,
        source_url=None,
        metadata_={"source": "supplement", "filename": filename},
        embedding_model=f"openai/{settings.embedding_model}",
    )
    db.add(doc)

    # Create chunks
    for i, chunk in enumerate(chunks):
        enriched = enrich_metadata(chunk["content"], {"cross_refs": chunk["cross_refs"]})
        cross_refs = enriched.pop("cross_refs", chunk["cross_refs"])

        db_chunk = Chunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            content=chunk["content"],
            section_number=chunk["section_number"],
            section_title=chunk["section_title"],
            chapter=None,
            part=None,
            chunk_index=i,
            embedding=embeddings[i],
            token_count=chunk["token_count"],
            metadata_={
                "cross_refs": cross_refs,
                "source": "supplement",
                **enriched,
            },
        )
        db.add(db_chunk)

    await db.commit()
    logger.info("supplement.ingested", title=meta["title"], chunks=len(chunks))
    return len(chunks)


async def main():
    total = 0
    async with async_session() as db:
        for filename, meta in SUPPLEMENT_DOCS.items():
            try:
                count = await ingest_supplement(db, filename, meta)
                total += count
                print(f"  ✅ {count:3d} chunks | {meta['title']}")
            except Exception as e:
                print(f"  ❌ FAILED  | {meta['title']}: {e}")

    print(f"\n  TOTAL: {total} supplement chunks ingested")


if __name__ == "__main__":
    print("═══ Ingesting Supplement Knowledge Files ═══\n")
    asyncio.run(main())
