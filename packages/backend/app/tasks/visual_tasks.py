"""
Visual frame analysis tasks
"""
from app.celery_app import celery_app
from app.services.visual_analyzer import VisualAnalyzer, RateLimitError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import logging
import os
from app.utils.tracing import add_span_attributes, add_span_event, TracedOperation

logger = logging.getLogger(__name__)

# Initialize visual analyzer (singleton)
_visual_analyzer = None

def get_visual_analyzer():
    """Get or create visual analyzer instance"""
    global _visual_analyzer
    if _visual_analyzer is None:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        _visual_analyzer = VisualAnalyzer(api_key=api_key)
    return _visual_analyzer


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,  # Base delay in seconds
    autoretry_for=(Exception,),  # Auto-retry on any exception (except RateLimitError)
    retry_backoff=True,  # Enable exponential backoff
    retry_backoff_max=600,  # Max backoff time (10 minutes)
    retry_jitter=True,  # Add randomness to prevent thundering herd
    name='app.tasks.visual_tasks.analyze_visual_task'
)
def analyze_visual_task(
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
    Analyze video frame for uniforms, badges, and threats.
    
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
        Dictionary with analysis results, score, and metadata
    
    Retry logic:
    - Max 3 retry attempts
    - Exponential backoff: 2^n seconds (2s, 4s, 8s)
    - Jitter added to prevent thundering herd
    - Rate limit errors trigger queueing instead of retry
    """
    try:
        logger.info(f"Visual analysis task started for session {session_id}")
        
        # Add tracing attributes
        add_span_attributes({
            "session_id": session_id,
            "user_id": user_id,
            "width": width,
            "height": height,
            "timestamp": timestamp,
            "task_id": self.request.id,
            "modality": "visual"
        })
        
        # Step 1: Decrypt frame data
        try:
            with TracedOperation("decrypt_frame", {"data_size": len(encrypted_data)}):
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
                add_span_event("frame_decrypted", {
                    "bytes": len(frame_bytes),
                    "width": width,
                    "height": height
                })
        
        except Exception as e:
            logger.error(f"Frame decryption failed: {e}")
            add_span_event("decryption_failed", {"error": str(e)})
            raise ValueError(f"Failed to decrypt frame data: {e}")
        
        # Step 2: Get analyzer instance
        with TracedOperation("get_analyzer"):
            analyzer = get_visual_analyzer()
        
        # Step 3: Analyze frame
        try:
            with TracedOperation("analyze_frame", {
                "width": width,
                "height": height
            }):
                result = analyzer.analyze_frame(frame_bytes)
            
            logger.info(
                f"Visual analysis complete: "
                f"uniform={result.uniform_detected}, "
                f"badge={result.badge_detected}, "
                f"score={result.score:.2f}, "
                f"confidence={result.confidence:.2f}, "
                f"cached={result.cached}"
            )
            
            # Add result attributes to span
            add_span_attributes({
                "uniform_detected": result.uniform_detected,
                "badge_detected": result.badge_detected,
                "score": result.score,
                "confidence": result.confidence,
                "cached": result.cached,
                "threats_count": len(result.threats)
            })
            
            add_span_event("analysis_complete", {
                "uniform": result.uniform_detected,
                "badge": result.badge_detected,
                "score": result.score,
                "cached": result.cached
            })
            
            # Step 4: Return results
            return {
                "session_id": session_id,
                "timestamp": timestamp,
                "uniform_detected": result.uniform_detected,
                "badge_detected": result.badge_detected,
                "threats": result.threats,
                "text_detected": result.text_detected,
                "confidence": result.confidence,
                "score": result.score,
                "analysis": result.analysis,
                "cached": result.cached,
                "width": width,
                "height": height,
                "status": "success"
            }
        
        except RateLimitError as e:
            # Handle rate limit errors specially
            logger.warning(f"Gemini API rate limit hit: {e}")
            add_span_event("rate_limit_hit", {"error": str(e)})
            
            # Queue frame for delayed processing
            analyzer.queue_frame(frame_bytes)
            
            # Return partial result indicating rate limit
            return {
                "session_id": session_id,
                "timestamp": timestamp,
                "uniform_detected": False,
                "badge_detected": False,
                "threats": [],
                "text_detected": "",
                "confidence": 0.0,
                "score": 0.0,
                "analysis": "Rate limit exceeded - frame queued for delayed processing",
                "cached": False,
                "width": width,
                "height": height,
                "status": "rate_limited",
                "queued": True,
                "queue_size": analyzer.get_queue_size()
            }
    
    except Exception as exc:
        logger.error(f"Visual analysis task failed (attempt {self.request.retries + 1}/3): {exc}")
        
        # Don't retry on rate limit errors (already queued)
        if isinstance(exc, RateLimitError):
            logger.info("Rate limit error - not retrying")
            raise
        
        # Exponential backoff: 2^n seconds
        countdown = 2 ** self.request.retries
        logger.info(f"Retrying in {countdown} seconds...")
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True)
def process_queued_frames(self, max_frames: int = 10):
    """
    Process frames from rate limit queue.
    
    This task should be called periodically (e.g., every 60 seconds) to process
    frames that were queued due to rate limits.
    
    Args:
        max_frames: Maximum number of frames to process in this batch
    
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Processing queued frames (max: {max_frames})")
        
        # Get analyzer instance
        analyzer = get_visual_analyzer()
        
        # Get initial queue size
        initial_queue_size = analyzer.get_queue_size()
        
        if initial_queue_size == 0:
            logger.info("No frames in queue")
            return {
                "status": "success",
                "processed": 0,
                "remaining": 0,
                "results": []
            }
        
        # Process queued frames
        results = analyzer.process_queued_frames(max_frames=max_frames)
        
        # Get final queue size
        final_queue_size = analyzer.get_queue_size()
        
        logger.info(
            f"Processed {len(results)} frames from queue. "
            f"Remaining: {final_queue_size}"
        )
        
        return {
            "status": "success",
            "processed": len(results),
            "remaining": final_queue_size,
            "results": [
                {
                    "uniform_detected": r.uniform_detected,
                    "badge_detected": r.badge_detected,
                    "threats": r.threats,
                    "score": r.score,
                    "confidence": r.confidence
                }
                for r in results
            ]
        }
    
    except Exception as exc:
        logger.error(f"Failed to process queued frames: {exc}")
        return {
            "status": "error",
            "error": str(exc),
            "processed": 0,
            "remaining": analyzer.get_queue_size() if analyzer else 0
        }


@celery_app.task(bind=True)
def get_cache_stats(self):
    """
    Get visual analyzer cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        analyzer = get_visual_analyzer()
        stats = analyzer.get_cache_stats()
        
        return {
            "status": "success",
            "cache_size": stats['size'],
            "cache_ttl_seconds": stats['ttl_seconds'],
            "similarity_threshold": stats['similarity_threshold']
        }
    
    except Exception as exc:
        logger.error(f"Failed to get cache stats: {exc}")
        return {
            "status": "error",
            "error": str(exc)
        }


@celery_app.task(bind=True)
def clear_cache(self):
    """
    Clear visual analyzer cache.
    
    Returns:
        Dictionary with operation status
    """
    try:
        analyzer = get_visual_analyzer()
        analyzer.clear_cache()
        
        logger.info("Visual analyzer cache cleared")
        
        return {
            "status": "success",
            "message": "Cache cleared successfully"
        }
    
    except Exception as exc:
        logger.error(f"Failed to clear cache: {exc}")
        return {
            "status": "error",
            "error": str(exc)
        }
