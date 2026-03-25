from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.db.database import get_db
from app.dependencies import limiter

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question cannot be empty")
        if len(v.strip()) < 3:
            raise ValueError("Question is too short")
        return v.strip()


@router.post("/ask")
@limiter.limit("60/hour")
async def ask_question(request: Request, body: AskRequest, db: AsyncSession = Depends(get_db)):
    """Core RAG Q&A endpoint. Returns SSE stream of answer tokens, followed by citations and confidence."""
    from app.core.rag_pipeline import rag_pipeline

    async def event_generator():
        async for event in rag_pipeline(body.question, body.conversation_id, db):
            yield event

    return EventSourceResponse(event_generator())
