import structlog

logger = structlog.get_logger()


def compute_confidence(chunks: list[dict], llm_response: dict) -> str:
    """Multi-signal confidence scoring: retrieval similarity, source coherence, LLM self-assessment."""

    # Signal 1: Average retrieval similarity of top-5 chunks
    similarities = sorted([c["similarity"] for c in chunks if c.get("similarity", 0) > 0], reverse=True)[:5]
    avg_similarity = sum(similarities) / len(similarities) if similarities else 0

    # Signal 2: Source coherence — do chunks come from the same section/chapter?
    sections = [c["section_number"] for c in chunks if c.get("section_number")]
    chapters = [c["chapter"] for c in chunks if c.get("chapter")]
    unique_sections = len(set(sections))
    unique_chapters = len(set(chapters))
    # More coherent if fewer unique sources
    coherence_score = 1.0
    if unique_sections > 5:
        coherence_score = 0.5
    elif unique_sections > 3:
        coherence_score = 0.7

    # Signal 3: LLM self-assessment
    llm_confidence = llm_response.get("confidence", "LOW")
    llm_score = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}.get(llm_confidence, 0.3)

    # Weighted combination
    final_score = (avg_similarity * 0.4) + (coherence_score * 0.2) + (llm_score * 0.4)

    if final_score >= 0.75:
        confidence = "HIGH"
    elif final_score >= 0.5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    logger.info(
        "confidence.computed",
        avg_similarity=round(avg_similarity, 3),
        coherence_score=coherence_score,
        llm_confidence=llm_confidence,
        final_score=round(final_score, 3),
        confidence=confidence,
    )
    return confidence
