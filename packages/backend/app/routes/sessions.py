"""
Session management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path
from app.models import SessionStatusResponse, ThreatStatus, ErrorResponse
from app.middleware import get_current_user
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get(
    "/{session_id}/status",
    response_model=SessionStatusResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_session_status(
    session_id: str = Path(..., description="Session UUID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get current threat status for a session.
    
    Returns the latest threat assessment including:
    - Current threat score and level
    - Individual modality scores (audio, visual, liveness)
    - Alert status
    - Threat explanations
    
    **Requirements**: 2.6, 7.1
    """
    try:
        logger.info(
            f"Session status request from user {current_user.get('user_id')} "
            f"for session {session_id}"
        )
        
        # Validate session belongs to user
        if current_user.get('session_id') != session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to authenticated user"
            )
        
        # TODO: Fetch actual session data from database
        # For now, return mock data structure
        # This will be implemented in Task 13 (Database Layer)
        
        # Mock response for API structure
        threat_status = ThreatStatus(
            session_id=session_id,
            current_threat_score=0.0,
            threat_level="low",
            is_alert=False,
            last_update=datetime.utcnow(),
            modality_scores={
                "audio": 0.0,
                "visual": 0.0,
                "liveness": 0.0
            },
            explanation=[],
            confidence=1.0
        )
        
        response = SessionStatusResponse(
            session_id=session_id,
            status="active",
            threat_status=threat_status,
            start_time=datetime.utcnow(),
            duration_seconds=0,
            alert_count=0,
            max_threat_score=0.0
        )
        
        logger.info(f"Session status retrieved for {session_id}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session status error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "SESSION_STATUS_ERROR",
                    "message": "Failed to retrieve session status",
                    "details": str(e)
                }
            }
        )
