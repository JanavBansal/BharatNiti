"""Ingest all remaining tax law documents into the database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import async_session
from app.ingestion.pipeline import ingest_document

DOCUMENTS = [
    {
        "file": "igst_act_updated.pdf",
        "title": "The Integrated Goods and Services Tax Act, 2017",
        "doc_type": "act",
        "version": "2024",
        "source_url": "https://cbic-gst.gov.in",
    },
    {
        "file": "finance_act_2024.pdf",
        "title": "The Finance Act, 2024 (No. 8 of 2024)",
        "doc_type": "act",
        "version": "2024",
        "source_url": "https://egazette.gov.in",
    },
    {
        "file": "finance_act_no2_2024.pdf",
        "title": "The Finance (No. 2) Act, 2024 (No. 15 of 2024)",
        "doc_type": "act",
        "version": "2024",
        "source_url": "https://egazette.gov.in",
    },
    {
        "file": "income_tax_rules_1962.pdf",
        "title": "The Income-tax Rules, 1962 (Amendments up to 2023)",
        "doc_type": "act",
        "version": "2023",
        "source_url": "https://thc.nic.in",
    },
    {
        "file": "gst_rate_services.pdf",
        "title": "GST Rate Schedule for Services",
        "doc_type": "rate_chart",
        "version": "2024",
        "source_url": "https://dcmsme.gov.in",
    },
]


async def main():
    data_dir = Path(__file__).parent.parent / "data" / "raw"

    for doc in DOCUMENTS:
        pdf_path = data_dir / doc["file"]
        if not pdf_path.exists():
            print(f"SKIP: {doc['file']} not found")
            continue

        print(f"\n{'='*60}")
        print(f"Ingesting: {doc['title']}")
        print(f"File: {doc['file']} ({pdf_path.stat().st_size / 1024:.0f} KB)")
        print(f"{'='*60}")

        try:
            async with async_session() as db:
                document = await ingest_document(
                    db=db,
                    file_path=pdf_path,
                    title=doc["title"],
                    doc_type=doc["doc_type"],
                    version=doc["version"],
                    source_url=doc["source_url"],
                )
                print(f"OK: {document.title} (ID: {document.id})")
        except Exception as e:
            print(f"ERROR: {doc['title']} — {e}")
            continue

    print("\n\nDone! All documents ingested.")


if __name__ == "__main__":
    asyncio.run(main())
