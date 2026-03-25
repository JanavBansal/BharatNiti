from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TaxRate


async def lookup_tds_rate(db: AsyncSession, section: str | None = None, pan_available: bool = True) -> dict:
    """Look up TDS rates from structured SQL table."""
    query = select(TaxRate).where(TaxRate.rate_type == "tds")
    if section:
        query = query.where(TaxRate.section_number == section.upper())

    result = await db.execute(query.order_by(TaxRate.section_number))
    rates = result.scalars().all()

    return {
        "rate_type": "tds",
        "results": [
            {
                "section": r.section_number,
                "category": r.category,
                "rate": r.rate_percent if pan_available else (r.rate_without_pan or r.rate_percent * 2),
                "threshold": r.threshold,
                "applicable_to": r.applicable_to,
                "pan_available": pan_available,
                "notes": r.notes,
            }
            for r in rates
        ],
    }


async def lookup_gst_rate(db: AsyncSession, category: str | None = None) -> dict:
    """Look up GST rates from structured SQL table."""
    query = select(TaxRate).where(TaxRate.rate_type == "gst")
    if category:
        query = query.where(TaxRate.category.ilike(f"%{category}%"))

    result = await db.execute(query.order_by(TaxRate.category))
    rates = result.scalars().all()

    return {
        "rate_type": "gst",
        "results": [
            {
                "category": r.category,
                "rate": r.rate_percent,
                "notes": r.notes,
            }
            for r in rates
        ],
    }


async def lookup_income_tax_slab(
    db: AsyncSession,
    income: float,
    regime: str = "new",
    assessment_year: str = "2025-26",
) -> dict:
    """Calculate income tax based on slab rates from SQL table."""
    query = (
        select(TaxRate)
        .where(
            TaxRate.rate_type == "income_tax_slab",
            TaxRate.assessment_year == assessment_year,
            TaxRate.applicable_to == regime,
        )
        .order_by(TaxRate.threshold)
    )

    result = await db.execute(query)
    slabs = result.scalars().all()

    if not slabs:
        return {"error": f"No slabs found for {regime} regime, AY {assessment_year}"}

    total_tax = 0.0
    slab_details = []
    remaining = income

    for i, slab in enumerate(slabs):
        lower = slab.threshold or 0
        upper = slabs[i + 1].threshold if i + 1 < len(slabs) else float("inf")
        taxable_in_slab = min(remaining, upper - lower)
        if taxable_in_slab <= 0:
            break
        tax_in_slab = taxable_in_slab * slab.rate_percent / 100
        total_tax += tax_in_slab
        remaining -= taxable_in_slab
        slab_details.append({
            "range": f"{lower:,.0f} - {upper:,.0f}" if upper != float("inf") else f"{lower:,.0f}+",
            "rate": slab.rate_percent,
            "taxable_amount": taxable_in_slab,
            "tax": tax_in_slab,
        })

    # Section 87A rebate
    rebate = 0.0
    if regime == "new":
        if assessment_year == "2026-27" and income <= 1200000:
            rebate = min(total_tax, 60000)  # New IT Act 2025: rebate up to 60K for income ≤12L
        elif income <= 700000:
            rebate = min(total_tax, 25000)  # AY 2025-26: rebate up to 25K for income ≤7L
        total_tax -= rebate

    cess = total_tax * 0.04  # 4% Health & Education Cess

    return {
        "income": income,
        "regime": regime,
        "assessment_year": assessment_year,
        "slabs": slab_details,
        "total_tax": round(total_tax, 2),
        "rebate_87a": round(rebate, 2),
        "cess": round(cess, 2),
        "total_liability": round(total_tax + cess, 2),
        "effective_rate": round((total_tax + cess) / income * 100, 2) if income > 0 else 0,
    }


async def lookup_tcs_rate(db: AsyncSession, section: str | None = None) -> dict:
    """Look up TCS (Tax Collected at Source) rates."""
    query = select(TaxRate).where(TaxRate.rate_type == "tcs")
    if section:
        query = query.where(TaxRate.section_number.ilike(f"%{section}%"))

    result = await db.execute(query.order_by(TaxRate.section_number))
    rates = result.scalars().all()

    return {
        "rate_type": "tcs",
        "results": [
            {
                "section": r.section_number,
                "category": r.category,
                "rate": r.rate_percent,
                "threshold": r.threshold,
                "notes": r.notes,
            }
            for r in rates
        ],
    }


async def lookup_cii(db: AsyncSession, financial_year: str | None = None) -> dict:
    """Look up Cost Inflation Index values for capital gains indexation."""
    query = select(TaxRate).where(TaxRate.rate_type == "cii")
    if financial_year:
        query = query.where(TaxRate.category.ilike(f"%{financial_year}%"))

    result = await db.execute(query.order_by(TaxRate.category))
    values = result.scalars().all()

    return {
        "rate_type": "cii",
        "results": [
            {
                "financial_year": v.category,
                "cii_value": int(v.rate_percent),
                "notes": v.notes,
            }
            for v in values
        ],
    }


async def lookup_deadline(db: AsyncSession, form_type: str | None = None) -> dict:
    """Look up tax filing deadlines."""
    query = select(TaxRate).where(TaxRate.rate_type == "deadline")
    if form_type:
        query = query.where(TaxRate.category.ilike(f"%{form_type}%"))

    result = await db.execute(query.order_by(TaxRate.category))
    deadlines = result.scalars().all()

    return {
        "rate_type": "deadline",
        "results": [
            {
                "form": d.category,
                "section": d.section_number,
                "deadline": d.notes,
            }
            for d in deadlines
        ],
    }
