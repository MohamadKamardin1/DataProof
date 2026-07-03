
from pydantic import BaseModel, Field


class Citation(BaseModel):
    authors: str
    year: int | None = None
    title: str
    venue: str | None = None
    doi_or_url: str | None = None


class PerSampleInterpretation(BaseModel):
    sample_id: str
    classification: str
    rationale: str


class LLMInterpretationResponse(BaseModel):
    """Strict JSON schema the LLM must return."""
    per_sample: list[PerSampleInterpretation] = Field(min_length=1)
    overall_narrative: str = Field(min_length=10)
    citations: list[Citation] = []


class VerifiedCitation(Citation):
    verified: bool = False


class InterpretationResultResponse(BaseModel):
    per_sample: list[PerSampleInterpretation]
    overall_narrative: str
    citations: list[VerifiedCitation]


class InterpretationJobResponse(BaseModel):
    job_id: str
    status: str  # "pending" | "running" | "completed" | "failed"
    result: InterpretationResultResponse | None = None
    error: str | None = None


class InterpretationStartResponse(BaseModel):
    job_id: str
    status_url: str
