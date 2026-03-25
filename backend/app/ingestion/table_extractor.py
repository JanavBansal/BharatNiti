"""Extract and structure rate tables from PDF pages.

Rate tables (TDS rates, GST rates, Income Tax slabs) are stored in two ways:
1. Structured SQL rows in tax_rates table (for direct SQL lookups)
2. Natural language embeddings in chunks table (for semantic search)
"""

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class ExtractedRate:
    rate_type: str  # tds, gst, income_tax_slab
    category: str
    section_number: str | None
    rate_percent: float
    threshold: float | None
    applicable_to: str | None
    notes: str | None
    rate_without_pan: float | None = None


def _parse_percentage(text: str) -> float | None:
    """Extract a percentage value from text."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1))
    try:
        return float(text.strip().rstrip("%"))
    except ValueError:
        return None


def _parse_amount(text: str) -> float | None:
    """Extract a monetary amount from text."""
    text = text.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None


def extract_tds_rates(table: list[list[str]]) -> list[ExtractedRate]:
    """Parse a TDS rate table. Expected columns: Section, Nature of Payment, Rate, Threshold."""
    rates = []
    if not table or len(table) < 2:
        return rates

    # Skip header row(s)
    header = [cell.lower().strip() for cell in table[0]]

    # Try to identify column positions
    section_col = next((i for i, h in enumerate(header) if "section" in h), None)
    nature_col = next((i for i, h in enumerate(header) if "nature" in h or "payment" in h or "category" in h), None)
    rate_col = next((i for i, h in enumerate(header) if "rate" in h and "without" not in h), None)
    threshold_col = next((i for i, h in enumerate(header) if "threshold" in h or "limit" in h or "exceed" in h), None)
    no_pan_col = next((i for i, h in enumerate(header) if "without" in h and "pan" in h), None)

    for row in table[1:]:
        if len(row) <= max(filter(None, [section_col, nature_col, rate_col]), default=0):
            continue

        section = row[section_col].strip() if section_col is not None and section_col < len(row) else None
        category = row[nature_col].strip() if nature_col is not None and nature_col < len(row) else ""
        rate = _parse_percentage(row[rate_col]) if rate_col is not None and rate_col < len(row) else None
        threshold = _parse_amount(row[threshold_col]) if threshold_col is not None and threshold_col < len(row) else None
        rate_without_pan = _parse_percentage(row[no_pan_col]) if no_pan_col is not None and no_pan_col < len(row) else None

        if rate is not None and category:
            rates.append(ExtractedRate(
                rate_type="tds",
                category=category,
                section_number=section,
                rate_percent=rate,
                threshold=threshold,
                applicable_to=None,
                notes=None,
                rate_without_pan=rate_without_pan,
            ))

    logger.info("table_extractor.tds", count=len(rates))
    return rates


def extract_gst_rates(table: list[list[str]]) -> list[ExtractedRate]:
    """Parse a GST rate table. Expected columns: Category/Description, Rate."""
    rates = []
    if not table or len(table) < 2:
        return rates

    header = [cell.lower().strip() for cell in table[0]]
    cat_col = next((i for i, h in enumerate(header) if "category" in h or "description" in h or "item" in h or "service" in h), 0)
    rate_col = next((i for i, h in enumerate(header) if "rate" in h or "gst" in h), 1)

    for row in table[1:]:
        if len(row) <= max(cat_col, rate_col):
            continue
        category = row[cat_col].strip()
        rate = _parse_percentage(row[rate_col])
        if rate is not None and category:
            rates.append(ExtractedRate(
                rate_type="gst",
                category=category,
                section_number=None,
                rate_percent=rate,
                threshold=None,
                applicable_to=None,
                notes=None,
            ))

    logger.info("table_extractor.gst", count=len(rates))
    return rates


def table_to_natural_language(table: list[list[str]], context: str = "") -> str:
    """Convert a table to natural language text for embedding.

    This allows semantic search to find rate information even when
    the query doesn't match SQL lookup patterns.
    """
    if not table:
        return ""

    header = table[0]
    lines = [context] if context else []

    for row in table[1:]:
        parts = []
        for i, cell in enumerate(row):
            if i < len(header) and cell.strip():
                parts.append(f"{header[i]}: {cell.strip()}")
        if parts:
            lines.append(". ".join(parts) + ".")

    return "\n".join(lines)
