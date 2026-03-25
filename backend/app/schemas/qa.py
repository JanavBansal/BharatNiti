from pydantic import BaseModel


class Citation(BaseModel):
    section_number: str
    section_title: str | None = None
    excerpt: str
    document_title: str | None = None


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: str  # HIGH, MEDIUM, LOW
    assessment_year: str | None = None
    disclaimer: str = "This is a tax research tool, not professional tax advice. Consult a Chartered Accountant for decisions."


class RateResponse(BaseModel):
    rate_type: str
    results: list[dict]


class SlabCalculation(BaseModel):
    income: float
    regime: str
    assessment_year: str
    slabs: list[dict]
    total_tax: float
    effective_rate: float
    cess: float
    total_liability: float
