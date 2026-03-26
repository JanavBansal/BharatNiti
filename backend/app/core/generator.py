import json

import structlog
from openai import AsyncOpenAI

from app.config import settings

logger = structlog.get_logger()
_openai_client: AsyncOpenAI | None = None

SYSTEM_PROMPT = """You are an expert Indian tax law research assistant. You answer questions based ONLY on the provided legal text excerpts.

RULES:
1. ALWAYS cite every section number that you reference in your answer. Never fabricate section numbers — only cite sections present in the provided context.
2. State the applicable Assessment Year when relevant.
3. Distinguish between law-as-written and common interpretations.
4. Flag when CBDT circulars modify the base Income Tax Act.
5. If the context is insufficient to fully answer, say so explicitly.
6. For ambiguous questions, present both possible interpretations.
7. Even for broad questions, cite the primary sections that form the basis of your answer.

FORMATTING RULES:
- Use clean, compact markdown. Use **bold** for key terms.
- Use bullet points (- or *) for lists, numbered lists (1. 2. 3.) for steps.
- Keep abbreviations intact with NO spaces: write "80C" not "80 C", "EPF" not "EP F", "PPF" not "PP F", "ELSS" not "EL SS", "NPS" not "N PS", "GST" not "G ST", "TDS" not "TD S".
- Keep section references compact: "Section 80C" not "Section 80 C".
- Use ₹ symbol for amounts: "₹1,50,000" not "Rs 1 , 50 , 000".
- Do NOT add extra spaces around punctuation or within words.

OUTPUT FORMAT:
You MUST always end your answer with a JSON citation block. After your answer, output a JSON block on a new line starting with ```json and ending with ```:
```json
{
  "citations": [{"section_number": "80C", "section_title": "Deduction in respect of life insurance premia", "excerpt": "brief relevant excerpt from the section"}],
  "confidence": "HIGH|MEDIUM|LOW",
  "assessment_year": "2025-26"
}
```

IMPORTANT: The citations array must NEVER be empty if you referenced any section in your answer. Include at least one citation for every section number you mention.

CONFIDENCE GUIDE:
- HIGH: Direct statutory provision clearly answers the question. Use this when the context contains the specific section being asked about.
- MEDIUM: Answer requires interpretation or multiple provisions interact
- LOW: Context is insufficient or conflicting provisions exist"""


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


async def generate_answer(question: str, chunks: list[dict]):
    """Generate a streaming answer using OpenAI with RAG context. Yields token and complete events."""
    client = _get_openai_client()
    context = _build_context(chunks)

    user_message = f"""Based on the following Indian tax law excerpts, answer this question:

QUESTION: {question}

LEGAL CONTEXT:
{context}"""

    full_response = ""

    stream = await client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=2048,
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
