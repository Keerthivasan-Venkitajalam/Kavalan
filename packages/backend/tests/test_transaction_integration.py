"""
Integration tests for transaction coordinator with real databases

Tests transactional writes across PostgreSQL and MongoDB using actual database connections.
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from app.db.postgres import PostgresDB
from app.db.mongodb import MongoDB
from app.db.transaction_coordinator import (
    TransactionCoordinator,
    TransactionState,
    create_transaction_coordinator
)


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
    """Create transaction coordinator with real databases"""
    return create_transaction_coordinator(postgres_db, mongodb)


@pytest.fixture
async def test_user(postgres_db):
    """Create a test user"""
    user_id = await postgres_db.create_user(
        email=f"test_{uuid4()}@example.com",
        consent_given=True
    )
    yield user_id
    # Cleanup
    await postgres_db.delete_user(user_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_write_threat_analysis_atomicity(coordinator, test_user, postgres_db, mongodb):
    """
    Test that threat analysis writes to both databases atomically.
    
    Validates: Requirements 8.3 - Transactional Consistency
    """
    # Create a session first
    session_id = await postgres_db.create_session(test_user, "meet")
    
    try:
        # Write threat analysis using coordinator
        event_id, evidence_id = await coordinator.write_threat_analysis(
            session_id=session_id,
            user_id=test_user,
            threat_score=8.5,
            audio_score=9.0,
            visual_score=8.0,
            liveness_score=7.5,
            threat_level="high",
            is_alert=True,
            confidence=0.92,
            audio_evidence={
                "transcript": "I am a CBI officer",
                "keywords": ["CBI", "officer"],
                "segments": []
            },
            visual_evidence={
                "analysis": "Uniform detected",
                "uniform_detected": True
            },
            liveness_evidence={
                "face_detected": True,
                "blink_rate": 15.0
            },
            metadata={
                "platform": "meet",
                "browser": "chrome"
            }
        )
        
        # Verify both writes succeeded
        assert event_id is not None
        assert evidence_id is not None
        assert coordinator.state == TransactionState.COMMITTED
        
        # Verify PostgreSQL record exists
        pg_event = await postgres_db.get_threat_event(event_id)
        assert pg_event is not None
        assert pg_event["threat_score"] == 8.5
        assert pg_event["audio_score"] == 9.0
        assert pg_event["threat_level"] == "high"
        assert pg_event["is_alert"] is True
        
        # Verify MongoDB record exists
        mongo_evidence = await mongodb.get_evidence(evidence_id)
        assert mongo_evidence is not None
        assert mongo_evidence["session_id"] == str(session_id)
        assert mongo_evidence["user_id"] == str(test_user)
        assert mongo_evidence["event_id"] == str(event_id)
        assert "audio" in mongo_evidence
        assert mongo_evidence["audio"]["transcript"] == "I am a CBI officer"
        assert "visual" in mongo_evidence
        assert mongo_evidence["visual"]["uniform_detected"] is True
        
        # Cleanup
        await postgres_db.delete_threat_event(event_id)
        await mongodb.delete_evidence(evidence_id)
    
    finally:
        # Cleanup session
        await postgres_db.delete_session(session_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_creation_with_evidence(coordinator, test_user, postgres_db, mongodb):
    """
    Test atomic session creation with initial evidence.
    
    Validates: Requirements 8.3 - Transactional Consistency
    """
    # Create session with evidence
    session_id, evidence_id = await coordinator.write_session_with_evidence(
        user_id=test_user,
        platform="zoom",
        initial_evidence={
            "audio": {"transcript": "Initial"},
            "visual": {},
            "liveness": {},
            "metadata": {"platform": "zoom"}
        }
    )
    
    try:
        # Verify both writes succeeded
        assert session_id is not None
        assert evidence_id is not None
        assert coordinator.state == TransactionState.COMMITTED
        
        # Verify PostgreSQL session exists
        pg_session = await postgres_db.get_session(session_id)
        assert pg_session is not None
        assert pg_session["user_id"] == test_user
        assert pg_session["platform"] == "zoom"
        
        # Verify MongoDB evidence exists
        mongo_evidence = await mongodb.get_evidence(evidence_id)
        assert mongo_evidence is not None
        assert mongo_evidence["session_id"] == str(session_id)
        assert mongo_evidence["user_id"] == str(test_user)
        assert mongo_evidence["audio"]["transcript"] == "Initial"
    
    finally:
        # Cleanup
        if evidence_id:
            await mongodb.delete_evidence(evidence_id)
        if session_id:
            await postgres_db.delete_session(session_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_session_cascades_to_evidence(coordinator, test_user, postgres_db, mongodb):
    """
    Test that deleting a session also deletes all related evidence.
    
    Validates: Requirements 8.3 - Transactional Consistency
    """
    # Create session with evidence
    session_id, evidence_id = await coordinator.write_session_with_evidence(
        user_id=test_user,
        platform="teams",
        initial_evidence={
            "audio": {},
            "visual": {},
            "liveness": {}
        }
    )
    
    # Add more evidence
    evidence_id_2 = await mongodb.create_evidence(
        session_id=session_id,
        user_id=test_user,
        audio={"transcript": "Additional evidence"}
    )
    
    # Verify evidence exists
    evidence_count_before = len(await mongodb.get_session_evidence(session_id))
    assert evidence_count_before == 2
    
    # Delete session and evidence atomically
    result = await coordinator.delete_session_with_evidence(session_id)
    assert result is True
    assert coordinator.state == TransactionState.COMMITTED
    
    # Verify PostgreSQL session is deleted
    pg_session = await postgres_db.get_session(session_id)
    assert pg_session is None
    
    # Verify MongoDB evidence is deleted
    evidence_count_after = len(await mongodb.get_session_evidence(session_id))
    assert evidence_count_after == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_session_with_threat_score(coordinator, test_user, postgres_db, mongodb):
    """
    Test updating session with max threat score.
    
    Validates: Requirements 8.3 - Transactional Consistency
    """
    # Create session
    session_id = await postgres_db.create_session(test_user, "meet")
    
    # Create evidence
    evidence_id = await mongodb.create_evidence(
        session_id=session_id,
        user_id=test_user,
        audio={"transcript": "Test"}
    )
    
    try:
        # Update session with threat score
        result = await coordinator.update_session_with_max_threat(
            session_id=session_id,
            threat_score=7.5,
            end_time=datetime.now(),
            duration_seconds=300
        )
        
        assert result is True
        assert coordinator.state == TransactionState.COMMITTED
        
        # Verify PostgreSQL session was updated
        pg_session = await postgres_db.get_session(session_id)
        assert pg_session is not None
        assert pg_session["max_threat_score"] == 7.5
        assert pg_session["duration_seconds"] == 300
        assert pg_session["alert_count"] == 1  # Score >= 7.0 increments alert count
        
        # Update with lower score (should not change max)
        result = await coordinator.update_session_with_max_threat(
            session_id=session_id,
            threat_score=5.0
        )
        
        pg_session = await postgres_db.get_session(session_id)
        assert pg_session["max_threat_score"] == 7.5  # Still the max
        assert pg_session["alert_count"] == 1  # Not incremented (score < 7.0)
        
        # Update with higher score (should update max)
        result = await coordinator.update_session_with_max_threat(
            session_id=session_id,
            threat_score=9.0
        )
        
        pg_session = await postgres_db.get_session(session_id)
        assert pg_session["max_threat_score"] == 9.0  # Updated to new max
        assert pg_session["alert_count"] == 2  # Incremented (score >= 7.0)
    
    finally:
        # Cleanup
        await mongodb.delete_evidence(evidence_id)
        await postgres_db.delete_session(session_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_threat_events_same_session(coordinator, test_user, postgres_db, mongodb):
    """
    Test writing multiple threat events for the same session.
    
    Validates: Requirements 8.3 - Transactional Consistency
    """
    # Create session
    session_id = await postgres_db.create_session(test_user, "meet")
    
    event_ids = []
    evidence_ids = []
    
    try:
        # Write multiple threat events
        for i in range(3):
            event_id, evidence_id = await coordinator.write_threat_analysis(
                session_id=session_id,
                user_id=test_user,
                threat_score=5.0 + i,
                audio_score=5.0 + i,
                visual_score=5.0,
                liveness_score=5.0,
                threat_level="moderate",
                is_alert=False,
                confidence=0.8,
                audio_evidence={"transcript": f"Event {i}"}
            )
            
            assert event_id is not None
            assert evidence_id is not None
            event_ids.append(event_id)
            evidence_ids.append(evidence_id)
        
        # Verify all PostgreSQL events exist
        pg_events = await postgres_db.get_session_threat_events(session_id)
        assert len(pg_events) == 3
        
        # Verify all MongoDB evidence exists
        mongo_evidence = await mongodb.get_session_evidence(session_id)
        assert len(mongo_evidence) == 3
        
        # Verify referential integrity (all evidence has matching event_id)
        for evidence in mongo_evidence:
            event_id_str = evidence["event_id"]
            assert any(str(eid) == event_id_str for eid in event_ids)
    
    finally:
        # Cleanup
        for event_id in event_ids:
            await postgres_db.delete_threat_event(event_id)
        for evidence_id in evidence_ids:
            await mongodb.delete_evidence(evidence_id)
        await postgres_db.delete_session(session_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_referential_integrity_verification(coordinator, test_user, postgres_db, mongodb):
    """
    Test that coordinator verifies referential integrity between stores.
    
    Validates: Requirements 8.4 - Referential Integrity
    """
    # Create session
    session_id = await postgres_db.create_session(test_user, "zoom")
    
    try:
        # Write threat analysis (creates evidence)
        event_id, evidence_id = await coordinator.write_threat_analysis(
            session_id=session_id,
            user_id=test_user,
            threat_score=6.0,
            audio_score=6.0,
            visual_score=6.0,
            liveness_score=6.0,
            threat_level="moderate",
            is_alert=False,
            confidence=0.85
        )
        
        # Verify evidence exists
        mongo_evidence = await mongodb.get_evidence(evidence_id)
        assert mongo_evidence is not None
        assert mongo_evidence["event_id"] == str(event_id)
        
        # Update session (verifies evidence exists)
        result = await coordinator.update_session_with_max_threat(
            session_id=session_id,
            threat_score=6.0
        )
        assert result is True
        
        # Cleanup
        await postgres_db.delete_threat_event(event_id)
        await mongodb.delete_evidence(evidence_id)
    
    finally:
        await postgres_db.delete_session(session_id)
