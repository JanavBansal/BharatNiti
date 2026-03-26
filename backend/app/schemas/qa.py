from pydantic import BaseModel


class Citation(BaseModel):
    section_number: str
    section_title: str | None = None
    excerpt: str
    document_title: str | None = None


class UserProfile(BaseModel):
    income_range: str | None = None  # "<5L", "5-10L", "10-20L", "20-50L", "50L+", "1Cr+"
    taxpayer_type: str | None = None  # "Salaried", "Self-employed", "Freelancer", "Business Owner", "NRI"
    age_group: str | None = None  # "Below 60", "60-80", "Above 80"
    regime: str | None = None  # "Old", "New", "Not sure"


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    profile: UserProfile | None = None


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
