"""
Analysis API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.models import (
    AudioAnalysisRequest,
    VisualAnalysisRequest,
    LivenessAnalysisRequest,
    AudioAnalysisResponse,
    VisualAnalysisResponse,
    LivenessAnalysisResponse,
    SessionStatusResponse,
    ErrorResponse
)
from app.middleware import get_current_user
from app.tasks.audio_tasks import analyze_audio
from app.tasks.visual_tasks import analyze_visual_task
from app.tasks.liveness_tasks import analyze_liveness_task
import logging
from datetime import datetime
import uuid
from app.utils.tracing import add_span_attributes, add_span_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analyze", tags=["analysis"])


@router.post(
    "/audio",
    response_model=AudioAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def analyze_audio_endpoint(
    request: AudioAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Accept encrypted audio chunks for analysis.
    
    This endpoint queues audio data for transcription and keyword matching.
    The actual processing happens asynchronously via Celery workers.
    
    **Requirements**: 2.6, 7.1
    """
    try:
        logger.info(
            f"Audio analysis request from user {current_user.get('user_id')} "
            f"for session {request.session_id}"
        )
        
        # Add tracing attributes
        add_span_attributes({
            "user_id": current_user.get('user_id'),
            "session_id": request.session_id,
            "modality": "audio",
            "sample_rate": request.sample_rate,
            "duration": request.duration
        })
        
        # Validate session belongs to user
        if current_user.get('session_id') != request.session_id:
            add_span_event("authorization_failed", {"reason": "session_mismatch"})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to authenticated user"
            )
        
        # Queue task for processing
        task = analyze_audio.delay(
            encrypted_data=request.encrypted_data,
            iv=request.iv,
            session_id=request.session_id,
            timestamp=request.timestamp,
            sample_rate=request.sample_rate,
            duration=request.duration,
            user_id=current_user.get('user_id')
        )
        
        logger.info(f"Audio analysis task queued: {task.id}")
        add_span_event("task_queued", {
            "task_id": task.id,
            "queue": "audio_queue"
        })
        
        return AudioAnalysisResponse(
            task_id=task.id,
            session_id=request.session_id,
            status="queued",
            message="Audio analysis queued for processing"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "AUDIO_ANALYSIS_ERROR",
                    "message": "Failed to queue audio analysis",
                    "details": str(e)
                }
            }
        )


@router.post(
    "/visual",
    response_model=VisualAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def analyze_visual_endpoint(
    request: VisualAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Accept encrypted video frames for visual analysis.
    
    This endpoint queues video frames for uniform/badge detection and threat analysis.
    The actual processing happens asynchronously via Celery workers.
    
    **Requirements**: 2.6, 7.1
    """
    try:
        logger.info(
            f"Visual analysis request from user {current_user.get('user_id')} "
            f"for session {request.session_id}"
        )
        
        # Add tracing attributes
        add_span_attributes({
            "user_id": current_user.get('user_id'),
            "session_id": request.session_id,
            "modality": "visual",
            "width": request.width,
            "height": request.height
        })
        
        # Validate session belongs to user
        if current_user.get('session_id') != request.session_id:
            add_span_event("authorization_failed", {"reason": "session_mismatch"})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to authenticated user"
            )
        
        # Queue task for processing
        task = analyze_visual_task.delay(
            encrypted_data=request.encrypted_data,
            iv=request.iv,
            session_id=request.session_id,
            timestamp=request.timestamp,
            width=request.width,
            height=request.height,
            user_id=current_user.get('user_id')
        )
        
        logger.info(f"Visual analysis task queued: {task.id}")
        add_span_event("task_queued", {
            "task_id": task.id,
            "queue": "visual_queue"
        })
        
        return VisualAnalysisResponse(
            task_id=task.id,
            session_id=request.session_id,
            status="queued",
            message="Visual analysis queued for processing"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Visual analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "VISUAL_ANALYSIS_ERROR",
                    "message": "Failed to queue visual analysis",
                    "details": str(e)
                }
            }
        )


@router.post(
    "/liveness",
    response_model=LivenessAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def analyze_liveness_endpoint(
    request: LivenessAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Accept frames for liveness detection.
    
    This endpoint queues video frames for deepfake and spoofing detection.
    The actual processing happens asynchronously via Celery workers.
    
    **Requirements**: 2.6, 7.1
    """
    try:
        logger.info(
            f"Liveness analysis request from user {current_user.get('user_id')} "
            f"for session {request.session_id}"
        )
        
        # Add tracing attributes
        add_span_attributes({
            "user_id": current_user.get('user_id'),
            "session_id": request.session_id,
            "modality": "liveness",
            "width": request.width,
            "height": request.height
        })
        
        # Validate session belongs to user
        if current_user.get('session_id') != request.session_id:
            add_span_event("authorization_failed", {"reason": "session_mismatch"})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to authenticated user"
            )
        
        # Queue task for processing
        task = analyze_liveness_task.delay(
            encrypted_data=request.encrypted_data,
            iv=request.iv,
            session_id=request.session_id,
            timestamp=request.timestamp,
            width=request.width,
            height=request.height,
            user_id=current_user.get('user_id')
        )
        
        logger.info(f"Liveness analysis task queued: {task.id}")
        add_span_event("task_queued", {
            "task_id": task.id,
            "queue": "liveness_queue"
        })
        
        return LivenessAnalysisResponse(
            task_id=task.id,
            session_id=request.session_id,
            status="queued",
            message="Liveness detection queued for processing"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Liveness analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "LIVENESS_ANALYSIS_ERROR",
                    "message": "Failed to queue liveness detection",
                    "details": str(e)
                }
            }
        )
