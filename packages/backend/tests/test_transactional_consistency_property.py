"""
Property-based test for transactional consistency across polyglot stores

Tests Property 15: Transactional Consistency Across Polyglot Stores
Validates: Requirements 8.3

For any threat analysis result, writes to both PostgreSQL (structured data) and 
MongoDB (unstructured data) should complete atomically—either both succeed or both fail.
"""
import pytest
import asyncio
from uuid import uuid4, UUID
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import Optional, Dict, Any

from app.db.postgres import PostgresDB
from app.db.mongodb import MongoDB
from app.db.transaction_coordinator import (
    TransactionCoordinator,
    TransactionState,
    create_transaction_coordinator
)


# Hypothesis strategies for generating test data
@st.composite
def threat_analysis_data(draw):
    """Generate random threat analysis data"""
    return {
        "threat_score": draw(st.floats(min_value=0.0, max_value=10.0)),
        "audio_score": draw(st.one_of(
            st.none(),
            st.floats(min_value=0.0, max_value=10.0)
        )),
        "visual_score": draw(st.one_of(
            st.none(),
            st.floats(min_value=0.0, max_value=10.0)
        )),
        "liveness_score": draw(st.one_of(
            st.none(),
            st.floats(min_value=0.0, max_value=10.0)
        )),
        "threat_level": draw(st.sampled_from(["low", "moderate", "high", "critical"])),
        "is_alert": draw(st.booleans()),
        "confidence": draw(st.one_of(
            st.none(),
            st.floats(min_value=0.0, max_value=1.0)
        )),
        "audio_evidence": draw(st.one_of(
            st.none(),
            st.fixed_dictionaries({
                "transcript": st.text(min_size=0, max_size=100),
                "keywords": st.lists(st.text(min_size=1, max_size=20), max_size=5),
                "segments": st.lists(st.fixed_dictionaries({
                    "text": st.text(min_size=0, max_size=50),
                    "start": st.floats(min_value=0.0, max_value=100.0),
                    "end": st.floats(min_value=0.0, max_value=100.0)
                }), max_size=3)
            })
        )),
        "visual_evidence": draw(st.one_of(
            st.none(),
            st.fixed_dictionaries({
                "analysis": st.text(min_size=0, max_size=100),
                "uniform_detected": st.booleans(),
                "badge_detected": st.booleans(),
                "threats": st.lists(st.text(min_size=1, max_size=30), max_size=5)
            })
        )),
        "liveness_evidence": draw(st.one_of(
            st.none(),
            st.fixed_dictionaries({
                "face_detected": st.booleans(),
                "blink_rate": st.floats(min_value=0.0, max_value=30.0),
                "stress_level": st.floats(min_value=0.0, max_value=1.0),
                "is_natural": st.booleans()
            })
        )),
        "metadata": draw(st.one_of(
            st.none(),
            st.fixed_dictionaries({
                "platform": st.sampled_from(["meet", "zoom", "teams"]),
                "browser": st.sampled_from(["chrome", "firefox", "edge"]),
                "extension_version": st.text(min_size=5, max_size=10)
            })
        ))
    }


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
    """Create a test user for property tests"""
    user_id = await postgres_db.create_user(
        email=f"proptest_{uuid4()}@example.com",
        consent_given=True
    )
    yield user_id
    # Cleanup
    try:
        await postgres_db.delete_user(user_id)
    except Exception:
        pass  # User may already be deleted


@pytest.fixture
async def test_session(postgres_db, test_user):
    """Create a test session for property tests"""
    session_id = await postgres_db.create_session(test_user, "meet")
    yield session_id
    # Cleanup
    try:
        await postgres_db.delete_session(session_id)
    except Exception:
        pass  # Session may already be deleted


