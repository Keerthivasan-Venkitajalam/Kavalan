"""
Property-based test for Digital FIR completeness

Feature: production-ready-browser-extension
Property 18: Digital FIR Completeness

For any generated Digital FIR package, it must contain:
(1) timestamped audio transcripts with speaker identification
(2) video frame snapshots with visual analysis annotations
(3) unified threat scores with confidence intervals
(4) cryptographic signature

Validates: Requirements 12.2, 12.3, 12.4, 12.5
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from uuid import uuid4, UUID
from datetime import datetime
from app.services.fir_generator import FIRGenerator
from app.db.mongodb import MongoDB
from app.db.postgres import PostgresDB


# Fixtures
@pytest.fixture
async def mongodb():
    """Create MongoDB client for testing"""
    db = MongoDB()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def postgres():
    """Create PostgreSQL client for testing"""
    db = PostgresDB()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def fir_generator(mongodb, postgres):
    """Create FIR generator instance"""
    return FIRGenerator(mongodb, postgres)


# Custom strategies for generating test data
@st.composite
def audio_evidence_strategy(draw):
    """Generate audio evidence with speaker identification and word timestamps"""
    num_segments = draw(st.integers(min_value=1, max_value=5))
    num_speakers = draw(st.integers(min_value=1, max_value=3))
    
    segments = []
    current_time = 0.0
    for i in range(num_segments):
        duration = draw(st.floats(min_value=0.5, max_value=3.0))
        speaker = f"Speaker_{draw(st.integers(min_value=1, max_value=num_speakers))}"
        text = draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))))
        
        segments.append({
            "text": text,
            "start": current_time,
            "end": current_time + duration,
            "speaker": speaker
        })
        current_time += duration
    
    # Generate word timestamps
    num_words = draw(st.integers(min_value=3, max_value=20))
    word_timestamps = []
    word_time = 0.0
    for i in range(num_words):
        word_duration = draw(st.floats(min_value=0.1, max_value=0.5))
        word_timestamps.append({
            "word": draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',)))),
            "start": word_time,
            "end": word_time + word_duration
        })
        word_time += word_duration
    
    speaker_labels = [f"Speaker_{i+1}" for i in range(num_speakers)]
    
    return {
        "transcript": draw(st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')))),
        "language": draw(st.sampled_from(["en", "hi", "ta", "te", "ml", "kn"])),
        "detected_keywords": {
            "authority": draw(st.lists(st.text(min_size=3, max_size=10), min_size=0, max_size=3)),
            "coercion": draw(st.lists(st.text(min_size=3, max_size=10), min_size=0, max_size=3)),
            "financial": draw(st.lists(st.text(min_size=3, max_size=10), min_size=0, max_size=3))
        },
        "segments": segments,
        "speaker_labels": speaker_labels,
        "word_timestamps": word_timestamps
    }


@st.composite
def visual_evidence_strategy(draw):
    """Generate visual evidence with annotations"""
    return {
        "frame_url": f"https://storage.example.com/frames/frame_{draw(st.integers(min_value=1, max_value=1000))}.jpg",
        "analysis": draw(st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')))),
        "uniform_detected": draw(st.booleans()),
        "badge_detected": draw(st.booleans()),
        "threats": draw(st.lists(st.text(min_size=3, max_size=15), min_size=0, max_size=5)),
        "text_detected": draw(st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))),
        "confidence": draw(st.floats(min_value=0.0, max_value=1.0))
    }


@st.composite
def liveness_evidence_strategy(draw):
    """Generate liveness detection evidence"""
    return {
        "face_detected": draw(st.booleans()),
        "blink_rate": draw(st.floats(min_value=0.0, max_value=30.0)),
        "stress_level": draw(st.floats(min_value=0.0, max_value=1.0)),
        "is_natural": draw(st.booleans())
    }


# Property-based tests
@pytest.mark.property
@pytest.mark.asyncio
@given(
    threat_score=st.floats(min_value=7.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    audio_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    audio_evidence=audio_evidence_strategy(),
    visual_evidence=visual_evidence_strategy(),
    liveness_evidence=liveness_evidence_strategy()
)
@settings(
    max_examples=100,
    deadline=15000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_fir_contains_all_required_components(
    mongodb,
    postgres,
    fir_generator,
    threat_score: float,
    audio_score: float,
    visual_score: float,
    liveness_score: float,
    confidence: float,
    audio_evidence: dict,
    visual_evidence: dict,
    liveness_evidence: dict
):
    """
    Property: For any generated FIR, it must contain all required components:
    (1) Timestamped audio transcripts with speaker identification (Req 12.2)
    (2) Video frame snapshots with visual analysis annotations (Req 12.3)
    (3) Unified threat scores with confidence intervals (Req 12.4)
    (4) Cryptographic signature (Req 12.5)
    
    This ensures all FIR packages are complete and legally admissible.
    """
    # Create test user and session
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="meet"
    )
    
    try:
        # Insert evidence with all required components
        await mongodb.create_evidence(
            session_id=session_id,
            user_id=user_id,
            audio=audio_evidence,
            visual=visual_evidence,
            liveness=liveness_evidence
        )
        
        # Generate FIR
        result = await fir_generator.generate_fir(
            session_id=session_id,
            user_id=user_id,
            threat_score=threat_score,
            threat_level="high" if threat_score < 8.5 else "critical",
            audio_score=audio_score,
            visual_score=visual_score,
            liveness_score=liveness_score,
            confidence=confidence,
            timestamp=datetime.utcnow()
        )
        
        # Verify FIR was generated successfully
        assert result.success is True, f"FIR generation failed: {result.error}"
        
        # Fetch FIR document
        fir_doc = await mongodb.get_digital_fir(result.fir_id)
        assert fir_doc is not None, "FIR document should exist in MongoDB"
        
        # Verify FIR structure
        assert "evidence" in fir_doc, "FIR must contain 'evidence' section"
        evidence = fir_doc["evidence"]
        
        # ===================================================================
        # Requirement 12.2: Timestamped audio transcripts with speaker identification
        # ===================================================================
        assert "transcripts" in evidence, \
            "FIR evidence must contain 'transcripts' field (Req 12.2)"
        
        assert isinstance(evidence["transcripts"], list), \
            "Transcripts must be a list"
        
        assert len(evidence["transcripts"]) > 0, \
            "FIR must contain at least one transcript (Req 12.2)"
        
        for transcript in evidence["transcripts"]:
            # Verify timestamp
            assert "timestamp" in transcript, \
                "Each transcript must have a timestamp (Req 12.2)"
            
            # Verify transcript text
            assert "text" in transcript, \
                "Each transcript must have text content (Req 12.2)"
            
            # Verify speaker identification
            assert "speaker_labels" in transcript, \
                "Each transcript must have speaker identification (Req 12.2)"
            assert isinstance(transcript["speaker_labels"], list), \
                "Speaker labels must be a list"
            
            # Verify segments with speaker information
            assert "segments" in transcript, \
                "Each transcript must have segments (Req 12.2)"
            assert isinstance(transcript["segments"], list), \
                "Segments must be a list"
            
            # Verify word-level timestamps
            assert "word_timestamps" in transcript, \
                "Each transcript must have word-level timestamps (Req 12.2)"
            assert isinstance(transcript["word_timestamps"], list), \
                "Word timestamps must be a list"
            
            # Verify word timestamp structure
            for word_ts in transcript["word_timestamps"]:
                assert "word" in word_ts, \
                    "Each word timestamp must have 'word' field"
                assert "start" in word_ts, \
                    "Each word timestamp must have 'start' time"
                assert "end" in word_ts, \
                    "Each word timestamp must have 'end' time"
        
        # ===================================================================
        # Requirement 12.3: Video frame snapshots with visual analysis annotations
        # ===================================================================
        assert "frames" in evidence, \
            "FIR evidence must contain 'frames' field (Req 12.3)"
        
        assert isinstance(evidence["frames"], list), \
            "Frames must be a list"
        
        assert len(evidence["frames"]) > 0, \
            "FIR must contain at least one frame snapshot (Req 12.3)"
        
        for frame in evidence["frames"]:
            # Verify timestamp
            assert "timestamp" in frame, \
                "Each frame must have a timestamp (Req 12.3)"
            
            # Verify frame URL/snapshot
            assert "url" in frame, \
                "Each frame must have a URL/snapshot reference (Req 12.3)"
            
            # Verify visual analysis
            assert "analysis" in frame, \
                "Each frame must have visual analysis (Req 12.3)"
            
            # Verify annotations
            assert "annotations" in frame, \
                "Each frame must have annotations (Req 12.3)"
            
            annotations = frame["annotations"]
            assert isinstance(annotations, dict), \
                "Annotations must be a dictionary"
            
            # Verify required annotation fields
            assert "uniform_detected" in annotations, \
                "Annotations must include uniform detection (Req 12.3)"
            assert "badge_detected" in annotations, \
                "Annotations must include badge detection (Req 12.3)"
            assert "text_detected" in annotations, \
                "Annotations must include text detection (Req 12.3)"
            assert "confidence" in annotations, \
                "Annotations must include confidence score (Req 12.3)"
            
            # Verify annotation types
            assert isinstance(annotations["uniform_detected"], bool), \
                "uniform_detected must be boolean"
            assert isinstance(annotations["badge_detected"], bool), \
                "badge_detected must be boolean"
            assert isinstance(annotations["confidence"], (int, float)), \
                "confidence must be numeric"
            assert 0.0 <= annotations["confidence"] <= 1.0, \
                "confidence must be in range [0.0, 1.0]"
        
        # ===================================================================
        # Requirement 12.4: Unified threat scores with confidence intervals
        # ===================================================================
        assert "threat_timeline" in evidence, \
            "FIR evidence must contain 'threat_timeline' field (Req 12.4)"
        
        assert isinstance(evidence["threat_timeline"], list), \
            "Threat timeline must be a list"
        
        assert len(evidence["threat_timeline"]) > 0, \
            "FIR must contain at least one threat timeline entry (Req 12.4)"
        
        for timeline_entry in evidence["threat_timeline"]:
            # Verify timestamp
            assert "timestamp" in timeline_entry, \
                "Each timeline entry must have a timestamp (Req 12.4)"
            
            # Verify unified threat score
            assert "unified_threat_score" in timeline_entry, \
                "Each timeline entry must have unified threat score (Req 12.4)"
            assert isinstance(timeline_entry["unified_threat_score"], (int, float)), \
                "Unified threat score must be numeric"
            assert 0.0 <= timeline_entry["unified_threat_score"] <= 10.0, \
                "Unified threat score must be in range [0.0, 10.0]"
            
            # Verify modality scores breakdown
            assert "modality_scores" in timeline_entry, \
                "Each timeline entry must have modality scores (Req 12.4)"
            
            modality_scores = timeline_entry["modality_scores"]
            assert isinstance(modality_scores, dict), \
                "Modality scores must be a dictionary"
            
            assert "audio" in modality_scores, \
                "Modality scores must include audio score"
            assert "visual" in modality_scores, \
                "Modality scores must include visual score"
            assert "liveness" in modality_scores, \
                "Modality scores must include liveness score"
            
            # Verify confidence
            assert "confidence" in timeline_entry, \
                "Each timeline entry must have confidence (Req 12.4)"
            assert isinstance(timeline_entry["confidence"], (int, float)), \
                "Confidence must be numeric"
            assert 0.0 <= timeline_entry["confidence"] <= 1.0, \
                "Confidence must be in range [0.0, 1.0]"
            
            # Verify confidence interval
            assert "confidence_interval" in timeline_entry, \
                "Each timeline entry must have confidence interval (Req 12.4)"
            
            ci = timeline_entry["confidence_interval"]
            assert isinstance(ci, dict), \
                "Confidence interval must be a dictionary"
            
            assert "lower" in ci, \
                "Confidence interval must have lower bound (Req 12.4)"
            assert "upper" in ci, \
                "Confidence interval must have upper bound (Req 12.4)"
            assert "confidence_level" in ci, \
                "Confidence interval must have confidence level (Req 12.4)"
            
            # Verify confidence interval bounds
            assert isinstance(ci["lower"], (int, float)), \
                "Lower bound must be numeric"
            assert isinstance(ci["upper"], (int, float)), \
                "Upper bound must be numeric"
            assert 0.0 <= ci["lower"] <= 10.0, \
                "Lower bound must be in range [0.0, 10.0]"
            assert 0.0 <= ci["upper"] <= 10.0, \
                "Upper bound must be in range [0.0, 10.0]"
            assert ci["lower"] <= ci["upper"], \
                "Lower bound must be <= upper bound"
            
            # Verify unified score is within confidence interval
            assert ci["lower"] <= timeline_entry["unified_threat_score"] <= ci["upper"], \
                "Unified threat score must be within confidence interval"
        
        # ===================================================================
        # Requirement 12.5: Cryptographic signature
        # ===================================================================
        assert "legal" in fir_doc, \
            "FIR must contain 'legal' section (Req 12.5)"
        
        legal = fir_doc["legal"]
        assert isinstance(legal, dict), \
            "Legal section must be a dictionary"
        
        # Verify cryptographic signature
        assert "cryptographic_signature" in legal, \
            "FIR must contain cryptographic signature (Req 12.5)"
        assert isinstance(legal["cryptographic_signature"], str), \
            "Cryptographic signature must be a string"
        assert len(legal["cryptographic_signature"]) > 0, \
            "Cryptographic signature must not be empty (Req 12.5)"
        
        # Verify signature is valid hex string (SHA-512 = 128 hex chars)
        assert len(legal["cryptographic_signature"]) == 128, \
            "Cryptographic signature should be SHA-512 (128 hex characters)"
        assert all(c in "0123456789abcdef" for c in legal["cryptographic_signature"]), \
            "Cryptographic signature must be valid hexadecimal"
        
        # Verify content hash
        assert "hash" in legal, \
            "FIR must contain content hash (Req 12.5)"
        assert isinstance(legal["hash"], str), \
            "Content hash must be a string"
        assert len(legal["hash"]) > 0, \
            "Content hash must not be empty (Req 12.5)"
        
        # Verify hash is valid hex string (SHA-256 = 64 hex chars)
        assert len(legal["hash"]) == 64, \
            "Content hash should be SHA-256 (64 hex characters)"
        assert all(c in "0123456789abcdef" for c in legal["hash"]), \
            "Content hash must be valid hexadecimal"
        
        # Verify chain of custody
        assert "chain_of_custody" in legal, \
            "FIR must contain chain of custody (Req 12.5)"
        assert isinstance(legal["chain_of_custody"], list), \
            "Chain of custody must be a list"
        assert len(legal["chain_of_custody"]) > 0, \
            "Chain of custody must have at least one entry"
        
        # Cleanup
        await mongodb.delete_digital_fir(result.fir_id)
        await mongodb.delete_session_evidence(session_id)
    
    finally:
        # Cleanup test data
        await postgres.delete_session(session_id)
        await postgres.delete_user(user_id)


@pytest.mark.property
@pytest.mark.asyncio
@given(
    threat_score=st.floats(min_value=7.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    audio_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    visual_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    liveness_score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
@settings(
    max_examples=100,
    deadline=10000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_fir_completeness_with_minimal_evidence(
    mongodb,
    postgres,
    fir_generator,
    threat_score: float,
    audio_score: float,
    visual_score: float,
    liveness_score: float,
    confidence: float
):
    """
    Property: Even with minimal evidence, FIR must still contain all required components.
    
    This tests the edge case where evidence is minimal but FIR structure must be complete.
    """
    # Create test user and session
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="zoom"
    )
    
    try:
        # Insert minimal evidence (but still valid)
        await mongodb.create_evidence(
            session_id=session_id,
            user_id=user_id,
            audio={
                "transcript": "Test",
                "language": "en",
                "detected_keywords": {},
                "segments": [{"text": "Test", "start": 0.0, "end": 1.0, "speaker": "Speaker_1"}],
                "speaker_labels": ["Speaker_1"],
                "word_timestamps": [{"word": "Test", "start": 0.0, "end": 1.0}]
            },
            visual={
                "frame_url": "https://example.com/frame.jpg",
                "analysis": "No threats",
                "uniform_detected": False,
                "badge_detected": False,
                "threats": [],
                "text_detected": "",
                "confidence": 0.5
            },
            liveness={
                "face_detected": True,
                "blink_rate": 15.0,
                "stress_level": 0.5,
                "is_natural": True
            }
        )
        
        # Generate FIR
        result = await fir_generator.generate_fir(
            session_id=session_id,
            user_id=user_id,
            threat_score=threat_score,
            threat_level="high" if threat_score < 8.5 else "critical",
            audio_score=audio_score,
            visual_score=visual_score,
            liveness_score=liveness_score,
            confidence=confidence,
            timestamp=datetime.utcnow()
        )
        
        assert result.success is True
        
        # Fetch FIR and verify all components are present
        fir_doc = await mongodb.get_digital_fir(result.fir_id)
        
        # All four requirements must be satisfied
        assert "evidence" in fir_doc
        assert "transcripts" in fir_doc["evidence"]
        assert len(fir_doc["evidence"]["transcripts"]) > 0
        
        assert "frames" in fir_doc["evidence"]
        assert len(fir_doc["evidence"]["frames"]) > 0
        
        assert "threat_timeline" in fir_doc["evidence"]
        assert len(fir_doc["evidence"]["threat_timeline"]) > 0
        assert "confidence_interval" in fir_doc["evidence"]["threat_timeline"][0]
        
        assert "legal" in fir_doc
        assert "cryptographic_signature" in fir_doc["legal"]
        assert len(fir_doc["legal"]["cryptographic_signature"]) == 128
        
        # Cleanup
        await mongodb.delete_digital_fir(result.fir_id)
        await mongodb.delete_session_evidence(session_id)
    
    finally:
        # Cleanup test data
        await postgres.delete_session(session_id)
        await postgres.delete_user(user_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
