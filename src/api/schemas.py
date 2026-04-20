"""
API Request/Response Schemas
-----------------------------
Pydantic models for all API endpoints.
These define exactly what the API accepts and returns.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class RoleEnum(str, Enum):
    general   = "general"
    sales     = "sales"
    executive = "executive"
    interview = "interview"
    coaching  = "coaching"


class JobStatus(str, Enum):
    pending    = "pending"
    started    = "started"
    progress   = "progress"
    completed  = "completed"
    failed     = "failed"


# ── Request Schemas ───────────────────────────────────────

class AnalyzeRequest(BaseModel):
    role: RoleEnum = Field(
        default=RoleEnum.general,
        description="Scoring role profile to apply"
    )


# ── Response Schemas ──────────────────────────────────────

class JobSubmittedResponse(BaseModel):
    job_id: str
    status: str = "pending"
    message: str
    filename: str
    role: str
    estimated_seconds: int = Field(
        description="Estimated processing time in seconds"
    )


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    stage: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class DimensionScoreResponse(BaseModel):
    name: str
    score: float
    normalized: float
    insight: str
    metrics: Dict[str, Any]


class ReportMetadataResponse(BaseModel):
    job_id: str
    filename: str
    duration_seconds: float
    language: str
    role: str
    generated_at: str
    asr_confidence: float
    used_fallback: bool


class AnalysisResultResponse(BaseModel):
    metadata: ReportMetadataResponse
    composite_score: float
    composite_pct: float
    grade: str
    summary: str
    improvement_priorities: List[str]
    dimensions: Dict[str, DimensionScoreResponse]
    transcript: str


class HealthResponse(BaseModel):
    status: str
    gpu_available: bool
    gpu_name: Optional[str]
    models_loaded: Dict[str, bool]
    circuit_breaker: Dict[str, Any]