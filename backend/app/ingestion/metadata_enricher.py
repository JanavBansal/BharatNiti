"""Enrich chunks with metadata: keywords, amendment references, cross-refs."""

import re

# Common tax law keywords for tagging
KEYWORD_PATTERNS = {
    "deduction": re.compile(r"\b(?:deduction|deductible|deducted)\b", re.IGNORECASE),
    "exemption": re.compile(r"\b(?:exempt|exemption|exempted)\b", re.IGNORECASE),
    "penalty": re.compile(r"\b(?:penalty|penalties|penalised)\b", re.IGNORECASE),
    "interest": re.compile(r"\b(?:interest)\b", re.IGNORECASE),
    "capital_gains": re.compile(r"\b(?:capital gain|capital gains|LTCG|STCG)\b", re.IGNORECASE),
    "tds": re.compile(r"\b(?:TDS|tax deducted at source)\b", re.IGNORECASE),
    "gst": re.compile(r"\b(?:GST|goods and services tax|CGST|SGST|IGST)\b", re.IGNORECASE),
    "assessment": re.compile(r"\b(?:assessment|reassessment|assessing officer)\b", re.IGNORECASE),
    "return": re.compile(r"\b(?:return of income|ITR|filing of return)\b", re.IGNORECASE),
    "appeal": re.compile(r"\b(?:appeal|appellate|ITAT|CIT\(A\))\b", re.IGNORECASE),
    "transfer_pricing": re.compile(r"\b(?:transfer pricing|arm.s length)\b", re.IGNORECASE),
    "residential_status": re.compile(r"\b(?:resident|non-resident|NRI|RNOR)\b", re.IGNORECASE),
}

AMENDMENT_RE = re.compile(
    r"(?:(?:inserted|substituted|omitted|amended)\s+by\s+(?:the\s+)?(?:Finance|Taxation)\s+Act[,\s]+(\d{4}))",
    re.IGNORECASE,
)

CBDT_CIRCULAR_RE = re.compile(
    r"(?:Circular\s+No\.\s*(\d+/\d{4}))|(?:Notification\s+No\.\s*(\d+/\d{4}))",
    re.IGNORECASE,
)


def enrich_metadata(content: str, existing_metadata: dict | None = None) -> dict:
    """Extract keywords, amendment history, and CBDT circular references from chunk content."""
    metadata = existing_metadata.copy() if existing_metadata else {}

    # Extract keywords
    keywords = []
    for keyword, pattern in KEYWORD_PATTERNS.items():
        if pattern.search(content):
            keywords.append(keyword)
    if keywords:
        metadata["keywords"] = keywords

    # Extract amendment history
    amendments = AMENDMENT_RE.findall(content)
    if amendments:
        metadata["amendment_years"] = sorted(set(amendments))

    # Extract CBDT circular references
    circular_matches = CBDT_CIRCULAR_RE.findall(content)
    circulars = [m[0] or m[1] for m in circular_matches if m[0] or m[1]]
    if circulars:
        metadata["cbdt_circulars"] = circulars

    return metadata
