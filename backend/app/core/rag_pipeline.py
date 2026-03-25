"""RAG pipeline orchestrator with smart routing.

Routes questions to the optimal handler:
- CALCULATION → SQL rate engine + formatted response
- COMPARISON → Dual SQL calculation + RAG context
- RATE_LOOKUP → SQL + optional RAG for context
- IN_SCOPE → Full RAG pipeline
- OUT_OF_SCOPE → Redirect to tax topics
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.confidence import compute_confidence
from app.core.generator import generate_answer
from app.core.rate_lookup import (
    lookup_income_tax_slab, lookup_tds_rate, lookup_gst_rate,
    lookup_tcs_rate, lookup_cii, lookup_deadline,
)
from app.core.retriever import retrieve_chunks
from app.core.scope_detector import detect_scope, QuestionIntent
from app.db.models import QueryCache

logger = structlog.get_logger()

DISCLAIMER = "This is an AI tax research assistant — not a substitute for professional advice. For filing decisions or complex cases, please consult a Chartered Accountant (CA)."


def _hash_question(question: str) -> str:
    normalized = question.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


async def _check_cache(db: AsyncSession, question_hash: str) -> dict | None:
    result = await db.execute(
        select(QueryCache).where(
            QueryCache.question_hash == question_hash,
            QueryCache.expires_at > datetime.now(timezone.utc),
        )
    )
    cached = result.scalar_one_or_none()
    if cached:
        cached.hit_count += 1
        await db.commit()
        return cached.response_json
    return None


async def _store_cache(db: AsyncSession, question: str, question_hash: str, response: dict):
    cache_entry = QueryCache(
        question_hash=question_hash,
        question_text=question,
        response_json=response,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.query_cache_ttl_days),
    )
    db.add(cache_entry)
    await db.commit()


def _format_slab_table(calc: dict) -> str:
    """Format income tax calculation as a readable markdown table with summary."""
    lines = [f"**Income Tax Calculation — {calc['regime'].upper()} Regime (AY {calc['assessment_year']})**"]
    lines.append("")
    lines.append(f"Gross Income: **₹{calc['income']:,.0f}**")
    lines.append("")
    lines.append("| Slab | Rate | Taxable | Tax |")
    lines.append("|------|------|---------|-----|")
    for slab in calc["slabs"]:
        lines.append(f"| {slab['range']} | {slab['rate']}% | ₹{slab['taxable_amount']:,.0f} | ₹{slab['tax']:,.0f} |")
    lines.append("")
    # Summary section — plain markdown, not table rows
    lines.append(f"**Tax before cess:** ₹{calc['total_tax']:,.0f}")
    lines.append("")
    if calc.get("rebate_87a", 0) > 0:
        lines.append(f"**Rebate u/s 87A:** -₹{calc['rebate_87a']:,.0f}")
        lines.append("")
    lines.append(f"**Health & Education Cess (4%):** ₹{calc['cess']:,.0f}")
    lines.append("")
    lines.append(f"### 💰 Total Tax: ₹{calc['total_liability']:,.0f}")
    lines.append("")
    lines.append(f"📊 Effective Tax Rate: **{calc['effective_rate']}%**")
    return "\n".join(lines)


async def _handle_calculation(intent: QuestionIntent, db: AsyncSession):
    """Handle tax calculation questions using SQL engine."""
    income = intent.params.get("income", 0)
    regime = intent.params.get("regime", "new")

    calc = await lookup_income_tax_slab(db, income=income, regime=regime)
    if "error" in calc:
        yield {"event": "answer", "data": f"Could not calculate tax: {calc['error']}"}
        yield {"event": "metadata", "data": json.dumps({"citations": [], "confidence": "LOW", "disclaimer": DISCLAIMER})}
        return

    answer = _format_slab_table(calc)
    yield {"event": "answer", "data": answer}
    yield {"event": "metadata", "data": json.dumps({
        "citations": [],
        "confidence": "HIGH",
        "assessment_year": calc["assessment_year"],
        "disclaimer": DISCLAIMER,
    })}


async def _handle_comparison(intent: QuestionIntent, question: str, db: AsyncSession):
    """Handle comparison questions (old vs new regime) with both calculations + RAG context."""
    income = intent.params.get("income")

    parts = []

    if income and income > 0:
        # Calculate both regimes
        new_calc = await lookup_income_tax_slab(db, income=income, regime="new")
        old_calc = await lookup_income_tax_slab(db, income=income, regime="old")

        if "error" not in new_calc and "error" not in old_calc:
            parts.append(f"## Tax Comparison for Income ₹{income:,.0f}\n")
            parts.append(_format_slab_table(new_calc))
            parts.append("\n---\n")
            parts.append(_format_slab_table(old_calc))
            parts.append("\n---\n")

            diff = old_calc["total_liability"] - new_calc["total_liability"]
            if diff > 0:
                parts.append(f"**The New Regime saves you ₹{diff:,.0f}** compared to the Old Regime at this income level.")
            elif diff < 0:
                parts.append(f"**The Old Regime saves you ₹{abs(diff):,.0f}** compared to the New Regime at this income level.")
                parts.append("\nNote: The Old Regime allows deductions under Sections 80C, 80D, HRA exemption, etc. Factor in your actual deductions before deciding.")
            else:
                parts.append("Both regimes result in the same tax liability at this income level.")

            yield {"event": "answer", "data": "\n".join(parts)}
            yield {"event": "metadata", "data": json.dumps({
                "citations": [],
                "confidence": "HIGH",
                "assessment_year": new_calc["assessment_year"],
                "disclaimer": DISCLAIMER,
            })}
            return

    # No income specified — give a RAG-based qualitative comparison
    chunks = await retrieve_chunks(db, question + " old regime new regime tax slab comparison deduction 80C 115BAC")

    if chunks:
        full_answer = ""
        raw_response = None
        async for event in generate_answer(
            question + "\n\nIMPORTANT: Compare both the old and new tax regimes. Mention the key deductions available only in the old regime (80C, 80D, HRA, etc.) and the lower slab rates in the new regime.",
            chunks,
        ):
            if event["type"] == "token":
                full_answer += event["data"]
                yield {"event": "token", "data": event["data"]}
            elif event["type"] == "complete":
                raw_response = event["data"]

        confidence = compute_confidence(chunks, raw_response) if raw_response else "MEDIUM"
        citations = raw_response.get("citations", []) if raw_response else []
        yield {"event": "metadata", "data": json.dumps({
            "citations": citations,
            "confidence": confidence,
            "assessment_year": raw_response.get("assessment_year") if raw_response else None,
            "disclaimer": DISCLAIMER,
        })}
    else:
        yield {"event": "answer", "data": "I need an income amount to compare the regimes properly. Try something like 'Compare old vs new regime for 15 lakh income'. If you're unsure which regime suits you, a CA can help factor in your specific deductions."}
        yield {"event": "metadata", "data": json.dumps({"citations": [], "confidence": "LOW", "disclaimer": DISCLAIMER})}


async def _handle_rate_lookup(intent: QuestionIntent, question: str, db: AsyncSession):
    """Handle rate lookup questions — SQL first, then RAG for context."""
    q_lower = question.lower()

    # Try to detect what kind of rate
    if "tds" in q_lower or "194" in q_lower or "192" in q_lower:
        # Extract section number if present
        import re
        section_match = re.search(r"(?:section\s+)?(\d{3}[A-Z]{0,2})", question)
        section = section_match.group(1) if section_match else None
        rate_data = await lookup_tds_rate(db, section=section)
        if rate_data["results"]:
            parts = ["**TDS Rate" + (f" — Section {section}" if section else "s") + "**\n"]
            for r in rate_data["results"]:
                line = f"• **Section {r['section']}**: {r['category']} — **{r['rate']}%**"
                if r.get("threshold"):
                    line += f" (threshold: ₹{r['threshold']:,.0f})"
                if r.get("notes"):
                    line += f" ({r['notes']})"
                parts.append(line)
            # Supplement with RAG context
            chunks = await retrieve_chunks(db, question)
            answer = "\n".join(parts)
            if chunks:
                answer += "\n\n---\n\n**Additional context from the Act:**\n"
                # Get RAG answer for context
                async for event in generate_answer(question, chunks[:5]):
                    if event["type"] == "token":
                        answer += event["data"]
                        # Don't stream — we'll send the full answer at once
                    elif event["type"] == "complete":
                        raw_response = event["data"]

            yield {"event": "answer", "data": answer}
            yield {"event": "metadata", "data": json.dumps({
                "citations": [{"section_number": r["section"], "section_title": r["category"], "excerpt": f"TDS rate: {r['rate']}%"} for r in rate_data["results"]],
                "confidence": "HIGH",
                "disclaimer": DISCLAIMER,
            })}
            return

    elif "gst" in q_lower:
        import re
        cat_match = re.search(r"(?:gst\s+rate\s+(?:for|on|of)\s+)(.+?)(?:\?|$)", q_lower)
        category = cat_match.group(1).strip() if cat_match else None
        rate_data = await lookup_gst_rate(db, category=category)
        if rate_data["results"]:
            parts = ["**GST Rates" + (f" — {category}" if category else "") + "**\n"]
            for r in rate_data["results"]:
                line = f"• {r['category']} — **{r['rate']}%**"
                if r.get("notes"):
                    line += f" ({r['notes']})"
                parts.append(line)
            yield {"event": "answer", "data": "\n".join(parts)}
            yield {"event": "metadata", "data": json.dumps({
                "citations": [],
                "confidence": "HIGH",
                "disclaimer": DISCLAIMER,
            })}
            return

    # TCS rates
    elif "tcs" in q_lower or "206c" in q_lower or "tax collected" in q_lower:
        rate_data = await lookup_tcs_rate(db)
        if rate_data["results"]:
            parts = ["**TCS (Tax Collected at Source) Rates**\n"]
            for r in rate_data["results"]:
                line = f"• **{r['section']}**: {r['category']} — **{r['rate']}%**"
                if r.get("threshold"):
                    line += f" (threshold: ₹{r['threshold']:,.0f})"
                if r.get("notes"):
                    line += f" ({r['notes']})"
                parts.append(line)
            yield {"event": "answer", "data": "\n".join(parts)}
            yield {"event": "metadata", "data": json.dumps({"citations": [], "confidence": "HIGH", "disclaimer": DISCLAIMER})}
            return

    # Cost Inflation Index
    elif "cii" in q_lower or "cost inflation" in q_lower or "inflation index" in q_lower:
        import re
        fy_match = re.search(r"(\d{4})-?(\d{2,4})", q_lower)
        fy = f"{fy_match.group(1)}-{fy_match.group(2)}" if fy_match else None
        cii_data = await lookup_cii(db, financial_year=fy)
        if cii_data["results"]:
            parts = ["**Cost Inflation Index (CII)**\n"]
            parts.append("| Financial Year | CII Value |")
            parts.append("|---|---|")
            for v in cii_data["results"]:
                parts.append(f"| {v['financial_year']} | **{v['cii_value']}** |")
            parts.append(f"\n*Base year: 2001-02 = 100*")
            yield {"event": "answer", "data": "\n".join(parts)}
            yield {"event": "metadata", "data": json.dumps({"citations": [], "confidence": "HIGH", "disclaimer": DISCLAIMER})}
            return

    # Filing deadlines
    elif any(kw in q_lower for kw in ("due date", "deadline", "last date", "filing date", "when to file")):
        deadline_data = await lookup_deadline(db)
        if deadline_data["results"]:
            parts = ["**Tax Filing Deadlines**\n"]
            for d in deadline_data["results"]:
                parts.append(f"• **{d['form']}** ({d['section'] or ''}): {d['deadline']}")
            yield {"event": "answer", "data": "\n".join(parts)}
            yield {"event": "metadata", "data": json.dumps({"citations": [], "confidence": "HIGH", "disclaimer": DISCLAIMER})}
            return

    # Fallback to standard RAG for slab lookups and other rates
    async for event in _handle_rag(question, db):
        yield event


async def _handle_rag(question: str, db: AsyncSession):
    """Standard RAG pipeline: retrieve → generate → score."""
    chunks = await retrieve_chunks(db, question)

    if not chunks:
        yield {"event": "answer", "data": "I wasn't able to find a confident answer to this from the tax law documents I have. This may need a more specific reading of the law or recent amendments. We'd recommend consulting a Chartered Accountant (CA) for an accurate answer to this one."}
        yield {"event": "metadata", "data": json.dumps({"citations": [], "confidence": "LOW", "disclaimer": DISCLAIMER})}
        return

    full_answer = ""
    raw_response = None
    async for event in generate_answer(question, chunks):
        if event["type"] == "token":
            full_answer += event["data"]
            yield {"event": "token", "data": event["data"]}
        elif event["type"] == "complete":
            raw_response = event["data"]

    if raw_response:
        confidence = compute_confidence(chunks, raw_response)
        citations = raw_response.get("citations", [])
        assessment_year = raw_response.get("assessment_year")
    else:
        confidence = "LOW"
        citations = []
        assessment_year = None

    yield {"event": "metadata", "data": json.dumps({
        "citations": citations,
        "confidence": confidence,
        "assessment_year": assessment_year,
        "disclaimer": DISCLAIMER,
    })}


async def rag_pipeline(question: str, conversation_id: str | None, db: AsyncSession):
    """Main orchestrator. Routes questions to the optimal handler."""
    log = logger.bind(question=question)
    log.info("rag_pipeline.start")

    # 1. Check cache
    question_hash = _hash_question(question)
    cached = await _check_cache(db, question_hash)
    if cached:
        log.info("rag_pipeline.cache_hit")
        yield {"event": "answer", "data": cached["answer"]}
        yield {"event": "metadata", "data": json.dumps({
            "citations": cached["citations"],
            "confidence": cached["confidence"],
            "assessment_year": cached.get("assessment_year"),
            "disclaimer": DISCLAIMER,
            "cached": True,
        })}
        return

    # 2. Detect intent
    intent = detect_scope(question)
    log.info("rag_pipeline.intent", scope=intent.scope, sub_type=intent.sub_type, params=intent.params)

    # 3. Route to handler
    full_answer = ""
    full_metadata = {}

    if intent.scope == "OUT_OF_SCOPE":
        answer = "I'm designed to help with Indian tax law — Income Tax, GST, TDS, deductions, and related topics. This question doesn't seem to fall in that area. Try asking something like 'What deductions can I claim under Section 80C?' or 'How much tax on 15 lakh income?'"
        yield {"event": "answer", "data": answer}
        yield {"event": "metadata", "data": json.dumps({"citations": [], "confidence": "LOW", "disclaimer": DISCLAIMER})}
        full_answer = answer
        full_metadata = {"answer": answer, "citations": [], "confidence": "LOW"}

    elif intent.scope == "CALCULATION":
        async for event in _handle_calculation(intent, db):
            if event.get("event") == "answer":
                full_answer = event["data"]
            elif event.get("event") == "metadata":
                full_metadata = json.loads(event["data"])
                full_metadata["answer"] = full_answer
            yield event

    elif intent.scope == "COMPARISON":
        async for event in _handle_comparison(intent, question, db):
            if event.get("event") == "answer":
                full_answer = event["data"]
            elif event.get("event") == "token":
                full_answer += event.get("data", "")
            elif event.get("event") == "metadata":
                full_metadata = json.loads(event["data"])
                full_metadata["answer"] = full_answer
            yield event

    elif intent.scope == "RATE_LOOKUP":
        async for event in _handle_rate_lookup(intent, question, db):
            if event.get("event") == "answer":
                full_answer = event["data"]
            elif event.get("event") == "token":
                full_answer += event.get("data", "")
            elif event.get("event") == "metadata":
                full_metadata = json.loads(event["data"])
                full_metadata["answer"] = full_answer
            yield event

    else:  # IN_SCOPE
        async for event in _handle_rag(question, db):
            if event.get("event") == "answer":
                full_answer = event["data"]
            elif event.get("event") == "token":
                full_answer += event.get("data", "")
            elif event.get("event") == "metadata":
                full_metadata = json.loads(event["data"])
                full_metadata["answer"] = full_answer
            yield event

    # 4. Cache the response
    if full_answer and full_metadata:
        cache_data = {
            "answer": full_answer,
            "citations": full_metadata.get("citations", []),
            "confidence": full_metadata.get("confidence", "LOW"),
            "assessment_year": full_metadata.get("assessment_year"),
        }
        await _store_cache(db, question, question_hash, cache_data)

    log.info("rag_pipeline.complete", scope=intent.scope, confidence=full_metadata.get("confidence"))