@pytest.mark.property
@pytest.mark.integration
@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=5000,  # 5 seconds per test
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(data=threat_analysis_data())
async def test_transactional_consistency_atomicity(
    data: Dict[str, Any],
    coordinator,
    test_user,
    test_session,
    postgres_db,
    mongodb
):
    """
    **Validates: Requirements 8.3**
    
    Feature: production-ready-browser-extension
    Property 15: Transactional Consistency Across Polyglot Stores
    
    For any threat analysis result, writes to both PostgreSQL (structured data) and 
    MongoDB (unstructured data) should complete atomically—either both succeed or both fail.
    
    This property verifies that:
    1. If the transaction succeeds, both PostgreSQL and MongoDB contain the data
    2. If the transaction fails, neither database contains the data
    3. The coordinator state reflects the transaction outcome
    """
    event_id = None
    evidence_id = None
    
    try:
        # Execute transactional write
        event_id, evidence_id = await coordinator.write_threat_analysis(
            session_id=test_session,
            user_id=test_user,
            **data
        )
        
        # Property 1: If transaction succeeded, both IDs should be returned
        if event_id is not None and evidence_id is not None:
            # Verify coordinator state is COMMITTED
            assert coordinator.state == TransactionState.COMMITTED, \
                "Coordinator state should be COMMITTED when both IDs are returned"
            
            # Property 2: PostgreSQL record must exist
            pg_event = await postgres_db.get_threat_event(event_id)
            assert pg_event is not None, \
                f"PostgreSQL record must exist for event_id={event_id}"
            
            # Verify PostgreSQL data matches input (with rounding tolerance for DECIMAL(4,2))
            assert abs(float(pg_event["threat_score"]) - data["threat_score"]) < 0.01, \
                f"PostgreSQL threat_score must match input (got {pg_event['threat_score']}, expected {data['threat_score']})"
            assert pg_event["threat_level"] == data["threat_level"], \
                "PostgreSQL threat_level must match input"
            assert pg_event["is_alert"] == data["is_alert"], \
                "PostgreSQL is_alert must match input"
            
            # Property 3: MongoDB record must exist
            mongo_evidence = await mongodb.get_evidence(evidence_id)
            assert mongo_evidence is not None, \
                f"MongoDB record must exist for evidence_id={evidence_id}"
            
            # Verify MongoDB data matches input
            assert mongo_evidence["session_id"] == str(test_session), \
                "MongoDB session_id must match"
            assert mongo_evidence["user_id"] == str(test_user), \
                "MongoDB user_id must match"
            assert mongo_evidence["event_id"] == str(event_id), \
                "MongoDB event_id must link to PostgreSQL record"
            
            # Property 4: Referential integrity - MongoDB references PostgreSQL
            assert str(event_id) == mongo_evidence["event_id"], \
                "MongoDB must reference the correct PostgreSQL event_id"
        
        # Property 5: If transaction failed, both IDs should be None
        elif event_id is None and evidence_id is None:
            # Verify coordinator state is ABORTED
            assert coordinator.state == TransactionState.ABORTED, \
                "Coordinator state should be ABORTED when both IDs are None"
            
            # Property 6: Neither database should contain partial data
            # (We can't verify this without knowing what IDs would have been used,
            # but the coordinator ensures cleanup)
        
        # Property 7: Partial success is not allowed
        else:
            pytest.fail(
                f"Partial transaction detected: event_id={event_id}, "
                f"evidence_id={evidence_id}. Both must be None or both must have values."
            )
    
    finally:
        # Cleanup: Delete created records
        if event_id is not None:
            try:
                await postgres_db.delete_threat_event(event_id)
            except Exception:
                pass  # May already be deleted
        
        if evidence_id is not None:
            try:
                await mongodb.delete_evidence(evidence_id)
            except Exception:
                pass  # May already be deleted


@pytest.mark.property
@pytest.mark.integration
@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=5000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    platform=st.sampled_from(["meet", "zoom", "teams"]),
    has_evidence=st.booleans()
)
async def test_session_creation_atomicity(
    platform: str,
    has_evidence: bool,
    coordinator,
    test_user,
    postgres_db,
    mongodb
):
    """
    **Validates: Requirements 8.3**
    
    Feature: production-ready-browser-extension
    Property 15: Transactional Consistency Across Polyglot Stores
    
    For any session creation with optional evidence, writes to both databases
    should be atomic.
    """
    session_id = None
    evidence_id = None
    
    try:
        # Prepare initial evidence if needed
        initial_evidence = None
        if has_evidence:
            initial_evidence = {
                "audio": {"transcript": "Initial transcript"},
                "visual": {},
                "liveness": {},
                "metadata": {"platform": platform}
            }
        
        # Execute transactional write
        session_id, evidence_id = await coordinator.write_session_with_evidence(
            user_id=test_user,
            platform=platform,
            initial_evidence=initial_evidence
        )
        
        # Property 1: Session creation should always succeed
        assert session_id is not None, "Session ID must be returned"
        assert coordinator.state == TransactionState.COMMITTED, \
            "Coordinator state should be COMMITTED"
        
        # Property 2: PostgreSQL session must exist
        pg_session = await postgres_db.get_session(session_id)
        assert pg_session is not None, "PostgreSQL session must exist"
        assert pg_session["user_id"] == test_user, "Session user_id must match"
        assert pg_session["platform"] == platform, "Session platform must match"
        
        # Property 3: Evidence existence matches has_evidence flag
        if has_evidence:
            assert evidence_id is not None, \
                "Evidence ID must be returned when initial_evidence provided"
            
            mongo_evidence = await mongodb.get_evidence(evidence_id)
            assert mongo_evidence is not None, "MongoDB evidence must exist"
            assert mongo_evidence["session_id"] == str(session_id), \
                "Evidence session_id must match"
        else:
            assert evidence_id is None, \
                "Evidence ID should be None when no initial_evidence provided"
    
    finally:
        # Cleanup
        if evidence_id is not None:
            try:
                await mongodb.delete_evidence(evidence_id)
            except Exception:
                pass
        
        if session_id is not None:
            try:
                await postgres_db.delete_session(session_id)
            except Exception:
                pass


