"""Full ingestion orchestrator: PDF → parse → chunk → enrich → embed → store."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document
from app.ingestion.embedder import embed_texts
from app.ingestion.metadata_enricher import enrich_metadata
from app.ingestion.pdf_parser import extract_pdf
from app.ingestion.section_chunker import chunk_document
from app.ingestion.table_extractor import extract_tds_rates, extract_gst_rates, table_to_natural_language

logger = structlog.get_logger()


async def ingest_document(
    db: AsyncSession,
    file_path: str | Path,
    title: str,
    doc_type: str = "act",
    version: str | None = None,
    source_url: str | None = None,
    effective_date: datetime | None = None,
) -> Document:
    """Full ingestion pipeline for a single PDF document.

    1. Extract text and tables from PDF
    2. Chunk text into section-aware chunks
    3. Enrich chunks with metadata (keywords, amendments, cross-refs)
    4. Batch embed all chunks
    5. Store document + chunks in database
    """
    log = logger.bind(file=str(file_path), title=title)
    log.info("ingestion.start")

    # 1. Extract PDF
    extraction = extract_pdf(file_path)
    if extraction.warnings:
        for warning in extraction.warnings:
            log.warning("ingestion.pdf_warning", warning=warning)

    # 2. Chunk the document (pass doc_type for correct header parsing)
    chunks = chunk_document(extraction.full_text, doc_type=doc_type)
    log.info("ingestion.chunked", chunk_count=len(chunks))

    # 3. Process tables — convert to natural language chunks too
    table_chunks_text = []
    for page in extraction.pages:
        for table in page.tables:
            nl_text = table_to_natural_language(table, context=f"Rate table from {title}, page {page.page_number}")
            if nl_text.strip():
                table_chunks_text.append(nl_text)

    # 4. Enrich metadata
    for chunk in chunks:
        enriched = enrich_metadata(chunk.content, {"cross_refs": chunk.cross_refs})
        chunk.cross_refs = enriched.pop("cross_refs", chunk.cross_refs)
        chunk._extra_metadata = enriched

    # 5. Embed all chunks (text + table natural language)
    all_texts = [c.content for c in chunks] + table_chunks_text
    log.info("ingestion.embedding", total_texts=len(all_texts))
    embeddings = await embed_texts(all_texts)

    # 6. Store in database
    document = Document(
        id=uuid.uuid4(),
        title=title,
        doc_type=doc_type,
        version=version,
        effective_date=effective_date or datetime.now(timezone.utc),
        is_current=True,
        source_url=source_url,
        metadata_={"total_pages": extraction.total_pages, "warnings": extraction.warnings},
        embedding_model=f"openai/{__import__('app.config', fromlist=['settings']).settings.embedding_model}",
    )
    db.add(document)

    # Store text chunks
    for i, chunk in enumerate(chunks):
        db_chunk = Chunk(
            id=uuid.uuid4(),
            document_id=document.id,
            content=chunk.content,
            section_number=chunk.section_number,
            section_title=chunk.section_title,
            chapter=chunk.chapter,
            part=chunk.part,
            chunk_index=chunk.chunk_index,
            embedding=embeddings[i],
            token_count=chunk.token_count,
            metadata_={
                "cross_refs": chunk.cross_refs,
                **getattr(chunk, "_extra_metadata", {}),
            },
        )
        db.add(db_chunk)

    # Store table chunks (as separate chunks with metadata flag)
    for j, table_text in enumerate(table_chunks_text):
        embedding_idx = len(chunks) + j
        db_chunk = Chunk(
            id=uuid.uuid4(),
            document_id=document.id,
            content=table_text,
            section_number=None,
            section_title="Rate Table",
            chapter=None,
            part=None,
            chunk_index=j,
            embedding=embeddings[embedding_idx],
            token_count=len(table_text.split()),  # Approximate
            metadata_={"is_table": True},
        )
        db.add(db_chunk)

    await db.commit()
    log.info("ingestion.complete", document_id=str(document.id), chunks_stored=len(chunks) + len(table_chunks_text))
    return document
