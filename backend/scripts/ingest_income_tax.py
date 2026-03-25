"""Ingest the Income Tax Act PDF into the database."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.ingestion.pipeline import ingest_document


async def main():
    pdf_path = Path(__file__).parent.parent / "data" / "raw" / "income_tax_act.pdf"

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        print("Download the Income Tax Act from indiacode.nic.in and place it at:")
        print(f"  {pdf_path}")
        sys.exit(1)

    async with async_session() as db:
        document = await ingest_document(
            db=db,
            file_path=pdf_path,
            title="The Income-tax Act, 1961",
            doc_type="act",
            version="2024",
            source_url="https://indiacode.nic.in",
        )
        print(f"Ingested: {document.title} (ID: {document.id})")


if __name__ == "__main__":
    asyncio.run(main())
