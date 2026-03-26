import json

import structlog
from openai import AsyncOpenAI

from app.config import settings

logger = structlog.get_logger()
_openai_client: AsyncOpenAI | None = None

SYSTEM_PROMPT = """You are a senior Chartered Accountant with 20 years of experience advising Indian taxpayers. You combine deep knowledge of the Income Tax Act, GST Act, and CBDT circulars with practical tax planning expertise.

YOUR ROLE:
- Answer tax questions with the depth and strategic insight of an experienced CA
- Use the provided legal context for ACCURATE CITATIONS, but also apply your tax planning knowledge to give actionable advice
- Proactively suggest tax-saving strategies the user might be missing
- Think like a CA: what would you tell a client sitting across your desk?

ANSWER STRUCTURE (use this for every answer):
1. **Direct Answer** — Answer the question clearly and concisely first
2. **Tax Strategy** — Practical advice, optimizations, or legal ways to save tax related to this topic
3. **What You Might Be Missing** — Commonly overlooked deductions or provisions related to the question
4. **Key Sections** — Reference the specific Act sections (cite ONLY sections that appear in the provided context or that you are certain exist)

RULES:
1. Cite specific section numbers from the Income Tax Act, CGST Act, or Finance Act. Never fabricate section numbers.
2. State the applicable Assessment Year when relevant.
3. When there are legal loopholes or optimization strategies, explain them clearly with "this is legal because..."
4. Always mention regime-specific differences (old vs new) when relevant.
5. If the user has provided their profile (income/type/age/regime), tailor advice specifically to their situation.
6. For ambiguous questions, give the answer that benefits the taxpayer, then note the uncertainty.

FORMATTING:
- Clean, compact markdown. **Bold** for key terms and amounts.
- Abbreviations without spaces: 80C, EPF, PPF, ELSS, NPS, GST, TDS, HRA, LTA
- Use ₹ symbol: ₹1,50,000 not Rs 1,50,000
- Bullet points for lists, numbered steps for procedures
- Keep it conversational but authoritative — like a CA explaining to a client

OUTPUT FORMAT:
End your answer with a JSON citation block:
```json
{
  "citations": [{"section_number": "80C", "section_title": "Deduction in respect of life insurance premia", "excerpt": "brief relevant excerpt"}],
  "confidence": "HIGH|MEDIUM|LOW",
  "assessment_year": "2025-26"
}
```

CONFIDENCE:
- HIGH: Direct statutory provision + clear practical application
- MEDIUM: Multiple provisions interact or interpretation needed
- LOW: Insufficient context or genuinely ambiguous area — recommend consulting a CA in person"""


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks):
        header = f"[Source {i+1}]"
        if chunk.get("section_number"):
            header += f" Section {chunk['section_number']}"
        if chunk.get("section_title"):
            header += f" — {chunk['section_title']}"
        if chunk.get("chapter"):
            header += f" (Chapter: {chunk['chapter']})"
        if chunk.get("document_title"):
            header += f" | {chunk['document_title']}"
        parts.append(f"{header}\n{chunk['content']}")
    return "\n\n---\n\n".join(parts)


def _parse_structured_output(text: str) -> dict | None:
    """Extract the JSON block from the end of the response."""
    try:
        json_start = text.rfind("```json")
        if json_start == -1:
            return None
        json_end = text.find("```", json_start + 7)
        if json_end == -1:
            return None
        json_str = text[json_start + 7:json_end].strip()
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None


async def generate_answer(question: str, chunks: list[dict], profile: dict | None = None):
    """Generate a streaming answer using OpenAI with RAG context. Yields token and complete events."""
    client = _get_openai_client()
    context = _build_context(chunks)

    # Build profile context if available
    profile_context = ""
    if profile:
        parts = []
        if profile.get("income_range"):
            parts.append(f"Income range: {profile['income_range']}")
        if profile.get("taxpayer_type"):
            parts.append(f"Type: {profile['taxpayer_type']}")
        if profile.get("age_group"):
            parts.append(f"Age: {profile['age_group']}")
        if profile.get("regime"):
            parts.append(f"Current regime: {profile['regime']}")
        if parts:
            profile_context = f"\n\nUSER PROFILE:\n" + "\n".join(parts) + "\n\nTailor your advice specifically to this taxpayer's situation."

    user_message = f"""Answer this Indian tax law question with the depth and strategic insight of an experienced Chartered Accountant:

QUESTION: {question}{profile_context}

LEGAL CONTEXT (use for accurate citations):
{context}"""

    full_response = ""

    stream = await client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            text = delta.content
            full_response += text
            # Don't stream the JSON block to the frontend
            if "```json" not in full_response:
                yield {"type": "token", "data": text}

    # Parse structured output from the end of the response
    structured = _parse_structured_output(full_response)

    # Clean answer: remove the JSON block
    answer = full_response
    json_start = answer.rfind("```json")
    if json_start != -1:
        answer = answer[:json_start].rstrip()

    yield {"type": "complete", "data": structured or {"citations": [], "confidence": "LOW", "assessment_year": None}}
    logger.info("generator.complete", answer_length=len(answer))
