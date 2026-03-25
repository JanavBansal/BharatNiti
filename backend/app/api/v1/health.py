from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    chunk_count = 0
    if db_status == "connected":
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM chunks"))
            chunk_count = result.scalar() or 0
        except Exception:
            pass

    return {"status": "ok", "database": db_status, "chunk_count": chunk_count}
