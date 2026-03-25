"""Seed the database with TCS rates, Cost Inflation Index, AY 2026-27 slabs, and filing deadlines.

This script is idempotent — it checks for existing rows before inserting
and never deletes data added by seed_db.py or previous runs.
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db.database import async_session
from app.db.models import TaxRate


# ---------------------------------------------------------------------------
# 1. TCS Rates (AY 2025-26)
# ---------------------------------------------------------------------------
TCS_RATES = [
    {
        "section": "206C(1)",
        "category": "Scrap",
        "rate": 1,
        "notes": "0.75% for specified persons",
    },
    {
        "section": "206C(1)",
        "category": "Timber obtained under forest lease",
        "rate": 2.5,
    },
    {
        "section": "206C(1)",
        "category": "Tendu leaves",
        "rate": 5,
    },
    {
        "section": "206C(1)",
        "category": "Minerals (coal, lignite, iron ore)",
        "rate": 1,
    },
    {
        "section": "206C(1C)",
        "category": "Lease/licence of parking lot, toll plaza, mining",
        "rate": 2,
    },
    {
        "section": "206C(1F)",
        "category": "Motor vehicle above 10L",
        "rate": 1,
    },
    {
        "section": "206C(1G)",
        "category": "Foreign remittance under LRS",
        "rate": 5,
        "notes": "Above ₹7L; 20% for non-education/medical purposes",
    },
    {
        "section": "206C(1G)",
        "category": "Overseas tour package",
        "rate": 5,
        "notes": "20% above ₹7L",
    },
    {
        "section": "206C(1H)",
        "category": "Sale of goods above 50L",
        "rate": 0.1,
    },
    {
        "section": "206CCA",
        "category": "Higher TCS for non-filers",
        "rate": 5,
    },
]

# ---------------------------------------------------------------------------
# 2. Cost Inflation Index (CII)
# ---------------------------------------------------------------------------
CII_VALUES = [
    ("FY 2001-02", 100),
    ("FY 2002-03", 105),
    ("FY 2003-04", 109),
    ("FY 2004-05", 113),
    ("FY 2005-06", 117),
    ("FY 2006-07", 122),
    ("FY 2007-08", 129),
    ("FY 2008-09", 137),
    ("FY 2009-10", 148),
    ("FY 2010-11", 167),
    ("FY 2011-12", 184),
    ("FY 2012-13", 200),
    ("FY 2013-14", 220),
    ("FY 2014-15", 240),
    ("FY 2015-16", 254),
    ("FY 2016-17", 264),
    ("FY 2017-18", 272),
    ("FY 2018-19", 280),
    ("FY 2019-20", 289),
    ("FY 2020-21", 301),
    ("FY 2021-22", 317),
    ("FY 2022-23", 331),
    ("FY 2023-24", 348),
    ("FY 2024-25", 363),
    ("FY 2025-26", 377),
]

# ---------------------------------------------------------------------------
# 3. Income Tax Slabs — AY 2026-27 (Income Tax Act 2025)
# ---------------------------------------------------------------------------
NEW_REGIME_SLABS_2026 = [
    {"threshold": 0, "rate": 0, "notes": "Up to ₹4,00,000"},
    {"threshold": 400000, "rate": 5, "notes": "₹4,00,001 to ₹8,00,000"},
    {"threshold": 800000, "rate": 10, "notes": "₹8,00,001 to ₹12,00,000"},
    {"threshold": 1200000, "rate": 15, "notes": "₹12,00,001 to ₹16,00,000"},
    {"threshold": 1600000, "rate": 20, "notes": "₹16,00,001 to ₹20,00,000"},
    {"threshold": 2000000, "rate": 25, "notes": "₹20,00,001 to ₹24,00,000"},
    {"threshold": 2400000, "rate": 30, "notes": "Above ₹24,00,000"},
]

OLD_REGIME_SLABS_2026 = [
    {"threshold": 0, "rate": 0, "notes": "Up to ₹2,50,000"},
    {"threshold": 250000, "rate": 5, "notes": "₹2,50,001 to ₹5,00,000"},
    {"threshold": 500000, "rate": 20, "notes": "₹5,00,001 to ₹10,00,000"},
    {"threshold": 1000000, "rate": 30, "notes": "Above ₹10,00,000"},
]

# ---------------------------------------------------------------------------
# 4. Filing Deadlines
# ---------------------------------------------------------------------------
DEADLINES = [
    {
        "category": "ITR (Individual/non-audit)",
        "notes": "Due: July 31 of the assessment year",
    },
    {
        "category": "ITR (Audit required)",
        "notes": "Due: October 31 of the assessment year",
    },
    {
        "category": "ITR (Transfer pricing)",
        "notes": "Due: November 30 of the assessment year",
    },
    {
        "category": "ITR (Belated return)",
        "notes": "Due: December 31 of the assessment year",
    },
    {
        "category": "ITR (Updated return)",
        "notes": "Within 24 months from end of the assessment year",
    },
    {
        "category": "Advance Tax Q1",
        "notes": "Due: June 15 — 15% of estimated tax",
    },
    {
        "category": "Advance Tax Q2",
        "notes": "Due: September 15 — 45% of estimated tax (cumulative)",
    },
    {
        "category": "Advance Tax Q3",
        "notes": "Due: December 15 — 75% of estimated tax (cumulative)",
    },
    {
        "category": "Advance Tax Q4",
        "notes": "Due: March 15 — 100% of estimated tax (cumulative)",
    },
    {
        "category": "GSTR-1 (Monthly)",
        "notes": "Due: 11th of the next month",
    },
    {
        "category": "GSTR-3B (Monthly)",
        "notes": "Due: 20th of the next month",
    },
    {
        "category": "GSTR-9 (Annual)",
        "notes": "Due: December 31 of the following financial year",
    },
    {
        "category": "TDS Return (Quarterly)",
        "notes": "Due dates: July 31, October 31, January 31, May 31",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _exists(db, rate_type: str, category: str, assessment_year: str | None = None) -> bool:
    """Return True if a matching TaxRate row already exists."""
    stmt = select(TaxRate.id).where(
        TaxRate.rate_type == rate_type,
        TaxRate.category == category,
    )
    if assessment_year is not None:
        stmt = stmt.where(TaxRate.assessment_year == assessment_year)
    else:
        stmt = stmt.where(TaxRate.assessment_year.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    inserted = {"tcs": 0, "cii": 0, "slab": 0, "deadline": 0}

    async with async_session() as db:
        # --- TCS Rates ---
        for r in TCS_RATES:
            if await _exists(db, "tcs", r["category"], "2025-26"):
                continue
            db.add(TaxRate(
                id=uuid.uuid4(),
                rate_type="tcs",
                category=r["category"],
                section_number=r["section"],
                rate_percent=r["rate"],
                threshold=None,
                applicable_to=None,
                assessment_year="2025-26",
                notes=r.get("notes"),
            ))
            inserted["tcs"] += 1

        # --- Cost Inflation Index ---
        for fy, cii_value in CII_VALUES:
            if await _exists(db, "cii", fy, None):
                continue
            db.add(TaxRate(
                id=uuid.uuid4(),
                rate_type="cii",
                category=fy,
                section_number=None,
                rate_percent=cii_value,
                threshold=None,
                applicable_to=None,
                assessment_year=None,
                notes="Base year 2001-02",
            ))
            inserted["cii"] += 1

        # --- Income Tax Slabs AY 2026-27 — New Regime ---
        for s in NEW_REGIME_SLABS_2026:
            if await _exists(db, "income_tax_slab", s["notes"], "2026-27"):
                continue
            db.add(TaxRate(
                id=uuid.uuid4(),
                rate_type="income_tax_slab",
                category=s["notes"],
                section_number=None,
                rate_percent=s["rate"],
                threshold=s["threshold"],
                applicable_to="new",
                assessment_year="2026-27",
                notes=s["notes"],
            ))
            inserted["slab"] += 1

        # --- Income Tax Slabs AY 2026-27 — Old Regime ---
        for s in OLD_REGIME_SLABS_2026:
            if await _exists(db, "income_tax_slab", s["notes"], "2026-27"):
                continue
            db.add(TaxRate(
                id=uuid.uuid4(),
                rate_type="income_tax_slab",
                category=s["notes"],
                section_number=None,
                rate_percent=s["rate"],
                threshold=s["threshold"],
                applicable_to="old",
                assessment_year="2026-27",
                notes=s["notes"],
            ))
            inserted["slab"] += 1

        # --- Filing Deadlines ---
        for d in DEADLINES:
            if await _exists(db, "deadline", d["category"], None):
                continue
            db.add(TaxRate(
                id=uuid.uuid4(),
                rate_type="deadline",
                category=d["category"],
                section_number=None,
                rate_percent=0,
                threshold=None,
                applicable_to=None,
                assessment_year=None,
                notes=d["notes"],
            ))
            inserted["deadline"] += 1

        await db.commit()

    print(
        f"Seeded: {inserted['tcs']} TCS rates, "
        f"{inserted['cii']} CII entries, "
        f"{inserted['slab']} income tax slabs (AY 2026-27), "
        f"{inserted['deadline']} filing deadlines"
    )
    total = sum(inserted.values())
    if total == 0:
        print("(all rows already existed — nothing inserted)")
    else:
        print(f"Total new rows: {total}")


if __name__ == "__main__":
    asyncio.run(main())
