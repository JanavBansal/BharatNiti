"""Hybrid retriever: semantic (pgvector) + keyword (PostgreSQL full-text search) + query rewriting."""

import re

import structlog
import tiktoken
from openai import AsyncOpenAI
from sqlalchemy import select, text, bindparam, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Chunk

logger = structlog.get_logger()
_openai_client: AsyncOpenAI | None = None
_encoder = tiktoken.get_encoding("cl100k_base")

# Regex to extract section numbers from questions
SECTION_RE = re.compile(r"[Ss]ection\s+(\d+[A-Z]{0,3}(?:\(\d+[A-Za-z]?\))?)")


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def _embed_query(query: str) -> list[float]:
    client = _get_openai_client()
    response = await client.embeddings.create(input=query, model=settings.embedding_model)
    return response.data[0].embedding


def _count_tokens(text_str: str) -> int:
    return len(_encoder.encode(text_str))


def _extract_section_refs(question: str) -> list[str]:
    """Extract section numbers mentioned in the question for keyword search."""
    matches = SECTION_RE.findall(question)
    # Also look for bare patterns like "80C", "194J", "234A"
    bare = re.findall(r"\b(\d{1,3}[A-Z]{0,3})\b", question)
    # Filter bare matches to likely section numbers
    likely_sections = [b for b in bare if re.match(r"^\d{1,3}[A-Z]{0,3}$", b) and len(b) >= 2]
    all_refs = list(set(matches + likely_sections))
    return all_refs


def _rewrite_query(question: str) -> str:
    """Expand the query with synonyms and related terms for better retrieval."""
    expansions = {
        "hra": "house rent allowance HRA Section 10(13A)",
        "lta": "leave travel allowance LTA Section 10(5)",
        "tds": "tax deducted at source TDS",
        "tcs": "tax collected at source TCS",
        "ltcg": "long term capital gains LTCG",
        "stcg": "short term capital gains STCG",
        "nps": "National Pension System NPS Section 80CCD",
        "elss": "Equity Linked Savings Scheme ELSS Section 80C",
        "itr": "income tax return ITR",
        "gst rate": "GST rate CGST SGST percentage",
        "slab": "slab rate tax bracket income range",
        "indexation": "indexation cost inflation index CII Section 48",
        "advance tax": "advance tax Section 208 209 210 211",
        "penalty": "penalty Section 270A 271 271F 234F",
        "residential status": "residential status resident non-resident NRI Section 6",
        "assessment": "assessment reassessment Section 143 144 147 148",
        "budget 2026": "Union Budget 2026-27 Finance Bill 2026 key highlights",
        "new income tax act": "Income Tax Act 2025 new code simplification",
        "input tax credit": "input tax credit ITC Section 16 17 18 CGST",
        "reverse charge": "reverse charge mechanism RCM Section 9(3) 9(4) CGST recipient liability",
        "composition scheme": "composition scheme Section 10 CGST turnover limit",
        "standard deduction": "standard deduction salary Section 16 Section 19 deduction from salary 50000 75000",
        "form 26as": "Form 26AS annual tax statement TDS TCS Section 203AA",
        "234f": "penalty late filing return Section 234F 5000 1000",
        "late filing": "penalty late filing return Section 234F belated return",
        "due date": "due date filing return Section 139 July 31 September 30 October 31",
        # New doc type expansions
        "dtaa": "double taxation avoidance agreement treaty Article resident",
        "double taxation": "DTAA treaty avoidance agreement permanent establishment Article",
        "transfer pricing": "transfer pricing arm's length Section 92 92A 92B 92C Rule 10A 10B",
        "benami": "benami property transaction prohibition Act 1988 2016 beneficial owner",
        "black money": "undisclosed foreign income assets Black Money Act 2015",
        "vivad se vishwas": "Direct Tax Vivad Se Vishwas dispute resolution scheme 2024",
        "equalisation levy": "equalisation levy digital economy Chapter VIII Finance Act 2016 non-resident",
        "tax audit": "tax audit Form 3CA 3CB 3CD Section 44AB turnover",
        "gstr": "GSTR return filing GST GSTR-1 GSTR-3B GSTR-9 annual return",
        "tcs": "tax collected at source TCS Section 206C buyer seller",
        "cii": "cost inflation index CII indexation capital gains Section 48",
        "cost inflation": "cost inflation index CII indexation Section 48 long term capital",
        "e-invoice": "e-invoice electronic invoicing GST Rule 48(4) IRP",
        "e-way bill": "e-way bill EWB movement goods Rule 138 CGST",
    }
    q_lower = question.lower()
    extra_terms = []
    for trigger, expansion in expansions.items():
        if trigger in q_lower:
            extra_terms.append(expansion)

    if extra_terms:
        return question + " " + " ".join(extra_terms)
    return question


