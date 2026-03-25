"""Section-aware chunking for Indian legal documents.

Indian legal documents follow strict hierarchy:
Part > Chapter > Section > Sub-section > Clause > Proviso > Explanation

Chunking rules:
- Primary split: Section boundary
- Secondary split: If section > 1000 tokens, split at sub-section boundaries
- Minimum chunk: 150 tokens (merge small sections with next in same chapter)
- Each sub-chunk inherits section header as prefix for self-containment
- Provisos/Explanations stay attached to their parent
- Cross-references extracted via regex
"""

import re
from dataclasses import dataclass, field

import tiktoken

_encoder = tiktoken.get_encoding("cl100k_base")

MAX_CHUNK_TOKENS = 1000
MIN_CHUNK_TOKENS = 150

# ─── Regex patterns for Indian legislative formatting ───────────────

# Acts: "1. Short title..." or "80C. Deduction..."
SECTION_HEADER_RE = re.compile(
    r"^(\d+[A-Z]{0,3})\.\s+(.+?)(?:\.\s*[-—]|$)", re.MULTILINE
)
# Rules: "Rule 1. ...", "Rule 2A. ..."
RULE_HEADER_RE = re.compile(
    r"^Rule\s+(\d+[A-Z]{0,3})\.\s*[-—]?\s*(.+?)(?:\.\s*[-—]|$)", re.MULTILINE
)
# DTAAs: "Article 1 ...", "ARTICLE 12 — Royalties"
ARTICLE_HEADER_RE = re.compile(
    r"^(?:ARTICLE|Article)\s+(\d+)\s*[-—.]?\s*(.+)", re.MULTILINE
)
# Circulars/Notifications: paragraph numbering "1. ...", "2. ..."
CIRCULAR_PARA_RE = re.compile(
    r"^(\d+)\.\s+(.+?)(?:\.\s*[-—]|$)", re.MULTILINE
)

SUB_SECTION_RE = re.compile(r"^\((\d+[a-z]?)\)\s+", re.MULTILINE)
CHAPTER_RE = re.compile(r"^CHAPTER\s+([IVXLCDM]+[A-Z]*)\s*[-—]?\s*(.+)", re.MULTILINE | re.IGNORECASE)
PART_RE = re.compile(r"^PART\s+([IVXLCDM]+[A-Z]*)\s*[-—]?\s*(.+)", re.MULTILINE | re.IGNORECASE)
PROVISO_RE = re.compile(r"^\s*Provided\s+that", re.MULTILINE | re.IGNORECASE)
EXPLANATION_RE = re.compile(r"^\s*Explanation\s*[\d]*\s*[-—.]", re.MULTILINE | re.IGNORECASE)
CROSS_REF_RE = re.compile(r"[Ss]ection\s+(\d+[A-Z]{0,3})")

# Map doc_type → (header regex, label prefix for chunks)
DOC_TYPE_REGEX = {
    "act": (SECTION_HEADER_RE, "Section"),
    "rules": (RULE_HEADER_RE, "Rule"),
    "dtaa": (ARTICLE_HEADER_RE, "Article"),
    "circular": (CIRCULAR_PARA_RE, "Para"),
    "notification": (CIRCULAR_PARA_RE, "Para"),
    "form": (SECTION_HEADER_RE, "Section"),  # fallback to section-style
}


def _count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


@dataclass
class ParsedSection:
    section_number: str
    section_title: str
    content: str
    chapter: str | None = None
    part: str | None = None
    cross_refs: list[str] = field(default_factory=list)


@dataclass
class ChunkOutput:
    content: str
    section_number: str | None
    section_title: str | None
    chapter: str | None
    part: str | None
    chunk_index: int
    token_count: int
    cross_refs: list[str] = field(default_factory=list)


def extract_cross_refs(text: str) -> list[str]:
    """Extract all section cross-references from text."""
    refs = CROSS_REF_RE.findall(text)
    return sorted(set(refs))


def parse_sections(text: str, doc_type: str = "act") -> list[ParsedSection]:
    """Parse full document text into structured sections with hierarchy.

    Supports different document types (acts, rules, DTAAs, circulars) by
    selecting the appropriate header regex pattern.
    """
    sections = []
    current_chapter = None
    current_part = None

    # Select header regex for this doc_type
    header_re, label = DOC_TYPE_REGEX.get(doc_type, (SECTION_HEADER_RE, "Section"))

    # Find all chapter and part markers
    chapter_positions = [(m.start(), m.group(1), m.group(2).strip()) for m in CHAPTER_RE.finditer(text)]
    part_positions = [(m.start(), m.group(1), m.group(2).strip()) for m in PART_RE.finditer(text)]

    # Find all section/rule/article starts using the appropriate regex
    section_matches = list(header_re.finditer(text))

    # Fallback: if doc_type-specific regex finds nothing, try the default section regex
    if not section_matches and doc_type != "act":
        section_matches = list(SECTION_HEADER_RE.finditer(text))
        label = "Section"

    if not section_matches:
        # No sections found — return entire text as one chunk
        return [ParsedSection(
            section_number="",
            section_title="Full Text",
            content=text.strip(),
            cross_refs=extract_cross_refs(text),
        )]

    for i, match in enumerate(section_matches):
        section_number = match.group(1)
        section_title = match.group(2).strip()
        start = match.start()
        end = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(text)
        content = text[start:end].strip()

        # Determine chapter/part at this position
        for pos, ch_num, ch_title in chapter_positions:
            if pos < start:
                current_chapter = f"Chapter {ch_num} — {ch_title}"
        for pos, pt_num, pt_title in part_positions:
            if pos < start:
                current_part = f"Part {pt_num} — {pt_title}"

        sections.append(ParsedSection(
            section_number=section_number,
            section_title=section_title,
            content=content,
            chapter=current_chapter,
            part=current_part,
            cross_refs=extract_cross_refs(content),
        ))

    return sections


def _split_at_subsections(section: ParsedSection) -> list[ChunkOutput]:
    """Split a large section at sub-section boundaries."""
    text = section.content
    header_prefix = f"Section {section.section_number}. {section.section_title}\n\n"

    # Find sub-section boundaries
    sub_matches = list(SUB_SECTION_RE.finditer(text))
    if not sub_matches:
        # No sub-sections — return as-is (even if large)
        return [ChunkOutput(
            content=text,
            section_number=section.section_number,
            section_title=section.section_title,
            chapter=section.chapter,
            part=section.part,
            chunk_index=0,
            token_count=_count_tokens(text),
            cross_refs=section.cross_refs,
        )]

    chunks = []
    # Text before first sub-section (section preamble)
    preamble = text[:sub_matches[0].start()].strip()

    for i, match in enumerate(sub_matches):
        start = match.start()
        end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(text)
        sub_text = text[start:end].strip()

        # Check if proviso/explanation follows — keep attached
        # (They'll naturally be included since we split at sub-section boundaries)

        # Prepend header prefix for self-containment (only if this isn't the first chunk that already has it)
        if i == 0 and preamble:
            chunk_content = preamble + "\n\n" + sub_text
        elif i > 0:
            chunk_content = header_prefix + sub_text
        else:
            chunk_content = sub_text

        chunks.append(ChunkOutput(
            content=chunk_content,
            section_number=section.section_number,
            section_title=section.section_title,
            chapter=section.chapter,
            part=section.part,
            chunk_index=i,
            token_count=_count_tokens(chunk_content),
            cross_refs=extract_cross_refs(chunk_content),
        ))

    return chunks


