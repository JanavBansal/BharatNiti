"""Re-embed all chunks with text-embedding-3-large (3072 dims)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, bindparam, String
from app.db.database import async_session
from app.ingestion.embedder import embed_texts

BATCH_SIZE = 50  # Smaller batches for large embeddings


async def main():
    async with async_session() as db:
        # Get all chunks without embeddings (or all chunks to re-embed)
        result = await db.execute(text("SELECT id, content FROM chunks ORDER BY id"))
        rows = result.fetchall()
        total = len(rows)
        print(f"Re-embedding {total} chunks with text-embedding-3-large (3072 dims)...")

        for i in range(0, total, BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            texts = [row[1] for row in batch]
            ids = [str(row[0]) for row in batch]

            embeddings = await embed_texts(texts)

            for chunk_id, embedding in zip(ids, embeddings):
                emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
                await db.execute(
                    text("UPDATE chunks SET embedding = cast(:emb as vector) WHERE id = cast(:cid as uuid)")
                    .bindparams(
                        bindparam("emb", value=emb_str, type_=String),
                        bindparam("cid", value=chunk_id, type_=String),
                    )
                )

            await db.commit()
            print(f"  Batch {i // BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1) // BATCH_SIZE}: {min(i + BATCH_SIZE, total)}/{total} chunks embedded")

    # Update documents metadata
    async with async_session() as db:
        await db.execute(text("UPDATE documents SET embedding_model = 'openai/text-embedding-3-large'"))
        await db.commit()

    print(f"\nDone! All {total} chunks re-embedded with text-embedding-3-large.")


if __name__ == "__main__":
    asyncio.run(main())
