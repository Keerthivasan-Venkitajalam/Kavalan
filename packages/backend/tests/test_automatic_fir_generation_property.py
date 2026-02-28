"""
Property-based test for automatic Digital FIR generation

Feature: production-ready-browser-extension
Property 17: Automatic Digital FIR Generation

For any confirmed threat event (threat score ≥ 7.0), the system should automatically 
generate a Digital FIR package within 5 seconds.

Validates: Requirements 12.1
"""
import pytest
import asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from app.services.fir_generator import FIRGenerator
from app.db.mongodb import MongoDB
from app.db.postgres import PostgresDB
import time


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


# Property-based tests
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
async def test_fir_generated_for_high_threat_scores(
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
    Property: For any threat score ≥ 7.0, FIR should be automatically generated.
    
    This ensures all confirmed threats have evidence packages created.
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
        # Verify FIR should be generated
        should_generate = await fir_generator.should_generate_fir(
            threat_score=threat_score,
            session_id=session_id
        )
        
        assert should_generate is True, \
            f"FIR should be generated for threat score {threat_score:.2f} >= 7.0"
        
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
        assert result.success is True, \
            f"FIR generation failed: {result.error}"
        assert result.fir_id is not None and result.fir_id != ""
        assert result.object_id is not None and result.object_id != ""
        assert result.session_id == session_id
        assert result.user_id == user_id
        assert result.threat_score == threat_score
        
        # Verify FIR exists in database
        fir_doc = await mongodb.get_digital_fir(result.fir_id)
        assert fir_doc is not None, "FIR should exist in MongoDB"
        
        # Cleanup
        await mongodb.delete_digital_fir(result.fir_id)
    
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
async def test_fir_generation_within_5_seconds(
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
    Property: For any threat score ≥ 7.0, FIR generation must complete within 5 seconds.
    
    This validates the performance requirement for automatic FIR generation.
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
        # Measure generation time
        start_time = time.time()
        
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
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Verify generation completed within 5 seconds
        assert generation_time < 5.0, \
            f"FIR generation took {generation_time:.2f}s, exceeds 5s requirement"
        
        # Verify FIR was generated successfully
        assert result.success is True, \
            f"FIR generation failed: {result.error}"
        
        # Cleanup
        if result.success:
            await mongodb.delete_digital_fir(result.fir_id)
    
    finally:
        # Cleanup test data
        await postgres.delete_session(session_id)
        await postgres.delete_user(user_id)


@pytest.mark.property
@pytest.mark.asyncio
@given(
    threat_score=st.floats(min_value=0.0, max_value=6.99, allow_nan=False, allow_infinity=False)
)
@settings(
    max_examples=100,
    deadline=5000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_fir_not_generated_below_threshold(
    mongodb,
    postgres,
    fir_generator,
    threat_score: float
):
    """
    Property: For any threat score < 7.0, FIR should NOT be automatically generated.
    
    This prevents unnecessary FIR generation for low-threat events.
    """
    # Create test session
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="teams"
    )
    
    try:
        # Verify FIR should NOT be generated
        should_generate = await fir_generator.should_generate_fir(
            threat_score=threat_score,
            session_id=session_id
        )
        
        assert should_generate is False, \
            f"FIR should NOT be generated for threat score {threat_score:.2f} < 7.0"
    
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
async def test_fir_id_format_consistency(
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
    Property: For any generated FIR, the FIR ID should follow the format FIR-{YYYYMMDD}-{prefix}-{hash}.
    
    This ensures consistent FIR identification across all threat events.
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
        
        # Verify FIR ID format
        fir_id = result.fir_id
        assert fir_id.startswith("FIR-"), \
            f"FIR ID should start with 'FIR-', got: {fir_id}"
        
        parts = fir_id.split("-")
        assert len(parts) == 4, \
            f"FIR ID should have 4 parts separated by '-', got: {fir_id}"
        
        # Verify date part (YYYYMMDD)
        date_part = parts[1]
        assert len(date_part) == 8, \
            f"Date part should be 8 characters (YYYYMMDD), got: {date_part}"
        assert date_part.isdigit(), \
            f"Date part should be numeric, got: {date_part}"
        
        # Verify session prefix (8 characters)
        session_prefix = parts[2]
        assert len(session_prefix) == 8, \
            f"Session prefix should be 8 characters, got: {session_prefix}"
        
        # Verify hash (8 characters)
        hash_part = parts[3]
        assert len(hash_part) == 8, \
            f"Hash part should be 8 characters, got: {hash_part}"
        
        # Cleanup
        await mongodb.delete_digital_fir(result.fir_id)
    
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
async def test_fir_not_duplicated_for_same_session(
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
    Property: For any session, only one FIR should be generated regardless of multiple high-threat events.
    
    This prevents duplicate FIR generation for the same session.
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
        # Generate first FIR
        result1 = await fir_generator.generate_fir(
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
        
        assert result1.success is True
        
        # Try to generate second FIR for same session
        should_generate = await fir_generator.should_generate_fir(
            threat_score=threat_score,
            session_id=session_id
        )
        
        # Should return False because FIR already exists
        assert should_generate is False, \
            "FIR should not be generated twice for the same session"
        
        # Cleanup
        await mongodb.delete_digital_fir(result1.fir_id)
    
    finally:
        # Cleanup test data
        await postgres.delete_session(session_id)
        await postgres.delete_user(user_id)


# Unit tests for boundary conditions
@pytest.mark.asyncio
async def test_fir_threshold_boundary_exact(mongodb, postgres, fir_generator):
    """
    Unit test: Test exact threshold boundary (7.0).
    """
    # Create test session
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
        # Test exactly at threshold (7.0)
        should_generate_at = await fir_generator.should_generate_fir(
            threat_score=7.0,
            session_id=session_id
        )
        assert should_generate_at is True, "FIR should be generated at threshold 7.0"
        
        # Test just below threshold (6.99)
        should_generate_below = await fir_generator.should_generate_fir(
            threat_score=6.99,
            session_id=session_id
        )
        assert should_generate_below is False, "FIR should NOT be generated below threshold 6.99"
        
        # Test just above threshold (7.01)
        should_generate_above = await fir_generator.should_generate_fir(
            threat_score=7.01,
            session_id=session_id
        )
        assert should_generate_above is True, "FIR should be generated above threshold 7.01"
    
    finally:
        # Cleanup test data
        await postgres.delete_session(session_id)
        await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_fir_generation_timestamp_accuracy(mongodb, postgres, fir_generator):
    """
    Unit test: Verify FIR generation timestamp is accurate.
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
        # Record timestamp before generation
        before_time = datetime.utcnow()
        
        # Generate FIR
        result = await fir_generator.generate_fir(
            session_id=session_id,
            user_id=user_id,
            threat_score=8.0,
            threat_level="high",
            audio_score=8.0,
            visual_score=7.5,
            liveness_score=8.5,
            confidence=0.9,
            timestamp=datetime.utcnow()
        )
        
        # Record timestamp after generation
        after_time = datetime.utcnow()
        
        assert result.success is True
        
        # Verify generated_at is within the time window
        assert before_time <= result.generated_at <= after_time, \
            "FIR generation timestamp should be within the generation time window"
        
        # Cleanup
        await mongodb.delete_digital_fir(result.fir_id)
    
    finally:
        # Cleanup test data
        await postgres.delete_session(session_id)
        await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_fir_generation_with_maximum_threat_score(mongodb, postgres, fir_generator):
    """
    Unit test: Test FIR generation with maximum threat score (10.0).
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
        # Generate FIR with maximum threat score
        result = await fir_generator.generate_fir(
            session_id=session_id,
            user_id=user_id,
            threat_score=10.0,
            threat_level="critical",
            audio_score=10.0,
            visual_score=10.0,
            liveness_score=10.0,
            confidence=1.0,
            timestamp=datetime.utcnow()
        )
        
        assert result.success is True
        assert result.threat_score == 10.0
        
        # Verify FIR exists
        fir_doc = await mongodb.get_digital_fir(result.fir_id)
        assert fir_doc is not None
        assert fir_doc["summary"]["max_threat_score"] == 10.0
        assert fir_doc["summary"]["threat_level"] == "critical"
        
        # Cleanup
        await mongodb.delete_digital_fir(result.fir_id)
    
    finally:
        # Cleanup test data
        await postgres.delete_session(session_id)
        await postgres.delete_user(user_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
