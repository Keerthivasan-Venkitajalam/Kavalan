"""
Unit tests for automatic FIR generation

Tests that FIR is automatically generated when threat score >= 7.0
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta
from app.services.fir_generator import FIRGenerator, FIRGenerationResult
from app.db.mongodb import MongoDB
from app.db.postgres import PostgresDB


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


@pytest.mark.asyncio
async def test_should_generate_fir_threshold_met(fir_generator):
    """Test that FIR generation is triggered when threat score >= 7.0"""
    session_id = uuid4()
    threat_score = 7.5
    
    # Should return True for score >= 7.0
    should_generate = await fir_generator.should_generate_fir(
        threat_score=threat_score,
        session_id=session_id
    )
    
    assert should_generate is True


@pytest.mark.asyncio
async def test_should_not_generate_fir_threshold_not_met(fir_generator):
    """Test that FIR generation is not triggered when threat score < 7.0"""
    session_id = uuid4()
    threat_score = 6.9
    
    # Should return False for score < 7.0
    should_generate = await fir_generator.should_generate_fir(
        threat_score=threat_score,
        session_id=session_id
    )
    
    assert should_generate is False


@pytest.mark.asyncio
async def test_fir_id_generation(fir_generator):
    """Test that FIR ID is generated in correct format"""
    session_id = uuid4()
    timestamp = datetime.utcnow()
    
    fir_id = fir_generator._generate_fir_id(session_id, timestamp)
    
    # Verify format: FIR-{YYYYMMDD}-{session_prefix}-{hash}
    assert fir_id.startswith("FIR-")
    parts = fir_id.split("-")
    assert len(parts) == 4
    assert parts[0] == "FIR"
    assert len(parts[1]) == 8  # YYYYMMDD
    assert len(parts[2]) == 8  # session prefix
    assert len(parts[3]) == 8  # hash


@pytest.mark.asyncio
async def test_fir_generation_with_mock_data(mongodb, postgres, fir_generator):
    """Test complete FIR generation flow with mock data"""
    # Create test user first
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    # Insert test session into PostgreSQL (it generates its own session_id)
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="meet"
    )
    
    # Insert test evidence into MongoDB
    await mongodb.create_evidence(
        session_id=session_id,
        user_id=user_id,
        audio={
            "transcript": "This is a test scam call",
            "language": "en",
            "detected_keywords": {
                "authority": ["police", "arrest"],
                "coercion": ["immediately"]
            },
            "segments": []
        },
        visual={
            "frame_url": "https://example.com/frame.jpg",
            "analysis": "Uniform detected",
            "uniform_detected": True,
            "badge_detected": True,
            "threats": ["uniform"],
            "text_detected": "",
            "confidence": 0.85
        },
        liveness={
            "face_detected": True,
            "blink_rate": 15.0,
            "stress_level": 0.8,
            "is_natural": True
        }
    )
    
    # Generate FIR
    result = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=8.5,
        threat_level="critical",
        audio_score=9.0,
        visual_score=8.0,
        liveness_score=8.0,
        confidence=0.9,
        timestamp=datetime.utcnow()
    )
    
    # Verify result
    assert result.success is True
    assert result.fir_id.startswith("FIR-")
    assert result.object_id is not None
    assert result.session_id == session_id
    assert result.user_id == user_id
    assert result.threat_score == 8.5
    assert result.error is None
    
    # Verify FIR was stored in MongoDB
    fir_doc = await mongodb.get_digital_fir(result.fir_id)
    assert fir_doc is not None
    assert fir_doc["fir_id"] == result.fir_id
    assert fir_doc["session_id"] == str(session_id)
    assert fir_doc["user_id"] == str(user_id)
    
    # Verify summary section
    assert "summary" in fir_doc
    assert fir_doc["summary"]["max_threat_score"] == 8.5
    assert fir_doc["summary"]["threat_level"] == "critical"
    assert "threat_categories" in fir_doc["summary"]
    
    # Verify evidence package
    assert "evidence" in fir_doc
    assert "transcripts" in fir_doc["evidence"]
    assert "frames" in fir_doc["evidence"]
    assert "threat_timeline" in fir_doc["evidence"]
    
    # Verify legal metadata
    assert "legal" in fir_doc
    assert "chain_of_custody" in fir_doc["legal"]
    assert "cryptographic_signature" in fir_doc["legal"]
    assert "hash" in fir_doc["legal"]
    assert "retention_until" in fir_doc["legal"]
    
    # Verify chain of custody
    assert len(fir_doc["legal"]["chain_of_custody"]) > 0
    assert fir_doc["legal"]["chain_of_custody"][0]["action"] == "FIR_CREATED"
    
    # Cleanup
    await mongodb.delete_digital_fir(result.fir_id)
    await mongodb.delete_session_evidence(session_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_fir_generation_timing(mongodb, postgres, fir_generator):
    """Test that FIR generation completes within 5 seconds"""
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
    
    # Measure generation time
    start_time = datetime.utcnow()
    
    result = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=7.5,
        threat_level="high",
        audio_score=7.0,
        visual_score=7.5,
        liveness_score=8.0,
        confidence=0.85,
        timestamp=datetime.utcnow()
    )
    
    end_time = datetime.utcnow()
    generation_time = (end_time - start_time).total_seconds()
    
    # Verify generation completed within 5 seconds
    assert generation_time < 5.0, f"FIR generation took {generation_time:.2f}s, exceeds 5s requirement"
    assert result.success is True
    
    # Cleanup
    if result.success:
        await mongodb.delete_digital_fir(result.fir_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_fir_not_generated_twice_for_same_session(mongodb, postgres, fir_generator):
    """Test that FIR is not generated twice for the same session"""
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="meet"
    )
    
    # Generate first FIR
    result1 = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=7.5,
        threat_level="high",
        audio_score=7.0,
        visual_score=7.5,
        liveness_score=8.0,
        confidence=0.85,
        timestamp=datetime.utcnow()
    )
    
    assert result1.success is True
    
    # Try to generate second FIR for same session
    should_generate = await fir_generator.should_generate_fir(
        threat_score=8.0,
        session_id=session_id
    )
    
    # Should return False because FIR already exists
    assert should_generate is False
    
    # Cleanup
    await mongodb.delete_digital_fir(result1.fir_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_fir_summary_includes_all_required_fields(mongodb, postgres, fir_generator):
    """Test that FIR summary includes all required fields"""
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="zoom"
    )
    
    result = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=8.0,
        threat_level="high",
        audio_score=8.5,
        visual_score=7.5,
        liveness_score=8.0,
        confidence=0.88,
        timestamp=datetime.utcnow()
    )
    
    assert result.success is True
    
    # Fetch FIR and verify summary
    fir_doc = await mongodb.get_digital_fir(result.fir_id)
    summary = fir_doc["summary"]
    
    # Required fields per design document
    assert "total_duration" in summary
    assert "max_threat_score" in summary
    assert "alert_count" in summary
    assert "threat_categories" in summary
    assert "threat_level" in summary
    assert "platform" in summary
    
    assert summary["max_threat_score"] == 8.0
    assert summary["threat_level"] == "high"
    assert summary["platform"] == "zoom"
    
    # Cleanup
    await mongodb.delete_digital_fir(result.fir_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_fir_content_assembly_completeness(mongodb, postgres, fir_generator):
    """
    Test that FIR content assembly includes all required components:
    - Timestamped audio transcripts with speaker identification (Req 12.2)
    - Video frame snapshots with visual analysis annotations (Req 12.3)
    - Unified threat scores with confidence intervals (Req 12.4)
    - Cryptographic signature for tamper-proofing (Req 12.5)
    """
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="meet"
    )
    
    # Insert evidence with speaker identification and word timestamps
    await mongodb.create_evidence(
        session_id=session_id,
        user_id=user_id,
        audio={
            "transcript": "I am a police officer. You must transfer money immediately.",
            "language": "en",
            "detected_keywords": {
                "authority": ["police", "officer"],
                "financial": ["transfer", "money"],
                "urgency": ["immediately"]
            },
            "segments": [
                {"text": "I am a police officer", "start": 0.0, "end": 2.5, "speaker": "Speaker_1"},
                {"text": "You must transfer money immediately", "start": 2.5, "end": 5.0, "speaker": "Speaker_1"}
            ],
            "speaker_labels": ["Speaker_1"],
            "word_timestamps": [
                {"word": "I", "start": 0.0, "end": 0.1},
                {"word": "am", "start": 0.1, "end": 0.2},
                {"word": "a", "start": 0.2, "end": 0.3},
                {"word": "police", "start": 0.3, "end": 0.8},
                {"word": "officer", "start": 0.8, "end": 1.3}
            ]
        },
        visual={
            "frame_url": "https://storage.example.com/frames/frame_001.jpg",
            "analysis": "Police uniform detected with badge visible",
            "uniform_detected": True,
            "badge_detected": True,
            "threats": ["uniform", "badge"],
            "text_detected": "POLICE",
            "confidence": 0.92
        },
        liveness={
            "face_detected": True,
            "blink_rate": 12.0,
            "stress_level": 0.75,
            "is_natural": True
        }
    )
    
    # Generate FIR
    result = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=8.7,
        threat_level="critical",
        audio_score=9.2,
        visual_score=8.5,
        liveness_score=8.0,
        confidence=0.91,
        timestamp=datetime.utcnow()
    )
    
    assert result.success is True
    
    # Fetch FIR and verify content assembly
    fir_doc = await mongodb.get_digital_fir(result.fir_id)
    evidence = fir_doc["evidence"]
    
    # Requirement 12.2: Timestamped audio transcripts with speaker identification
    assert "transcripts" in evidence
    assert len(evidence["transcripts"]) > 0
    
    transcript = evidence["transcripts"][0]
    assert "timestamp" in transcript
    assert "text" in transcript
    assert "language" in transcript
    assert "segments" in transcript
    assert "speaker_labels" in transcript  # Speaker identification
    assert "word_timestamps" in transcript  # Word-level timestamps
    
    # Verify speaker labels are present
    assert len(transcript["speaker_labels"]) > 0
    assert "Speaker_1" in transcript["speaker_labels"]
    
    # Verify word timestamps are present
    assert len(transcript["word_timestamps"]) > 0
    assert "word" in transcript["word_timestamps"][0]
    assert "start" in transcript["word_timestamps"][0]
    assert "end" in transcript["word_timestamps"][0]
    
    # Requirement 12.3: Video frame snapshots with visual analysis annotations
    assert "frames" in evidence
    assert len(evidence["frames"]) > 0
    
    frame = evidence["frames"][0]
    assert "timestamp" in frame
    assert "url" in frame
    assert "analysis" in frame
    assert "threats" in frame
    assert "annotations" in frame  # Visual analysis annotations
    
    # Verify annotations include all detection results
    annotations = frame["annotations"]
    assert "uniform_detected" in annotations
    assert "badge_detected" in annotations
    assert "text_detected" in annotations
    assert "confidence" in annotations
    assert annotations["uniform_detected"] is True
    assert annotations["badge_detected"] is True
    assert annotations["text_detected"] == "POLICE"
    assert annotations["confidence"] == 0.92
    
    # Requirement 12.4: Unified threat scores with confidence intervals
    assert "threat_timeline" in evidence
    assert len(evidence["threat_timeline"]) > 0
    
    timeline_entry = evidence["threat_timeline"][0]
    assert "unified_threat_score" in timeline_entry
    assert "modality_scores" in timeline_entry
    assert "confidence" in timeline_entry
    assert "confidence_interval" in timeline_entry  # Confidence intervals
    
    # Verify modality scores breakdown
    modality_scores = timeline_entry["modality_scores"]
    assert "audio" in modality_scores
    assert "visual" in modality_scores
    assert "liveness" in modality_scores
    assert modality_scores["audio"] == 9.2
    assert modality_scores["visual"] == 8.5
    assert modality_scores["liveness"] == 8.0
    
    # Verify confidence interval structure
    ci = timeline_entry["confidence_interval"]
    assert "lower" in ci
    assert "upper" in ci
    assert "confidence_level" in ci
    assert ci["confidence_level"] == 0.95
    assert ci["lower"] <= timeline_entry["unified_threat_score"] <= ci["upper"]
    assert 0.0 <= ci["lower"] <= 10.0
    assert 0.0 <= ci["upper"] <= 10.0
    
    # Requirement 12.5: Cryptographic signature for tamper-proofing
    legal = fir_doc["legal"]
    assert "cryptographic_signature" in legal
    assert "hash" in legal
    
    # Verify signature and hash are non-empty
    assert len(legal["cryptographic_signature"]) > 0
    assert len(legal["hash"]) > 0
    
    # Verify hash is SHA-256 (64 hex characters)
    assert len(legal["hash"]) == 64
    assert all(c in "0123456789abcdef" for c in legal["hash"])
    
    # Verify signature is SHA-512 (128 hex characters)
    assert len(legal["cryptographic_signature"]) == 128
    assert all(c in "0123456789abcdef" for c in legal["cryptographic_signature"])
    
    # Cleanup
    await mongodb.delete_digital_fir(result.fir_id)
    await mongodb.delete_session_evidence(session_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
