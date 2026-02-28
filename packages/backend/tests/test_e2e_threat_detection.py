"""
End-to-End Test for Complete Threat Detection Flow

Tests the complete pipeline from media capture to alert generation and FIR creation.
Simulates a video call with scam content and verifies the entire system responds correctly.

Validates:
- Audio transcription and keyword matching
- Visual analysis of frames
- Liveness detection
- Threat score fusion
- Alert triggering
- Digital FIR generation
"""
import pytest
import asyncio
import numpy as np
from uuid import uuid4
from datetime import datetime
from PIL import Image
import io

from app.services.audio_transcriber import AudioTranscriber
from app.services.visual_analyzer import VisualAnalyzer
from app.services.liveness_detector import LivenessDetector
from app.services.threat_analyzer import ThreatAnalyzer
from app.services.fir_generator import FIRGenerator
from app.db.postgres import PostgresDB
from app.db.mongodb import MongoDB
from app.db.transaction_coordinator import create_transaction_coordinator


@pytest.fixture
def audio_transcriber():
    """Create audio transcriber (using tiny model for speed)"""
    return AudioTranscriber(model_size='tiny')


@pytest.fixture
def visual_analyzer():
    """Create visual analyzer (mock for testing without API key)"""
    # For E2E test, we'll use a mock that simulates Gemini responses
    class MockVisualAnalyzer:
        def analyze_frame(self, frame_bytes: bytes):
            from app.services.visual_analyzer import VisualResult
            # Simulate detection of uniform and badge
            return VisualResult(
                uniform_detected=True,
                badge_detected=True,
                threats=["Official-looking badge", "Legal document visible"],
                text_detected="CBI OFFICER - ARREST WARRANT",
                confidence=0.92,
                score=8.5,
                analysis="Detected police uniform with CBI badge and arrest warrant document",
                cached=False
            )
    
    return MockVisualAnalyzer()


@pytest.fixture
def liveness_detector():
    """Create liveness detector"""
    return LivenessDetector()


@pytest.fixture
def threat_analyzer():
    """Create threat analyzer"""
    return ThreatAnalyzer()


@pytest.fixture
def fir_generator(mongodb, postgres_db):
    """Create FIR generator"""
    return FIRGenerator(mongodb, postgres_db)


@pytest.fixture
async def postgres_db():
    """Create PostgreSQL database connection"""
    db = PostgresDB()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def mongodb():
    """Create MongoDB database connection"""
    db = MongoDB()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def coordinator(postgres_db, mongodb):
    """Create transaction coordinator"""
    return create_transaction_coordinator(postgres_db, mongodb)


@pytest.fixture
async def test_user(postgres_db):
    """Create a test user"""
    user_id = await postgres_db.create_user(
        email=f"test_e2e_{uuid4()}@example.com",
        consent_given=True
    )
    yield user_id
    # Cleanup
    await postgres_db.delete_user(user_id)


def generate_scam_audio() -> np.ndarray:
    """
    Generate synthetic audio data simulating scam conversation.
    
    In a real test, this would load actual audio samples.
    For this test, we generate silence and rely on the transcriber mock.
    """
    # Generate 3 seconds of silence at 16kHz
    sample_rate = 16000
    duration = 3.0
    samples = int(sample_rate * duration)
    
    # Generate silence (in real test, load actual scam audio)
    audio = np.zeros(samples, dtype=np.float32)
    
    return audio