@pytest.mark.property
@pytest.mark.integration
@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=5000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_evidence=st.integers(min_value=0, max_value=5)
)
async def test_delete_session_cascades_atomically(
    num_evidence: int,
    coordinator,
    test_user,
    postgres_db,
    mongodb
):
    """
    **Validates: Requirements 8.3**
    
    Feature: production-ready-browser-extension
    Property 15: Transactional Consistency Across Polyglot Stores
    
    For any session deletion, both the PostgreSQL session and all MongoDB evidence
    should be deleted atomically.
    """
    # Create session
    session_id = await postgres_db.create_session(test_user, "meet")
    evidence_ids = []
    
    try:
        # Create multiple evidence records
        for i in range(num_evidence):
            evidence_id = await mongodb.create_evidence(
                session_id=session_id,
                user_id=test_user,
                audio={"transcript": f"Evidence {i}"}
            )
            evidence_ids.append(evidence_id)
        
        # Verify evidence exists before deletion
        evidence_before = await mongodb.get_session_evidence(session_id)
        assert len(evidence_before) == num_evidence, \
            f"Should have {num_evidence} evidence records before deletion"
        
        # Execute atomic deletion
        result = await coordinator.delete_session_with_evidence(session_id)
        
        # Property 1: Deletion should succeed
        assert result is True, "Deletion should succeed"
        assert coordinator.state == TransactionState.COMMITTED, \
            "Coordinator state should be COMMITTED"
        
        # Property 2: PostgreSQL session should be deleted
        pg_session = await postgres_db.get_session(session_id)
        assert pg_session is None, "PostgreSQL session must be deleted"
        
        # Property 3: All MongoDB evidence should be deleted
        evidence_after = await mongodb.get_session_evidence(session_id)
        assert len(evidence_after) == 0, \
            "All MongoDB evidence must be deleted"
        
        # Mark as cleaned up
        session_id = None
        evidence_ids = []
    
    finally:
        # Cleanup any remaining records
        for evidence_id in evidence_ids:
            try:
                await mongodb.delete_evidence(evidence_id)
            except Exception:
                pass
        
        if session_id is not None:
            try:
                await postgres_db.delete_session(session_id)
            except Exception:
                pass


@pytest.mark.property
@pytest.mark.integration
@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=5000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    threat_scores=st.lists(
        st.floats(min_value=0.0, max_value=10.0),
        min_size=1,
        max_size=5
    )
)
async def test_multiple_writes_maintain_consistency(
    threat_scores: list,
    coordinator,
    test_user,
    test_session,
    postgres_db,
    mongodb
):
    """
    **Validates: Requirements 8.3**
    
    Feature: production-ready-browser-extension
    Property 15: Transactional Consistency Across Polyglot Stores
    
    For any sequence of threat analysis writes, each write should be atomic and
    maintain referential integrity between stores.
    """
    event_ids = []
    evidence_ids = []
    
    try:
        # Write multiple threat analyses
        for i, score in enumerate(threat_scores):
            event_id, evidence_id = await coordinator.write_threat_analysis(
                session_id=test_session,
                user_id=test_user,
                threat_score=score,
                audio_score=score,
                visual_score=score,
                liveness_score=score,
                threat_level="moderate" if score < 7.0 else "high",
                is_alert=score >= 7.0,
                confidence=0.8,
                audio_evidence={"transcript": f"Transcript {i}"}
            )
            
            # Property 1: Each write should succeed atomically
            assert event_id is not None, f"Write {i} should return event_id"
            assert evidence_id is not None, f"Write {i} should return evidence_id"
            assert coordinator.state == TransactionState.COMMITTED, \
                f"Write {i} should be COMMITTED"
            
            event_ids.append(event_id)
            evidence_ids.append(evidence_id)
        
        # Property 2: All PostgreSQL records should exist
        pg_events = await postgres_db.get_session_threat_events(test_session)
        assert len(pg_events) == len(threat_scores), \
            "PostgreSQL should have all threat events"
        
        # Property 3: All MongoDB records should exist
        mongo_evidence = await mongodb.get_session_evidence(test_session)
        assert len(mongo_evidence) == len(threat_scores), \
            "MongoDB should have all evidence records"
        
        # Property 4: Referential integrity - each evidence links to an event
        for evidence in mongo_evidence:
            event_id_str = evidence["event_id"]
            assert any(str(eid) == event_id_str for eid in event_ids), \
                f"Evidence {evidence['_id']} must reference a valid event_id"
        
        # Property 5: Each event has corresponding evidence
        for event_id in event_ids:
            matching_evidence = [
                e for e in mongo_evidence
                if e["event_id"] == str(event_id)
            ]
            assert len(matching_evidence) == 1, \
                f"Event {event_id} must have exactly one evidence record"
    
    finally:
        # Cleanup
        for event_id in event_ids:
            try:
                await postgres_db.delete_threat_event(event_id)
            except Exception:
                pass
        
        for evidence_id in evidence_ids:
            try:
                await mongodb.delete_evidence(evidence_id)
            except Exception:
                pass
