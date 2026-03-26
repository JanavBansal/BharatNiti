"""Document text extraction using pdfplumber (PDF) or plain read (TXT) with validation.

Handles:
- Text-based PDFs from indiacode.nic.in
- Plain text (.txt) files for locally-prepared legal content
- Table detection and extraction (PDFs only)
- Extraction quality validation (detect scanned/corrupt PDFs)
"""

import structlog
import pdfplumber
from dataclasses import dataclass
from pathlib import Path

logger = structlog.get_logger()

MIN_CHARS_PER_PAGE = 100  # Below this, flag as likely scanned/corrupt
TXT_PAGE_CHARS = 3000  # Approximate chars per "page" when splitting TXT files


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    tables: list[list[list[str]]]  # Each table is a list of rows, each row a list of cells


@dataclass
class PDFExtractionResult:
    file_path: str
    pages: list[ExtractedPage]
    full_text: str
    total_pages: int
    warnings: list[str]


def _extract_txt(file_path: Path) -> PDFExtractionResult:
    """Extract text from a plain .txt file.

    Splits the text into synthetic "pages" of ~TXT_PAGE_CHARS characters
    (breaking at the nearest newline) so downstream chunking works consistently.
    """
    logger.info("txt_parser.start", file=str(file_path))

    raw_text = file_path.read_text(encoding="utf-8")
    warnings: list[str] = []

    if not raw_text.strip():
        warnings.append("TXT file is empty")

    # Split into synthetic pages at paragraph boundaries
    pages: list[ExtractedPage] = []
    start = 0
    page_num = 0
    while start < len(raw_text):
        end = start + TXT_PAGE_CHARS
        if end < len(raw_text):
            # Find the nearest newline after the target to avoid mid-sentence splits
            newline_pos = raw_text.find("\n", end)
            if newline_pos != -1 and newline_pos - end < 500:
                end = newline_pos + 1
        else:
            end = len(raw_text)
        page_num += 1
        page_text = raw_text[start:end]
        pages.append(ExtractedPage(page_number=page_num, text=page_text, tables=[]))
        start = end

    total_pages = len(pages) or 1

    logger.info("txt_parser.complete", file=str(file_path), pages=total_pages, total_chars=len(raw_text))

    return PDFExtractionResult(
        file_path=str(file_path),
        pages=pages,
        full_text=raw_text,
        total_pages=total_pages,
        warnings=warnings,
    )


def extract_pdf(file_path: str | Path) -> PDFExtractionResult:
    """Extract text and tables from a PDF or TXT file.

    If the file has a .txt extension, reads it as plain text.
    Otherwise, uses pdfplumber for PDF extraction.

    Returns structured extraction result with per-page text, tables, and quality warnings.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Plain text files — read directly, skip pdfplumber
    if file_path.suffix.lower() == ".txt":
        return _extract_txt(file_path)

    # PDF extraction via pdfplumber — batch processing for large files
    import gc
    pages: list[ExtractedPage] = []
    warnings: list[str] = []
    all_text_parts: list[str] = []

    # First pass: get page count
    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
    logger.info("pdf_parser.start", file=str(file_path), pages=total_pages)

    # Process in batches of BATCH_SIZE pages to limit memory
    BATCH_SIZE = 100
    for batch_start in range(0, total_pages, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_pages)
        logger.info("pdf_parser.batch", start=batch_start + 1, end=batch_end, total=total_pages)

        with pdfplumber.open(file_path, pages=list(range(batch_start, batch_end))) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = batch_start + i + 1

                text = page.extract_text() or ""

                if len(text.strip()) < MIN_CHARS_PER_PAGE:
                    warnings.append(f"Page {page_num}: Low text extraction ({len(text.strip())} chars) — may be scanned/image")

                tables = []
                try:
                    raw_tables = page.extract_tables() or []
                    for table in raw_tables:
                        cleaned = [[cell or "" for cell in row] for row in table if row]
                        if cleaned:
                            tables.append(cleaned)
                except Exception as e:
                    warnings.append(f"Page {page_num}: Table extraction failed — {e}")

                pages.append(ExtractedPage(page_number=page_num, text=text, tables=tables))
                all_text_parts.append(text)

        # Free memory between batches
        gc.collect()

    full_text = "\n\n".join(all_text_parts)

    # Overall quality check
    low_quality_pages = sum(1 for p in pages if len(p.text.strip()) < MIN_CHARS_PER_PAGE)
    if low_quality_pages > total_pages * 0.5:
        warnings.append(f"WARNING: {low_quality_pages}/{total_pages} pages have low text extraction. This PDF may be scanned.")

    logger.info("pdf_parser.complete", file=str(file_path), pages=total_pages, warnings=len(warnings), total_chars=len(full_text))

    return PDFExtractionResult(
        file_path=str(file_path),
        pages=pages,
        full_text=full_text,
        total_pages=total_pages,
        warnings=warnings,
    )
