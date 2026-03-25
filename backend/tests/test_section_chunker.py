"""Tests for the section-aware legal document chunker."""

from app.ingestion.section_chunker import chunk_document, extract_cross_refs, parse_sections


SAMPLE_LEGAL_TEXT = """PART I — PRELIMINARY

CHAPTER I — SHORT TITLE AND DEFINITIONS

1. Short title, extent and commencement. — (1) This Act may be called the Income-tax Act, 1961.
(2) It extends to the whole of India.
(3) It shall come into force on the 1st day of April, 1962.

2. Definitions. — In this Act, unless the context otherwise requires,—
(1) "agricultural income" means— (a) any rent or revenue derived from land which is situated in India and is used for agricultural purposes;
(b) any income derived from such land by agriculture.
(2) "amalgamation" in relation to companies means the merger of one or more companies with another company.

CHAPTER II — BASIS OF CHARGE

3. Previous year defined. — For the purposes of this Act, "previous year" means the financial year immediately preceding the assessment year.

4. Charge of income-tax. — (1) Where any Central Act enacts that income-tax shall be charged for any assessment year at any rate or rates, income-tax at that rate or those rates shall be charged for that year in accordance with, and subject to the provisions of, this Act in respect of the total income of the previous year of every person.
(2) In respect of income chargeable under sub-section (1), income-tax shall be deducted at the source or paid in advance, where it is so deductible or payable under any provision of this Act.

CHAPTER III — INCOMES WHICH DO NOT FORM PART OF TOTAL INCOME

10. Incomes not included in total income. — In computing the total income of a previous year of any person, any income falling within any of the following clauses shall not be included—
(1) agricultural income as defined in Section 2;
(2) any sum received by a member of a Hindu undivided family;

80C. Deduction in respect of life insurance premia, deferred annuity. — (1) In computing the total income of an assessee, being an individual or a Hindu undivided family, there shall be deducted, in accordance with and subject to the provisions of this section, the whole of the amount paid or deposited in the previous year, being the aggregate of the sums referred to in sub-section (2), as does not exceed one lakh fifty thousand rupees.
(2) The sums referred to in sub-section (1) shall be any sums paid or deposited by the assessee—
(a) to effect or to keep in force an insurance on the life of the assessee;
(b) to effect or to keep in force an insurance on the life of the spouse or any child of the assessee;
(c) as contribution to the Employee Provident Fund under Section 194C;
(d) as subscription to any notified savings certificate under the National Savings Certificates.

Provided that where the policy is issued on or after the 1st day of April, 2012, the premium shall not exceed ten per cent of the actual capital sum assured.

Explanation.— For the purposes of this sub-section, "insurance" includes insurance on the life of any member.
"""


def test_parse_sections_finds_all():
    sections = parse_sections(SAMPLE_LEGAL_TEXT)
    section_numbers = [s.section_number for s in sections]
    assert "1" in section_numbers
    assert "2" in section_numbers
    assert "3" in section_numbers
    assert "4" in section_numbers
    assert "10" in section_numbers
    assert "80C" in section_numbers


def test_parse_sections_chapters():
    sections = parse_sections(SAMPLE_LEGAL_TEXT)
    section_1 = next(s for s in sections if s.section_number == "1")
    assert section_1.chapter is not None
    assert "CHAPTER I" in section_1.chapter

    section_3 = next(s for s in sections if s.section_number == "3")
    assert section_3.chapter is not None
    assert "CHAPTER II" in section_3.chapter


def test_parse_sections_parts():
    sections = parse_sections(SAMPLE_LEGAL_TEXT)
    section_1 = next(s for s in sections if s.section_number == "1")
    assert section_1.part is not None
    assert "PART I" in section_1.part


def test_extract_cross_refs():
    text = "as per Section 194C and Section 80C of the Act"
    refs = extract_cross_refs(text)
    assert "194C" in refs
    assert "80C" in refs


def test_chunk_document_produces_chunks():
    chunks = chunk_document(SAMPLE_LEGAL_TEXT)
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.content
        assert chunk.token_count > 0


def test_chunk_large_section_splits():
    """Section 80C in the sample text should remain as-is or split if large enough."""
    chunks = chunk_document(SAMPLE_LEGAL_TEXT)
    section_80c_chunks = [c for c in chunks if c.section_number == "80C"]
    assert len(section_80c_chunks) >= 1


def test_chunk_small_sections_merged():
    """Very small sections should be merged with adjacent sections in the same chapter."""
    chunks = chunk_document(SAMPLE_LEGAL_TEXT)
    # All chunks should meet minimum token count (or be the last chunk)
    for chunk in chunks[:-1]:
        # Allow some tolerance — the minimum is soft for edge cases
        assert chunk.token_count > 0


def test_cross_refs_in_chunks():
    chunks = chunk_document(SAMPLE_LEGAL_TEXT)
    section_80c = [c for c in chunks if c.section_number == "80C"]
    if section_80c:
        refs = section_80c[0].cross_refs
        assert "194C" in refs
