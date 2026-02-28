"""
Audio transcription and analysis tasks
"""
from app.celery_app import celery_app
from app.services.audio_transcriber import AudioTranscriber
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import numpy as np
import base64
import logging
from app.utils.tracing import add_span_attributes, add_span_event, TracedOperation

logger = logging.getLogger(__name__)

# Initialize audio transcriber (singleton)
_audio_transcriber = None

def get_audio_transcriber():
    """Get or create audio transcriber instance"""
    global _audio_transcriber
    if _audio_transcriber is None:
        _audio_transcriber = AudioTranscriber(model_size='medium')
    return _audio_transcriber


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,  # Base delay in seconds
    autoretry_for=(Exception,),  # Auto-retry on any exception
    retry_backoff=True,  # Enable exponential backoff
    retry_backoff_max=600,  # Max backoff time (10 minutes)
    retry_jitter=True  # Add randomness to prevent thundering herd
)
def analyze_audio(
    self,
    encrypted_data: str,
    iv: str,
    session_id: str,
    timestamp: float,
    sample_rate: int,
    duration: float,
    user_id: str,
    encryption_key: str = None
):
    """
    Transcribe audio and detect scam keywords.
    
    Args:
        encrypted_data: Base64-encoded encrypted audio data
        iv: Base64-encoded initialization vector
        session_id: Session identifier
        timestamp: Audio chunk timestamp
        sample_rate: Audio sample rate in Hz
        duration: Audio duration in seconds
        user_id: User identifier
        encryption_key: Base64-encoded encryption key (optional, uses default if not provided)
    
    Returns:
        Dictionary with transcript, keywords, score, and metadata
    
    Retry logic:
    - Max 3 retry attempts
    - Exponential backoff: 2^n seconds (2s, 4s, 8s)
    - Jitter added to prevent thundering herd
    """
    try:
        logger.info(f"Audio analysis task started for session {session_id}")
        
        # Add tracing attributes
        add_span_attributes({
            "session_id": session_id,
            "user_id": user_id,
            "sample_rate": sample_rate,
            "duration": duration,
            "timestamp": timestamp,
            "task_id": self.request.id,
            "modality": "audio"
        })
        
        # Step 1: Decrypt audio data
        try:
            with TracedOperation("decrypt_audio", {"data_size": len(encrypted_data)}):
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
                audio_bytes = aesgcm.decrypt(iv_bytes, encrypted_bytes, None)
                
                # Convert bytes to numpy array (assuming float32 PCM)
                audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
                
                logger.info(f"Decrypted audio: {len(audio_array)} samples at {sample_rate}Hz")
                add_span_event("audio_decrypted", {
                    "samples": len(audio_array),
                    "sample_rate": sample_rate
                })
        
        except Exception as e:
            logger.error(f"Audio decryption failed: {e}")
            add_span_event("decryption_failed", {"error": str(e)})
            raise ValueError(f"Failed to decrypt audio data: {e}")
        
        # Step 2: Get transcriber instance
        with TracedOperation("get_transcriber"):
            transcriber = get_audio_transcriber()
        
        # Step 3: Analyze audio
        with TracedOperation("transcribe_and_analyze", {
            "audio_duration": duration,
            "sample_rate": sample_rate
        }):
            result = transcriber.analyze(
                audio=audio_array,
                language=None,  # Auto-detect language
                sample_rate=sample_rate
            )
        
        logger.info(
            f"Audio analysis complete: "
            f"language={result.language}, "
            f"score={result.score:.2f}, "
            f"confidence={result.confidence:.2f}"
        )
        
        # Add result attributes to span
        add_span_attributes({
            "language": result.language,
            "score": result.score,
            "confidence": result.confidence,
            "keywords_found": len(result.keywords),
            "segments_count": len(result.segments)
        })
        
        add_span_event("analysis_complete", {
            "language": result.language,
            "score": result.score,
            "keywords": len(result.keywords)
        })
        
        # Step 4: Return results
        return {
            "session_id": session_id,
            "timestamp": timestamp,
            "transcript": result.transcript,
            "language": result.language,
            "keywords": result.keywords,
            "score": result.score,
            "confidence": result.confidence,
            "segments": [
                {
                    "text": seg.text,
                    "start": seg.start,
                    "end": seg.end,
                    "confidence": seg.confidence,
                    "speaker": seg.speaker,
                    "words": seg.words
                }
                for seg in result.segments
            ],
            "low_confidence_segments": result.low_confidence_segments,
            "status": "success"
        }
    
    except Exception as exc:
        logger.error(f"Audio analysis task failed (attempt {self.request.retries + 1}/3): {exc}")
        # Exponential backoff: 2^n seconds
        countdown = 2 ** self.request.retries
        logger.info(f"Retrying in {countdown} seconds...")
        raise self.retry(exc=exc, countdown=countdown)
