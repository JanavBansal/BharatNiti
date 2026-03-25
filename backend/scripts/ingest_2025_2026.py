"""Ingest all 2025-2026 tax law documents into the database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import async_session
from app.ingestion.pipeline import ingest_document

DOCUMENTS = [
    # Already ingested via earlier scripts: income_tax_act.pdf, cgst_act.pdf, igst_act_updated.pdf,
    # finance_act_2024.pdf, finance_act_no2_2024.pdf, income_tax_rules_1962.pdf, gst_rate_services.pdf

    # 2025 documents
    {"file": "finance_act_2025.pdf", "title": "The Finance Act, 2025 (No. 7 of 2025)", "doc_type": "act", "version": "2025"},
    {"file": "income_tax_act_2025.pdf", "title": "The Income Tax Act, 2025 (New Code, effective 1 April 2026)", "doc_type": "act", "version": "2025"},
    {"file": "income_tax_bill_2025.pdf", "title": "The Income-tax Bill, 2025 (As Introduced in Lok Sabha)", "doc_type": "act", "version": "2025"},
    {"file": "taxation_laws_amendment_2025.pdf", "title": "Taxation Laws (Amendment) Act, 2025 (No. 29 of 2025)", "doc_type": "act", "version": "2025"},
    {"file": "taxation_laws_bill_2025.pdf", "title": "The Taxation Laws (Amendment) Bill, 2025", "doc_type": "act", "version": "2025"},
    {"file": "pib_reshaping_tax.pdf", "title": "Income Tax Act 2025 — Reshaping Tax Framework (PIB Summary)", "doc_type": "circular", "version": "2025"},

    # 2026 documents
    {"file": "finance_bill_2026.pdf", "title": "The Finance Bill, 2026 (Union Budget 2026-27)", "doc_type": "act", "version": "2026"},
    {"file": "budget_2026_highlights.pdf", "title": "Key Features of Union Budget 2026-27", "doc_type": "circular", "version": "2026"},

    # GST — goods rates + remaining acts
    {"file": "gst_goods_rates_reckoner.pdf", "title": "CBIC GST Ready Reckoner — CGST Rates on Goods (Sep 2025)", "doc_type": "rate_chart", "version": "2025"},
    {"file": "utgst_act_2017.pdf", "title": "The Union Territory Goods and Services Tax Act, 2017", "doc_type": "act", "version": "2017"},
    {"file": "gst_cess_flyer.pdf", "title": "GST Compensation Cess — Overview", "doc_type": "circular", "version": "2019"},

    # TDS/TCS rate charts
    {"file": "tds_rate_chart_2025_26.pdf", "title": "TDS Rate Chart FY 2025-26 (AY 2026-27)", "doc_type": "rate_chart", "version": "2025"},
    {"file": "tds_tcs_chart_2025_26.pdf", "title": "TDS & TCS Rate Chart FY 2025-26 (AY 2026-27) — Post Budget", "doc_type": "rate_chart", "version": "2025"},
]


async def main():
    data_dir = Path(__file__).parent.parent / "data" / "raw"
    success = 0
    failed = 0

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
                    version=doc.get("version"),
                )
                print(f"OK: {document.title} (ID: {document.id})")
                success += 1
        except Exception as e:
            print(f"ERROR: {doc['title']} — {e}")
            failed += 1

    print(f"\n\nDone! {success} succeeded, {failed} failed.")


if __name__ == "__main__":
    asyncio.run(main())
