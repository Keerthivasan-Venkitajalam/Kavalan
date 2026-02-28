"""
Liveness detection Celery tasks
"""
from app.celery_app import celery_app
from app.services.liveness_detector import LivenessDetector
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import logging

logger = logging.getLogger(__name__)

# Initialize liveness detector (singleton)
_liveness_detector = None

def get_liveness_detector():
    """Get or create liveness detector instance"""
    global _liveness_detector
    if _liveness_detector is None:
        _liveness_detector = LivenessDetector()
    return _liveness_detector


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,  # Base delay in seconds
    autoretry_for=(Exception,),  # Auto-retry on any exception
    retry_backoff=True,  # Enable exponential backoff
    retry_backoff_max=600,  # Max backoff time (10 minutes)
    retry_jitter=True,  # Add randomness to prevent thundering herd
    name='app.tasks.liveness_tasks.analyze_liveness_task'
)
def analyze_liveness_task(
    self,
    encrypted_data: str,
    iv: str,
    session_id: str,
    timestamp: float,
    width: int,
    height: int,
    user_id: str,
    encryption_key: str = None
):
    """
    Detect deepfakes and liveness in video frames.
    
    Args:
        encrypted_data: Base64-encoded encrypted frame data
        iv: Base64-encoded initialization vector
        session_id: Session identifier
        timestamp: Frame timestamp
        width: Frame width in pixels
        height: Frame height in pixels
        user_id: User identifier
        encryption_key: Base64-encoded encryption key (optional, uses default if not provided)
    
    Returns:
        Dictionary with liveness analysis results
    
    Retry logic:
    - Max 3 retry attempts
    - Exponential backoff: 2^n seconds (2s, 4s, 8s)
    - Jitter added to prevent thundering herd
    """
    try:
        logger.info(f"Liveness detection task started for session {session_id}")
        
        # Step 1: Decrypt frame data
        try:
            # Decode base64 strings
            encrypted_bytes = base64.b64decode(encrypted_data)
            iv_bytes = base64.b64decode(iv)
            
            # Use provided key or default (in production, fetch from secure storage)
            if encryption_key:
                key_bytes = base64.b64decode(encryption_key)
            else:
                # Default key for development (32 bytes for AES-256)
                key_bytes = b'0' * 32
            
            # Decrypt using AES-256-GCM
            aesgcm = AESGCM(key_bytes)
            frame_bytes = aesgcm.decrypt(iv_bytes, encrypted_bytes, None)
            
            logger.info(f"Decrypted frame: {len(frame_bytes)} bytes ({width}x{height})")
        
        except Exception as e:
            logger.error(f"Frame decryption failed: {e}")
            raise ValueError(f"Failed to decrypt frame data: {e}")
        
        # Step 2: Get detector instance
        detector = get_liveness_detector()
        
        # Step 3: Analyze frame for liveness
        try:
            result = detector.detect_liveness(frame_bytes, timestamp=timestamp)
            
            logger.info(
                f"Liveness analysis complete: "
                f"face_detected={result.face_detected}, "
                f"liveness_score={result.liveness_score:.2f}, "
                f"is_deepfake={result.is_deepfake}, "
                f"num_faces={result.num_faces}, "
                f"blink_rate={result.blink_rate:.2f}, "
                f"stress_level={result.stress_level:.2f}"
            )
            
            # Step 4: Return results
            return {
                "session_id": session_id,
                "timestamp": timestamp,
                "face_detected": result.face_detected,
                "liveness_score": result.liveness_score,
                "blink_rate": result.blink_rate,
                "stress_level": result.stress_level,
                "is_natural": result.is_natural,
                "is_deepfake": result.is_deepfake,
                "num_faces": result.num_faces,
                "faces": result.faces,
                "width": width,
                "height": height,
                "status": "success"
            }
        
        except Exception as e:
            logger.error(f"Liveness analysis failed: {e}", exc_info=True)
            raise
    
    except Exception as exc:
        logger.error(f"Liveness detection task failed (attempt {self.request.retries + 1}/3): {exc}")
        
        # Exponential backoff: 2^n seconds
        countdown = 2 ** self.request.retries
        logger.info(f"Retrying in {countdown} seconds...")
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True)
def reset_liveness_detector(self, session_id: str = None):
    """
    Reset liveness detector history.
    
    This should be called when a session ends to clear tracking state.
    
    Args:
        session_id: Session identifier (for logging)
    
    Returns:
        Dictionary with operation status
    """
    try:
        logger.info(f"Resetting liveness detector for session {session_id}")
        
        detector = get_liveness_detector()
        detector.reset_history()
        
        return {
            "status": "success",
            "message": "Liveness detector history reset",
            "session_id": session_id
        }
    
    except Exception as exc:
        logger.error(f"Failed to reset liveness detector: {exc}")
        return {
            "status": "error",
            "error": str(exc),
            "session_id": session_id
        }


@celery_app.task(bind=True)
def get_liveness_stats(self):
    """
    Get liveness detector processing statistics.
    
    Returns:
        Dictionary with processing statistics
    """
    try:
        detector = get_liveness_detector()
        stats = detector.get_stats()
        
        return {
            "status": "success",
            "stats": stats
        }
    
    except Exception as exc:
        logger.error(f"Failed to get liveness stats: {exc}")
        return {
            "status": "error",
            "error": str(exc)
        }

