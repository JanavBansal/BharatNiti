"""Seed the database with TDS rates, GST rates, and Income Tax slabs."""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import async_session
from app.db.models import TaxRate


# TDS Rates (AY 2025-26) — common sections
TDS_RATES = [
    {"section": "192", "category": "Salary", "rate": 0, "threshold": None, "notes": "As per applicable slab rates"},
    {"section": "194A", "category": "Interest other than on securities (banks)", "rate": 10, "threshold": 40000, "notes": "Threshold ₹50,000 for senior citizens", "rate_without_pan": 20},
    {"section": "194A", "category": "Interest other than on securities (others)", "rate": 10, "threshold": 5000, "rate_without_pan": 20},
    {"section": "194B", "category": "Winning from lottery/crossword puzzle", "rate": 30, "threshold": 10000, "rate_without_pan": 30},
    {"section": "194C", "category": "Payment to contractor (individual/HUF)", "rate": 1, "threshold": 30000, "notes": "Annual limit ₹1,00,000", "rate_without_pan": 20},
    {"section": "194C", "category": "Payment to contractor (others)", "rate": 2, "threshold": 30000, "notes": "Annual limit ₹1,00,000", "rate_without_pan": 20},
    {"section": "194D", "category": "Insurance commission", "rate": 5, "threshold": 15000, "rate_without_pan": 20},
    {"section": "194H", "category": "Commission or brokerage", "rate": 5, "threshold": 15000, "rate_without_pan": 20},
    {"section": "194I", "category": "Rent on land/building/furniture", "rate": 10, "threshold": 240000, "rate_without_pan": 20},
    {"section": "194I", "category": "Rent on plant/machinery", "rate": 2, "threshold": 240000, "rate_without_pan": 20},
    {"section": "194J", "category": "Professional/technical fees", "rate": 10, "threshold": 30000, "rate_without_pan": 20},
    {"section": "194J", "category": "Fee for technical services (to call centre)", "rate": 2, "threshold": 30000, "rate_without_pan": 20},
    {"section": "194N", "category": "Cash withdrawal exceeding ₹1 crore", "rate": 2, "threshold": 10000000, "rate_without_pan": 20},
    {"section": "194Q", "category": "Purchase of goods", "rate": 0.1, "threshold": 5000000, "rate_without_pan": 5},
    {"section": "194R", "category": "Benefit/perquisite to business", "rate": 10, "threshold": 20000, "rate_without_pan": 20},
    {"section": "194S", "category": "Transfer of virtual digital asset", "rate": 1, "threshold": 10000, "rate_without_pan": 20},
]

# Income Tax Slabs — New Regime (AY 2025-26)
NEW_REGIME_SLABS = [
    {"threshold": 0, "rate": 0, "notes": "Up to ₹3,00,000"},
    {"threshold": 300000, "rate": 5, "notes": "₹3,00,001 to ₹7,00,000"},
    {"threshold": 700000, "rate": 10, "notes": "₹7,00,001 to ₹10,00,000"},
    {"threshold": 1000000, "rate": 15, "notes": "₹10,00,001 to ₹12,00,000"},
    {"threshold": 1200000, "rate": 20, "notes": "₹12,00,001 to ₹15,00,000"},
    {"threshold": 1500000, "rate": 30, "notes": "Above ₹15,00,000"},
]

# Income Tax Slabs — Old Regime (AY 2025-26)
OLD_REGIME_SLABS = [
    {"threshold": 0, "rate": 0, "notes": "Up to ₹2,50,000"},
    {"threshold": 250000, "rate": 5, "notes": "₹2,50,001 to ₹5,00,000"},
    {"threshold": 500000, "rate": 20, "notes": "₹5,00,001 to ₹10,00,000"},
    {"threshold": 1000000, "rate": 30, "notes": "Above ₹10,00,000"},
]

# Common GST Rates
GST_RATES = [
    {"category": "Essential food items (rice, wheat, milk)", "rate": 0},
    {"category": "Packaged food items", "rate": 5},
    {"category": "Butter, cheese, ghee", "rate": 12},
    {"category": "Restaurant services (non-AC)", "rate": 5, "notes": "No ITC available"},
    {"category": "Restaurant services (AC/5-star)", "rate": 18, "notes": "ITC available up to 2024, 5% without ITC from 2024"},
    {"category": "Telecom services", "rate": 18},
    {"category": "IT/software services", "rate": 18},
    {"category": "Legal/accounting services", "rate": 18},
    {"category": "Financial services", "rate": 18},
    {"category": "Construction (affordable housing)", "rate": 1, "notes": "Without ITC"},
    {"category": "Construction (other residential)", "rate": 5, "notes": "Without ITC"},
    {"category": "Automobile (small cars)", "rate": 18},
    {"category": "Automobile (SUV/luxury)", "rate": 28, "notes": "Plus compensation cess"},
    {"category": "Cement", "rate": 28},
    {"category": "Movie tickets (up to ₹100)", "rate": 12},
    {"category": "Movie tickets (above ₹100)", "rate": 18},
    {"category": "Insurance (life)", "rate": 18},
    {"category": "Insurance (health)", "rate": 18},
    {"category": "E-commerce operator commission", "rate": 18},
    {"category": "Gold/precious metals", "rate": 3},
]


async def main():
    async with async_session() as db:
        # Clear existing rates
        from sqlalchemy import delete
        await db.execute(delete(TaxRate))

        # Seed TDS rates
        for r in TDS_RATES:
            db.add(TaxRate(
                id=uuid.uuid4(),
                rate_type="tds",
                category=r["category"],
                section_number=r["section"],
                rate_percent=r["rate"],
                threshold=r.get("threshold"),
                applicable_to=None,
                assessment_year="2025-26",
                pan_available=True,
                rate_without_pan=r.get("rate_without_pan"),
                notes=r.get("notes"),
            ))

        # Seed new regime slabs
        for s in NEW_REGIME_SLABS:
            db.add(TaxRate(
                id=uuid.uuid4(),
                rate_type="income_tax_slab",
                category=s["notes"],
                section_number=None,
                rate_percent=s["rate"],
                threshold=s["threshold"],
                applicable_to="new",
                assessment_year="2025-26",
                notes=s.get("notes"),
            ))

        # Seed old regime slabs
        for s in OLD_REGIME_SLABS:
            db.add(TaxRate(
                id=uuid.uuid4(),
                rate_type="income_tax_slab",
                category=s["notes"],
                section_number=None,
                rate_percent=s["rate"],
                threshold=s["threshold"],
                applicable_to="old",
                assessment_year="2025-26",
                notes=s.get("notes"),
            ))

        # Seed GST rates
        for g in GST_RATES:
            db.add(TaxRate(
                id=uuid.uuid4(),
                rate_type="gst",
                category=g["category"],
                section_number=None,
                rate_percent=g["rate"],
                threshold=None,
                applicable_to=None,
                assessment_year=None,
                notes=g.get("notes"),
            ))

        await db.commit()
        print(f"Seeded: {len(TDS_RATES)} TDS rates, {len(NEW_REGIME_SLABS) + len(OLD_REGIME_SLABS)} income tax slabs, {len(GST_RATES)} GST rates")


if __name__ == "__main__":
    asyncio.run(main())