async def _semantic_search(db: AsyncSession, query: str, top_k: int) -> list[dict]:
    """Pgvector cosine similarity search."""
    expanded_query = _rewrite_query(query)
    query_embedding = await _embed_query(expanded_query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    sql = text(
        "SELECT c.id, c.content, c.section_number, c.section_title, "
        "c.chapter, c.part, c.token_count, c.metadata, "
        "d.title as document_title, "
        "1 - (c.embedding <=> cast(:emb as vector)) as similarity "
        "FROM chunks c "
        "JOIN documents d ON c.document_id = d.id "
        "WHERE d.is_current = true "
        "ORDER BY c.embedding <=> cast(:emb as vector) "
        "LIMIT :topk"
    ).bindparams(bindparam("emb", value=embedding_str, type_=String), bindparam("topk", value=top_k, type_=Integer))

    result = await db.execute(sql)
    return [dict(row) for row in result.mappings().all()]


async def _keyword_search(db: AsyncSession, question: str, top_k: int) -> list[dict]:
    """PostgreSQL full-text search on chunk content + section number matching."""
    results = []

    # 1. Direct section number match (highest priority)
    section_refs = _extract_section_refs(question)
    if section_refs:
        # Strip sub-section references for DB lookup: "10(13A)" -> "10"
        base_sections = list(set(ref.split("(")[0] for ref in section_refs))
        # Prioritize primary acts (IT Act 1961, CGST Act 2017) over amendment docs
        # Also filter by doc_type = 'act' to avoid rate table rows with same "section_number"
        section_result = await db.execute(
            text(
                "SELECT c.id, c.content, c.section_number, c.section_title, "
                "c.chapter, c.part, c.token_count, c.metadata, "
                "d.title as document_title, "
                "CASE "
                "  WHEN d.title LIKE '%Income-tax Act, 1961%' THEN 0.98 "
                "  WHEN d.title LIKE '%Income Tax Act, 2025%' THEN 0.96 "
                "  WHEN d.title LIKE '%Central Goods and Services Tax Act%' THEN 0.97 "
                "  WHEN d.title LIKE '%Integrated Goods%' THEN 0.96 "
                "  WHEN d.doc_type = 'rules' THEN 0.95 "
                "  WHEN d.doc_type = 'act' THEN 0.93 "
                "  WHEN d.doc_type = 'dtaa' THEN 0.90 "
                "  ELSE 0.85 "
                "END as similarity "
                "FROM chunks c "
                "JOIN documents d ON c.document_id = d.id "
                "WHERE d.is_current = true "
                "AND c.section_number = ANY(:sections) "
                "AND d.doc_type IN ('act', 'rules', 'dtaa', 'guide') "
                "ORDER BY similarity DESC, length(c.content) DESC, c.chunk_index "
                "LIMIT :topk"
            ).bindparams(
                bindparam("sections", value=base_sections),
                bindparam("topk", value=top_k, type_=Integer),
            )
        )
        results.extend([dict(row) for row in section_result.mappings().all()])

    # 2. Full-text keyword search for important terms
    # Include 3-char tax terms (GST, TDS, ITC, HRA, RCM, NPS, etc.)
    keywords = re.findall(r"\b[a-zA-Z]{3,}\b", question.lower())
    stopwords = {
        "what", "which", "where", "when", "does", "that", "this", "with",
        "from", "have", "under", "about", "their", "there", "been", "will",
        "would", "should", "could", "being", "after", "before", "they",
        "them", "than", "then", "into", "also", "some", "such", "each",
        "very", "more", "most", "much", "many", "the", "and", "for", "are",
        "how", "can", "you", "has", "was", "not", "but",
    }
    meaningful = [k for k in keywords if k not in stopwords][:6]

    if meaningful and len(results) < top_k:
        # Use OR for broader matching — rank by relevance score
        search_term = " | ".join(meaningful)
        try:
            ts_result = await db.execute(
                text(
                    "SELECT c.id, c.content, c.section_number, c.section_title, "
                    "c.chapter, c.part, c.token_count, c.metadata, "
                    "d.title as document_title, "
                    "ts_rank(to_tsvector('english', c.content), "
                    "  to_tsquery('english', :search)) * 0.85 as similarity "
                    "FROM chunks c "
                    "JOIN documents d ON c.document_id = d.id "
                    "WHERE d.is_current = true "
                    "AND to_tsvector('english', c.content) @@ to_tsquery('english', :search) "
                    "ORDER BY similarity DESC "
                    "LIMIT :topk"
                ).bindparams(
                    bindparam("search", value=search_term, type_=String),
                    bindparam("topk", value=top_k, type_=Integer),
                )
            )
            results.extend([dict(row) for row in ts_result.mappings().all()])
        except Exception:
            pass  # Full-text search may fail on some queries, fall back to semantic only

    # 3. ILIKE fallback for short/specific terms the full-text parser may miss
    # (e.g., "reverse charge", "standard deduction", "form 26AS")
    key_phrases = re.findall(r"(?:reverse charge|standard deduction|form 26as|input tax credit|"
                             r"advance tax|capital gains|assessment year|financial year|"
                             r"composition scheme|place of supply|time of supply|"
                             r"zero rated|nil rated|exempt supply|"
                             r"set off|carry forward|presumptive taxation|"
                             r"updated return|revised return|belated return|"
                             r"late filing|penalty|234f|gst registration|"
                             r"hra exemption|house rent|80c deduction|80d medical|"
                             r"nps deduction|80ccd|home loan|section 24|"
                             r"old regime|new regime|old vs new|"
                             r"tds on rent|tds on salary|tds on professional|"
                             r"itr filing|due date|form 16|"
                             r"ltcg|stcg|long term|short term|"
                             r"gst rate|gst export|e-invoice|e-way bill)", question.lower())
    if key_phrases and len(results) < top_k:
        for phrase in key_phrases[:2]:
            try:
                ilike_result = await db.execute(
                    text(
                        "SELECT c.id, c.content, c.section_number, c.section_title, "
                        "c.chapter, c.part, c.token_count, c.metadata, "
                        "d.title as document_title, "
                        "CASE WHEN d.doc_type = 'guide' THEN 0.82 ELSE 0.75 END as similarity "
                        "FROM chunks c "
                        "JOIN documents d ON c.document_id = d.id "
                        "WHERE d.is_current = true "
                        "AND LOWER(c.content) LIKE :phrase "
                        "ORDER BY d.doc_type = 'guide' DESC, d.doc_type = 'act' DESC, length(c.content) DESC "
                        "LIMIT :topk"
                    ).bindparams(
                        bindparam("phrase", value=f"%{phrase}%", type_=String),
                        bindparam("topk", value=top_k, type_=Integer),
                    )
                )
                results.extend([dict(row) for row in ilike_result.mappings().all()])
            except Exception:
                pass

    return results


async def retrieve_chunks(db: AsyncSession, question: str) -> list[dict]:
    """Hybrid retrieval: combines semantic search + keyword search + cross-reference expansion."""
    top_k = settings.retrieval_top_k

    # Run both search strategies
    semantic_results = await _semantic_search(db, question, top_k * 2)
    keyword_results = await _keyword_search(db, question, top_k)

    # Merge and deduplicate, preferring higher similarity
    seen_ids = set()
    merged = []

    # Keyword results first (they're more precise when sections are mentioned)
    for row in keyword_results:
        chunk_id = str(row["id"])
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(row)

    # Then semantic results
    for row in semantic_results:
        chunk_id = str(row["id"])
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(row)

    # Sort by similarity descending
    merged.sort(key=lambda x: float(x.get("similarity", 0)), reverse=True)

    # Apply threshold and token budget
    chunks = []
    total_tokens = 0

    for row in merged:
        sim = float(row.get("similarity", 0))
        if sim < settings.retrieval_threshold:
            continue

        token_count = row.get("token_count") or _count_tokens(row["content"])
        if total_tokens + token_count > settings.chunk_token_budget:
            break

        total_tokens += token_count
        chunks.append({
            "id": str(row["id"]),
            "content": row["content"],
            "section_number": row.get("section_number"),
            "section_title": row.get("section_title"),
            "chapter": row.get("chapter"),
            "part": row.get("part"),
            "document_title": row.get("document_title"),
            "similarity": sim,
            "token_count": token_count,
            "metadata": row.get("metadata") or {},
        })

    # Cross-reference expansion (1-hop)
    cross_refs = set()
    for chunk in chunks:
        refs = chunk["metadata"].get("cross_refs", [])
        cross_refs.update(refs)

    existing_sections = {c["section_number"] for c in chunks if c["section_number"]}
    cross_refs -= existing_sections

    if cross_refs and total_tokens < settings.chunk_token_budget:
        ref_result = await db.execute(
            select(Chunk).where(Chunk.section_number.in_(cross_refs)).limit(5)
        )
        for ref_chunk in ref_result.scalars():
            token_count = ref_chunk.token_count or _count_tokens(ref_chunk.content)
            if total_tokens + token_count > settings.chunk_token_budget:
                break
            total_tokens += token_count
            chunks.append({
                "id": str(ref_chunk.id),
                "content": ref_chunk.content,
                "section_number": ref_chunk.section_number,
                "section_title": ref_chunk.section_title,
                "chapter": ref_chunk.chapter,
                "part": ref_chunk.part,
                "document_title": None,
                "similarity": 0.0,
                "token_count": token_count,
                "metadata": ref_chunk.metadata_ or {},
                "is_cross_ref": True,
            })

    logger.info("retriever.complete", total_chunks=len(chunks), total_tokens=total_tokens,
                semantic_hits=len(semantic_results), keyword_hits=len(keyword_results))
    return chunks