def _strip_table_of_contents(text: str) -> str:
    """Remove the 'ARRANGEMENT OF SECTIONS' table of contents from Indian law PDFs.

    The TOC contains section headers with no body text, which pollute the chunker.
    We detect the TOC by looking for the pattern and strip everything until the actual
    sections begin (usually marked by 'CHAPTER I' or 'PRELIMINARY').
    """
    # Find the start of TOC
    toc_start = text.find("ARRANGEMENT OF SECTIONS")
    if toc_start == -1:
        toc_start = text.find("ARRANGEMENT OF CLAUSES")
    if toc_start == -1:
        return text

    # Find where the actual content starts after the TOC
    # Look for "CHAPTER I" or "CHAPTER 1" or "PRELIMINARY" after the TOC
    import re
    content_patterns = [
        re.compile(r"^CHAPTER\s+I\b", re.MULTILINE),
        re.compile(r"^PRELIMINARY", re.MULTILINE),
        re.compile(r"^PART\s+I\b", re.MULTILINE),
    ]

    # Search for content start after toc_start
    content_start = None
    for pattern in content_patterns:
        match = pattern.search(text, toc_start + 100)  # Skip at least 100 chars past TOC header
        if match:
            if content_start is None or match.start() < content_start:
                content_start = match.start()

    if content_start and content_start > toc_start:
        # Keep text before TOC + text after TOC
        return text[:toc_start].rstrip() + "\n\n" + text[content_start:]

    return text


def chunk_document(text: str, doc_type: str = "act") -> list[ChunkOutput]:
    """Main entry point: parse and chunk a legal document.

    Args:
        text: Full document text
        doc_type: One of 'act', 'rules', 'dtaa', 'circular', 'notification', 'form'

    Returns a list of ChunkOutput objects ready for embedding.
    """
    text = _strip_table_of_contents(text)
    sections = parse_sections(text, doc_type=doc_type)
    chunks: list[ChunkOutput] = []
    pending_merge: ChunkOutput | None = None

    for section in sections:
        token_count = _count_tokens(section.content)

        if token_count > MAX_CHUNK_TOKENS:
            # Flush any pending merge first
            if pending_merge:
                chunks.append(pending_merge)
                pending_merge = None
            # Split at sub-section boundaries
            sub_chunks = _split_at_subsections(section)
            chunks.extend(sub_chunks)

        elif token_count < MIN_CHUNK_TOKENS:
            # Too small — merge with pending or start a new pending
            chunk = ChunkOutput(
                content=section.content,
                section_number=section.section_number,
                section_title=section.section_title,
                chapter=section.chapter,
                part=section.part,
                chunk_index=0,
                token_count=token_count,
                cross_refs=section.cross_refs,
            )
            if pending_merge and pending_merge.chapter == section.chapter:
                # Merge with pending
                merged_content = pending_merge.content + "\n\n" + section.content
                pending_merge = ChunkOutput(
                    content=merged_content,
                    section_number=pending_merge.section_number,
                    section_title=pending_merge.section_title,
                    chapter=pending_merge.chapter,
                    part=pending_merge.part,
                    chunk_index=0,
                    token_count=_count_tokens(merged_content),
                    cross_refs=list(set(pending_merge.cross_refs + section.cross_refs)),
                )
                # If merged chunk is now big enough, flush it
                if pending_merge.token_count >= MIN_CHUNK_TOKENS:
                    chunks.append(pending_merge)
                    pending_merge = None
            else:
                # Different chapter or no pending — flush old and start new
                if pending_merge:
                    chunks.append(pending_merge)
                pending_merge = chunk
        else:
            # Normal sized section
            if pending_merge:
                chunks.append(pending_merge)
                pending_merge = None
            chunks.append(ChunkOutput(
                content=section.content,
                section_number=section.section_number,
                section_title=section.section_title,
                chapter=section.chapter,
                part=section.part,
                chunk_index=0,
                token_count=token_count,
                cross_refs=section.cross_refs,
            ))

    # Flush any remaining pending merge
    if pending_merge:
        chunks.append(pending_merge)

    return chunks
