"""
Threat fusion and FIR generation coordination tasks
"""
from app.celery_app import celery_app
from app.services.threat_analyzer import ThreatAnalyzer
from app.tasks.fir_tasks import generate_fir_task
from datetime import datetime
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

# Initialize threat analyzer (singleton)
_threat_analyzer = None


def get_threat_analyzer():
    """Get or create threat analyzer instance"""
    global _threat_analyzer
    if _threat_analyzer is None:
        _threat_analyzer = ThreatAnalyzer()
    return _threat_analyzer


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def fuse_and_generate_fir(
    self,
    session_id: str,
    user_id: str,
    audio_score: float,
    visual_score: float,
    liveness_score: float,
    audio_confidence: float = 1.0,
    visual_confidence: float = 1.0,
    liveness_confidence: float = 1.0,
    timestamp: str = None
):
    """
    Fuse modality scores and automatically generate FIR if threshold exceeded.
    
    This task coordinates:
    1. Score fusion using ThreatAnalyzer
    2. Automatic FIR generation when threat_score >= 7.0
    
    Args:
        session_id: Session UUID as string
        user_id: User UUID as string
        audio_score: Audio threat score [0.0, 10.0]
        visual_score: Visual threat score [0.0, 10.0]
        liveness_score: Liveness threat score [0.0, 10.0]
        audio_confidence: Confidence in audio score [0.0, 1.0]
        visual_confidence: Confidence in visual score [0.0, 1.0]
        liveness_confidence: Confidence in liveness score [0.0, 1.0]
        timestamp: ISO format timestamp string (optional, defaults to now)
    
    Returns:
        Dictionary with threat result and FIR generation status
    """
    try:
        logger.info(
            f"Threat fusion task started for session {session_id}, "
            f"scores: audio={audio_score:.2f}, visual={visual_score:.2f}, "
            f"liveness={liveness_score:.2f}"
        )
        
        # Get threat analyzer
        analyzer = get_threat_analyzer()
        
        # Fuse scores
        result = analyzer.fuse_scores(
            audio=audio_score,
            visual=visual_score,
            liveness=liveness_score,
            audio_confidence=audio_confidence,
            visual_confidence=visual_confidence,
            liveness_confidence=liveness_confidence
        )
        
        # Add to history
        analyzer.add_to_history(result)
        
        logger.info(
            f"Threat fusion complete: final_score={result.final_score:.2f}, "
            f"threat_level={result.threat_level}, is_alert={result.is_alert}"
        )
        
        # Prepare response
        response = {
            "session_id": session_id,
            "final_score": result.final_score,
            "audio_score": result.audio_score,
            "visual_score": result.visual_score,
            "liveness_score": result.liveness_score,
            "threat_level": result.threat_level,
            "is_alert": result.is_alert,
            "message": result.message,
            "explanation": result.explanation,
            "confidence": result.confidence,
            "timestamp": result.timestamp.isoformat(),
            "fir_generated": False,
            "fir_id": None
        }
        
        # Check if FIR should be generated (threat_score >= 7.0)
        if result.final_score >= 7.0:
            logger.info(
                f"Threat score {result.final_score:.2f} >= 7.0, "
                f"triggering FIR generation for session {session_id}"
            )
            
            # Use provided timestamp or result timestamp
            fir_timestamp = timestamp if timestamp else result.timestamp.isoformat()
            
            # Trigger FIR generation task asynchronously
            fir_task = generate_fir_task.delay(
                session_id=session_id,
                user_id=user_id,
                threat_score=result.final_score,
                threat_level=result.threat_level,
                audio_score=result.audio_score,
                visual_score=result.visual_score,
                liveness_score=result.liveness_score,
                confidence=result.confidence,
                timestamp=fir_timestamp
            )
            
            logger.info(
                f"FIR generation task queued: {fir_task.id} "
                f"for session {session_id}"
            )
            
            response["fir_generation_task_id"] = fir_task.id
            response["fir_triggered"] = True
        else:
            logger.info(
                f"Threat score {result.final_score:.2f} < 7.0, "
                f"FIR generation not triggered"
            )
            response["fir_triggered"] = False
        
        return response
    
    except Exception as e:
        logger.error(f"Threat fusion task failed: {e}", exc_info=True)
        
        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        # Return failure result if max retries exceeded
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }
