"""Batch embedding using OpenAI text-embedding-3-small."""

import structlog
import tiktoken
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = structlog.get_logger()
_client: AsyncOpenAI | None = None
_encoder = tiktoken.get_encoding("cl100k_base")

BATCH_SIZE = 100
MAX_TOKENS_PER_TEXT = 8000  # text-embedding-3-small supports 8191 max


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


def _truncate_text(text: str) -> str:
    """Truncate text to fit within embedding model's token limit."""
    tokens = _encoder.encode(text)
    if len(tokens) <= MAX_TOKENS_PER_TEXT:
        return text
    logger.warning("embedder.truncated", original_tokens=len(tokens), max_tokens=MAX_TOKENS_PER_TEXT)
    return _encoder.decode(tokens[:MAX_TOKENS_PER_TEXT])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _embed_batch(texts: list[str]) -> list[list[float]]:
    client = _get_client()
    truncated = [_truncate_text(t) for t in texts]
    response = await client.embeddings.create(
        input=truncated,
        model=settings.embedding_model,
    )
    return [item.embedding for item in response.data]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts in batches. Returns embeddings in same order as input."""
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.info("embedder.batch", batch_start=i, batch_size=len(batch), total=len(texts))
        embeddings = await _embed_batch(batch)
        all_embeddings.extend(embeddings)

    logger.info("embedder.complete", total_embedded=len(all_embeddings))
    return all_embeddings
