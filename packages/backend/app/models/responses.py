"""
Response models for API endpoints
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class AudioAnalysisResponse(BaseModel):
    """Response model for audio analysis"""
    task_id: str = Field(..., description="Celery task ID for tracking")
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(default="queued", description="Task status")
    message: str = Field(default="Audio analysis queued for processing")


class VisualAnalysisResponse(BaseModel):
    """Response model for visual analysis"""
    task_id: str = Field(..., description="Celery task ID for tracking")
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(default="queued", description="Task status")
    message: str = Field(default="Visual analysis queued for processing")


class LivenessAnalysisResponse(BaseModel):
    """Response model for liveness detection"""
    task_id: str = Field(..., description="Celery task ID for tracking")
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(default="queued", description="Task status")
    message: str = Field(default="Liveness detection queued for processing")


class ThreatStatus(BaseModel):
    """Threat status for a session"""
    session_id: str
    current_threat_score: float = Field(..., ge=0.0, le=10.0)
    threat_level: str = Field(..., description="low, moderate, high, or critical")
    is_alert: bool
    last_update: datetime
    modality_scores: Dict[str, float] = Field(
        ...,
        description="Individual scores from audio, visual, liveness"
    )
    explanation: List[str] = Field(
        default_factory=list,
        description="Human-readable threat explanations"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)


class SessionStatusResponse(BaseModel):
    """Response model for session status"""
    session_id: str
    status: str = Field(..., description="active, completed, or error")
    threat_status: Optional[ThreatStatus] = None
    start_time: datetime
    duration_seconds: Optional[int] = None
    alert_count: int = Field(default=0)
    max_threat_score: Optional[float] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: Dict[str, Any] = Field(
        ...,
        description="Error details including code, message, and context"
    )
