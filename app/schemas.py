"""Pydantic request / response contracts, also used for OpenAPI docs."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    page_count: int
    chunk_count: int
    created_at: datetime


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    document_id: UUID | None = None


class SourceOut(BaseModel):
    ref: int
    filename: str
    page: int
    similarity: float
    snippet: str
    document_id: UUID


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    retrieval_count: int
    latency_ms: int


class HealthOut(BaseModel):
    status: str
    database: str
    gemini_configured: bool
