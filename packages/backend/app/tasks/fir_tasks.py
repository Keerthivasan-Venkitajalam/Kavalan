"""
Digital FIR generation tasks
"""
from app.celery_app import celery_app
from app.services.fir_generator import FIRGenerator
from app.db.mongodb import MongoDB
from app.db.postgres import PostgresDB
from datetime import datetime
from uuid import UUID
import logging
import asyncio

logger = logging.getLogger(__name__)

# Initialize FIR generator (singleton)
_fir_generator = None
_mongodb = None
_postgres_db = None


async def get_fir_generator():
    """Get or create FIR generator instance"""
    global _fir_generator, _mongodb, _postgres_db
    
    if _fir_generator is None:
        # Initialize MongoDB
        if _mongodb is None:
            _mongodb = MongoDB()
            await _mongodb.connect()
        
        # Initialize PostgreSQL
        if _postgres_db is None:
            _postgres_db = PostgresDB()
            await _postgres_db.connect()
        
        _fir_generator = FIRGenerator(_mongodb, _postgres_db)
    
    return _fir_generator


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=10,
    retry_jitter=True
)
def generate_fir_task(
    self,
    session_id: str,
    user_id: str,
    threat_score: float,
    threat_level: str,
    audio_score: float,
    visual_score: float,
    liveness_score: float,
    confidence: float,
    timestamp: str
):
    """
    Generate Digital FIR package for confirmed threat.
    
    This task is automatically triggered when threat score >= 7.0.
    Must complete within 5 seconds per requirement 12.1.
    
    Args:
        session_id: Session UUID as string
        user_id: User UUID as string
        threat_score: Unified threat score
        threat_level: Threat level (low/moderate/high/critical)
        audio_score: Audio modality score
        visual_score: Visual modality score
        liveness_score: Liveness modality score
        confidence: Overall confidence score
        timestamp: ISO format timestamp string
    
    Returns:
        Dictionary with FIR ID and generation status
    
    Retry logic:
    - Max 2 retry attempts (to stay within 5 second window)
    - Exponential backoff: 2^n seconds
    """
    try:
        logger.info(
            f"FIR generation task started for session {session_id}, "
            f"threat_score={threat_score:.2f}"
        )
        
        # Convert string parameters to proper types
        session_uuid = UUID(session_id)
        user_uuid = UUID(user_id)
        timestamp_dt = datetime.fromisoformat(timestamp)
        
        # Run async FIR generation
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def _generate():
            generator = await get_fir_generator()
            
            # Check if FIR should be generated
            should_generate = await generator.should_generate_fir(
                threat_score=threat_score,
                session_id=session_uuid
            )
            
            if not should_generate:
                logger.info(f"FIR generation skipped for session {session_id}")
                return {
                    "success": False,
                    "reason": "FIR already exists or threshold not met"
                }
            
            # Generate FIR
            result = await generator.generate_fir(
                session_id=session_uuid,
                user_id=user_uuid,
                threat_score=threat_score,
                threat_level=threat_level,
                audio_score=audio_score,
                visual_score=visual_score,
                liveness_score=liveness_score,
                confidence=confidence,
                timestamp=timestamp_dt
            )
            
            return {
                "success": result.success,
                "fir_id": result.fir_id,
                "object_id": result.object_id,
                "generated_at": result.generated_at.isoformat(),
                "error": result.error
            }
        
        result = loop.run_until_complete(_generate())
        
        if result["success"]:
            logger.info(
                f"FIR generated successfully: {result['fir_id']} "
                f"for session {session_id}"
            )
        else:
            logger.warning(
                f"FIR generation failed for session {session_id}: "
                f"{result.get('error', result.get('reason', 'Unknown error'))}"
            )
        
        return result
    
    except Exception as e:
        logger.error(f"FIR generation task failed: {e}", exc_info=True)
        
        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        # Return failure result if max retries exceeded
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }
