from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_lookup import (
    lookup_gst_rate, lookup_income_tax_slab, lookup_tds_rate,
    lookup_tcs_rate, lookup_cii, lookup_deadline,
)
from app.db.database import get_db

router = APIRouter()


@router.get("/rates/tds")
async def get_tds_rate(
    section: str | None = Query(None, description="TDS section number e.g. 194A"),
    pan: bool = Query(True, description="Whether PAN is available"),
    db: AsyncSession = Depends(get_db),
):
    return await lookup_tds_rate(db, section=section, pan_available=pan)


@router.get("/rates/gst")
async def get_gst_rate(
    category: str | None = Query(None, description="GST category e.g. restaurant"),
    db: AsyncSession = Depends(get_db),
):
    return await lookup_gst_rate(db, category=category)


@router.get("/rates/income-tax")
async def get_income_tax_slab(
    income: float = Query(..., description="Annual taxable income"),
    regime: str = Query("new", description="Tax regime: old or new"),
    assessment_year: str = Query("2025-26", description="Assessment year"),
    db: AsyncSession = Depends(get_db),
):
    return await lookup_income_tax_slab(db, income=income, regime=regime, assessment_year=assessment_year)


@router.get("/rates/tcs")
async def get_tcs_rate(
    section: str | None = Query(None, description="TCS section e.g. 206C(1G)"),
    db: AsyncSession = Depends(get_db),
):
    return await lookup_tcs_rate(db, section=section)


@router.get("/rates/cii")
async def get_cii(
    fy: str | None = Query(None, description="Financial year e.g. 2023-24"),
    db: AsyncSession = Depends(get_db),
):
    return await lookup_cii(db, financial_year=fy)


@router.get("/rates/deadlines")
async def get_deadlines(
    form: str | None = Query(None, description="Form type e.g. ITR, GSTR, TDS"),
    db: AsyncSession = Depends(get_db),
):
    return await lookup_deadline(db, form_type=form)
