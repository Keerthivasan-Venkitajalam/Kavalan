"""
Request models for API endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AudioAnalysisRequest(BaseModel):
    """Request model for audio analysis"""
    encrypted_data: str = Field(..., description="Base64 encoded encrypted audio data")
    iv: str = Field(..., description="Base64 encoded initialization vector")
    session_id: str = Field(..., description="Session identifier")
    timestamp: float = Field(..., description="Unix timestamp of capture")
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    duration: float = Field(..., description="Audio duration in seconds")


class VisualAnalysisRequest(BaseModel):
    """Request model for visual analysis"""
    encrypted_data: str = Field(..., description="Base64 encoded encrypted frame data")
    iv: str = Field(..., description="Base64 encoded initialization vector")
    session_id: str = Field(..., description="Session identifier")
    timestamp: float = Field(..., description="Unix timestamp of capture")
    width: int = Field(..., description="Frame width in pixels")
    height: int = Field(..., description="Frame height in pixels")


class LivenessAnalysisRequest(BaseModel):
    """Request model for liveness detection"""
    encrypted_data: str = Field(..., description="Base64 encoded encrypted frame data")
    iv: str = Field(..., description="Base64 encoded initialization vector")
    session_id: str = Field(..., description="Session identifier")
    timestamp: float = Field(..., description="Unix timestamp of capture")
    width: int = Field(..., description="Frame width in pixels")
    height: int = Field(..., description="Frame height in pixels")