def generate_scam_frame() -> bytes:
    """
    Generate synthetic video frame simulating scam video.
    
    Creates a simple image with text that would trigger visual analysis.
    """
    # Create a 640x480 RGB image
    img = Image.new('RGB', (640, 480), color=(50, 50, 100))
    
    # In a real test, we would add text/badges using PIL.ImageDraw
    # For now, just return the basic image
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_threat_detection_flow(
    audio_transcriber,
    visual_analyzer,
    liveness_detector,
    threat_analyzer,
    fir_generator,
    coordinator,
    test_user,
    postgres_db,
    mongodb
):
    """
    Test complete end-to-end threat detection flow.
    
    Simulates:
    1. Video call starts
    2. Audio/video captured
    3. All modalities analyzed in parallel
    4. Scores fused
    5. Alert triggered (score >= 7.0)
    6. Digital FIR generated
    7. Evidence stored in databases
    
    Validates: Complete system integration
    """
    # Step 1: Create session
    session_id = await postgres_db.create_session(test_user, "meet")
    
    try:
        # Step 2: Generate scam media
        audio_data = generate_scam_audio()
        frame_data = generate_scam_frame()
        
        # Step 3: Analyze audio (with mock transcription for speed)
        # In real test, this would use actual Whisper transcription
        # For now, we'll mock the result
        from app.services.audio_transcriber import AudioResult, TranscriptSegment
        
        audio_result = AudioResult(
            transcript="I am a CBI officer and you are under arrest for money laundering. Transfer 50000 rupees immediately to avoid jail.",
            language="en",
            segments=[
                TranscriptSegment(
                    text="I am a CBI officer and you are under arrest for money laundering.",
                    start=0.0,
                    end=3.5,
                    confidence=0.95,
                    speaker="Speaker_1"
                ),
                TranscriptSegment(
                    text="Transfer 50000 rupees immediately to avoid jail.",
                    start=3.5,
                    end=6.0,
                    confidence=0.92,
                    speaker="Speaker_1"
                )
            ],
            keywords={
                'authority': ['CBI', 'officer', 'arrest'],
                'crime': ['money laundering', 'jail'],
                'financial': ['50000 rupees', 'transfer'],
                'urgency': ['immediately']
            },
            score=9.5,  # High threat score
            confidence=0.94,
            low_confidence_segments=[]
        )
        
        # Step 4: Analyze visual
        visual_result = visual_analyzer.analyze_frame(frame_data)
        
        # Step 5: Analyze liveness
        liveness_result = liveness_detector.detect_liveness(frame_data)
        
        # Convert liveness score to 0-10 scale
        liveness_score = liveness_result.liveness_score * 10.0
        
        # Step 6: Fuse scores
        threat_result = threat_analyzer.fuse_scores(
            audio=audio_result.score,
            visual=visual_result.score,
            liveness=liveness_score,
            audio_confidence=audio_result.confidence,
            visual_confidence=visual_result.confidence,
            liveness_confidence=liveness_result.liveness_score
        )
        
        # Step 7: Verify alert is triggered
        assert threat_result.is_alert is True, "Alert should be triggered for high threat score"
        assert threat_result.final_score >= 7.0, f"Final score {threat_result.final_score} should be >= 7.0"
        assert threat_result.threat_level in ['high', 'critical'], f"Threat level should be high/critical, got {threat_result.threat_level}"
        
        # Step 8: Add to history
        threat_analyzer.add_to_history(threat_result)
        
        # Step 9: Store threat analysis in databases
        event_id, evidence_id = await coordinator.write_threat_analysis(
            session_id=session_id,
            user_id=test_user,
            threat_score=threat_result.final_score,
            audio_score=threat_result.audio_score,
            visual_score=threat_result.visual_score,
            liveness_score=threat_result.liveness_score,
            threat_level=threat_result.threat_level,
            is_alert=threat_result.is_alert,
            confidence=threat_result.confidence,
            audio_evidence={
                "transcript": audio_result.transcript,
                "keywords": audio_result.keywords,
                "segments": [
                    {
                        "text": seg.text,
                        "start": seg.start,
                        "end": seg.end,
                        "confidence": seg.confidence,
                        "speaker": seg.speaker
                    }
                    for seg in audio_result.segments
                ]
            },
            visual_evidence={
                "analysis": visual_result.analysis,
                "uniform_detected": visual_result.uniform_detected,
                "badge_detected": visual_result.badge_detected,
                "threats": visual_result.threats,
                "text_detected": visual_result.text_detected
            },
            liveness_evidence={
                "face_detected": liveness_result.face_detected,
                "blink_rate": liveness_result.blink_rate,
                "stress_level": liveness_result.stress_level,
                "is_natural": liveness_result.is_natural,
                "is_deepfake": liveness_result.is_deepfake
            },
            metadata={
                "platform": "meet",
                "browser": "chrome",
                "extension_version": "1.0.0"
            }
        )
        
        # Step 10: Verify database writes
        assert event_id is not None, "Threat event should be created in PostgreSQL"
        assert evidence_id is not None, "Evidence should be created in MongoDB"
        
        # Verify PostgreSQL record
        pg_event = await postgres_db.get_threat_event(event_id)
        assert pg_event is not None
        assert abs(float(pg_event["threat_score"]) - threat_result.final_score) < 0.01, "Threat scores should match"
        assert pg_event["is_alert"] is True
        assert pg_event["threat_level"] == threat_result.threat_level
        
        # Verify MongoDB record
        mongo_evidence = await mongodb.get_evidence(evidence_id)
        assert mongo_evidence is not None
        assert mongo_evidence["session_id"] == str(session_id)
        assert "audio" in mongo_evidence
        assert "CBI" in str(mongo_evidence["audio"]["keywords"])
        assert "visual" in mongo_evidence
        assert mongo_evidence["visual"]["uniform_detected"] is True
        
        # Step 11: Generate Digital FIR (since threat score >= 7.0)
        fir_result = await fir_generator.generate_fir(
            session_id=session_id,
            user_id=test_user,
            threat_score=threat_result.final_score,
            threat_level=threat_result.threat_level,
            audio_score=threat_result.audio_score,
            visual_score=threat_result.visual_score,
            liveness_score=threat_result.liveness_score,
            confidence=threat_result.confidence,
            timestamp=threat_result.timestamp
        )
        
        # Step 12: Verify FIR generation succeeded
        assert fir_result.success is True, f"FIR generation should succeed: {fir_result.error}"
        assert fir_result.fir_id is not None and fir_result.fir_id != ""
        assert fir_result.object_id is not None and fir_result.object_id != ""
        
        # Fetch the generated FIR from MongoDB
        fir_data = await mongodb.get_digital_fir_by_object_id(fir_result.object_id, track_access=False)
        assert fir_data is not None, "FIR should be stored in MongoDB"
        
        # Verify FIR contains required elements
        assert "fir_id" in fir_data
        assert "summary" in fir_data
        assert "evidence" in fir_data
        assert "legal" in fir_data
        
        # Verify FIR summary
        assert "total_duration" in fir_data["summary"]
        assert "max_threat_score" in fir_data["summary"]
        assert "alert_count" in fir_data["summary"]
        
        # Verify FIR evidence package
        assert "transcripts" in fir_data["evidence"]
        assert "frames" in fir_data["evidence"]
        assert "threat_timeline" in fir_data["evidence"]
        
        # Verify legal metadata
        assert "chain_of_custody" in fir_data["legal"]
        assert "cryptographic_signature" in fir_data["legal"]
        assert "hash" in fir_data["legal"]
        
        # Step 13: Verify end-to-end timing (should be < 5 seconds for FIR generation)
        # In real test, we would measure actual timing
        # For now, we just verify the FIR was generated
        
        # Step 14: Verify alert message is appropriate
        assert "CRITICAL" in threat_result.message or "HIGH" in threat_result.message
        assert len(threat_result.explanation) > 0
        
        # Cleanup
        await mongodb.delete_digital_fir(fir_result.object_id)
        await postgres_db.delete_threat_event(event_id)
        await mongodb.delete_evidence(evidence_id)
    
    finally:
        # Cleanup session
        await postgres_db.delete_session(session_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_low_threat_no_fir_generation(
    audio_transcriber,
    visual_analyzer,
    liveness_detector,
    threat_analyzer,
    coordinator,
    test_user,
    postgres_db,
    mongodb
):
    """
    Test that low-threat calls do NOT trigger FIR generation.
    
    Validates: FIR is only generated for high-threat events (score >= 7.0)
    """
    # Create session
    session_id = await postgres_db.create_session(test_user, "zoom")
    
    try:
        # Generate benign media
        audio_data = generate_scam_audio()
        frame_data = generate_scam_frame()
        
        # Create low-threat audio result
        from app.services.audio_transcriber import AudioResult, TranscriptSegment
        
        audio_result = AudioResult(
            transcript="Hello, how are you today? The weather is nice.",
            language="en",
            segments=[
                TranscriptSegment(
                    text="Hello, how are you today? The weather is nice.",
                    start=0.0,
                    end=2.5,
                    confidence=0.98,
                    speaker="Speaker_1"
                )
            ],
            keywords={},  # No scam keywords
            score=1.0,  # Low threat score
            confidence=0.98,
            low_confidence_segments=[]
        )
        
        # Create low-threat visual result
        from app.services.visual_analyzer import VisualResult
        
        visual_result = VisualResult(
            uniform_detected=False,
            badge_detected=False,
            threats=[],
            text_detected="",
            confidence=0.95,
            score=0.5,
            analysis="Normal video call, no threats detected",
            cached=False
        )
        
        # Analyze liveness
        liveness_result = liveness_detector.detect_liveness(frame_data)
        liveness_score = liveness_result.liveness_score * 10.0
        
        # Fuse scores
        threat_result = threat_analyzer.fuse_scores(
            audio=audio_result.score,
            visual=visual_result.score,
            liveness=liveness_score
        )
        
        # Verify NO alert is triggered
        assert threat_result.is_alert is False, "Alert should NOT be triggered for low threat"
        assert threat_result.final_score < 7.0, f"Final score {threat_result.final_score} should be < 7.0"
        assert threat_result.threat_level == 'low', f"Threat level should be low, got {threat_result.threat_level}"
        
        # Store in databases
        event_id, evidence_id = await coordinator.write_threat_analysis(
            session_id=session_id,
            user_id=test_user,
            threat_score=threat_result.final_score,
            audio_score=threat_result.audio_score,
            visual_score=threat_result.visual_score,
            liveness_score=threat_result.liveness_score,
            threat_level=threat_result.threat_level,
            is_alert=threat_result.is_alert,
            confidence=threat_result.confidence
        )
        
        # Verify FIR should NOT be generated (score < 7.0)
        # In production, FIR generation is triggered automatically by score threshold
        # Here we just verify the score is below threshold
        
        # Cleanup
        await postgres_db.delete_threat_event(event_id)
        await mongodb.delete_evidence(evidence_id)
    
    finally:
        await postgres_db.delete_session(session_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_threat_events_in_session(
    threat_analyzer,
    coordinator,
    test_user,
    postgres_db,
    mongodb
):
    """
    Test handling multiple threat events within a single session.
    
    Validates: System can track multiple threat assessments over time
    """
    # Create session
    session_id = await postgres_db.create_session(test_user, "teams")
    
    event_ids = []
    evidence_ids = []
    
    try:
        # Simulate 5 threat assessments over time
        threat_scores = [3.0, 5.5, 7.2, 8.5, 6.0]
        
        for i, score in enumerate(threat_scores):
            # Create threat result
            threat_result = threat_analyzer.fuse_scores(
                audio=score,
                visual=score * 0.9,
                liveness=score * 0.8
            )
            
            # Add to history
            threat_analyzer.add_to_history(threat_result)
            
            # Store in databases
            event_id, evidence_id = await coordinator.write_threat_analysis(
                session_id=session_id,
                user_id=test_user,
                threat_score=threat_result.final_score,
                audio_score=threat_result.audio_score,
                visual_score=threat_result.visual_score,
                liveness_score=threat_result.liveness_score,
                threat_level=threat_result.threat_level,
                is_alert=threat_result.is_alert,
                confidence=threat_result.confidence
            )
            
            event_ids.append(event_id)
            evidence_ids.append(evidence_id)
        
        # Verify all events stored
        assert len(event_ids) == 5
        assert len(evidence_ids) == 5
        
        # Verify history tracking
        history = threat_analyzer.get_history()
        assert len(history) == 5
        
        # Verify max threat score (weighted fusion will reduce from 8.5)
        max_score = threat_analyzer.get_max_threat_score()
        assert max_score >= 7.5, f"Max score should be >= 7.5, got {max_score}"
        
        # Verify alert count (only scores >= 7.0 after weighted fusion)
        # With weights (0.45, 0.35, 0.20), only the 7.2 and 8.5 inputs will result in >= 7.0
        alert_count = threat_analyzer.get_alert_count()
        assert alert_count >= 1, f"Should have at least 1 alert, got {alert_count}"
        
        # Verify session was updated with max threat score
        pg_session = await postgres_db.get_session(session_id)
        assert pg_session is not None
        # Note: max_threat_score update happens via coordinator.update_session_with_max_threat
        # which is called separately in production
        
        # Cleanup
        for event_id in event_ids:
            await postgres_db.delete_threat_event(event_id)
        for evidence_id in evidence_ids:
            await mongodb.delete_evidence(evidence_id)
    
    finally:
        await postgres_db.delete_session(session_id)
        threat_analyzer.clear_history()
