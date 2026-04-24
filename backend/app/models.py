from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    answer: str
    reasoning: str = ""
    sources: list[str] = []
    trace: list[dict] = []
    suggested_action: dict | None = None
    executed: bool = False
    metrics: dict = {}


class ActionRequest(BaseModel):
    action: str
    params: dict[str, Any] = {}


class ActionResponse(BaseModel):
    action: str
    executed: bool
    result: dict[str, Any]


class LogIngestRequest(BaseModel):
    timestamp: str = Field(..., min_length=1, description="ISO 8601 timestamp (e.g., 2026-04-24T10:00:00).")
    service: str = Field(..., min_length=1, max_length=128)
    user_id: str | None = Field(default=None, max_length=32)
    message: str = Field(..., min_length=1, max_length=2000)
    severity: Literal["INFO", "WARN", "ERROR"]


class LogIngestResponse(BaseModel):
    id: int
    status: Literal["ingested"] = "ingested"
