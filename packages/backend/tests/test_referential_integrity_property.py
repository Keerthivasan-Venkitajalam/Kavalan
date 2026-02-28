"""
Property-based test for referential integrity between PostgreSQL and MongoDB

Tests Property 16: Referential Integrity Between Stores
Validates: Requirements 8.4

For any session record in PostgreSQL, all referenced evidence documents in MongoDB 
(by session_id) should exist and be accessible.
"""
import pytest
import asyncio
from uuid import uuid4, UUID
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import List, Dict, Any

from app.db.postgres import PostgresDB
from app.db.mongodb import MongoDB
from app.db.transaction_coordinator import create_transaction_coordinator
from app.db.referential_integrity import (
    ReferentialIntegrityChecker,
    create_integrity_checker,
    IntegrityViolation
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
async def integrity_checker(postgres_db, mongodb):
    """Create referential integrity checker"""
    return create_integrity_checker(postgres_db, mongodb)


@pytest.fixture
async def coordinator(postgres_db, mongodb):
    """Create transaction coordinator"""
    return create_transaction_coordinator(postgres_db, mongodb)


@pytest.fixture
async def test_user(postgres_db):
    """Create a test user for property tests"""
    user_id = await postgres_db.create_user(
        email=f"integrity_test_{uuid4()}@example.com",
        consent_given=True
    )
    yield user_id
    # Cleanup
    try:
        await postgres_db.delete_user(user_id)
    except Exception:
        pass


@pytest.mark.property
@pytest.mark.integration
@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=5000,  # 5 seconds per test
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    platform=st.sampled_from(["meet", "zoom", "teams"]),
    num_evidence=st.integers(min_value=0, max_value=10)
)
async def test_session_evidence_referential_integrity(
    platform: str,
    num_evidence: int,
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """
    **Validates: Requirements 8.4**
    
    Feature: production-ready-browser-extension
    Property 16: Referential Integrity Between Stores
    
    For any session record in PostgreSQL, all referenced evidence documents in MongoDB 
    (by session_id) should exist and be accessible.
    
    This property verifies that:
    1. All MongoDB evidence records reference an existing PostgreSQL session
    2. session_id values are consistent between stores
    3. No dangling references exist
    """
    session_id = None
    evidence_ids = []
    
    try:
        # Create PostgreSQL session
        session_id = await postgres_db.create_session(test_user, platform)
        
        # Create MongoDB evidence records
        for i in range(num_evidence):
            evidence_id = await mongodb.create_evidence(
                session_id=session_id,
                user_id=test_user,
                audio={"transcript": f"Test transcript {i}"},
                visual={"analysis": f"Test analysis {i}"},
                liveness={"face_detected": True, "blink_rate": 15.0},
                metadata={"platform": platform, "test_index": i}
            )
            evidence_ids.append(evidence_id)
        
        # Property 1: Session must exist in PostgreSQL
        pg_session = await postgres_db.get_session(session_id)
        assert pg_session is not None, \
            f"PostgreSQL session must exist for session_id={session_id}"
        assert pg_session["user_id"] == test_user, \
            "Session user_id must match"
        assert pg_session["platform"] == platform, \
            "Session platform must match"
        
        # Property 2: All evidence records must reference the correct session
        mongo_evidence = await mongodb.get_session_evidence(session_id)
        assert len(mongo_evidence) == num_evidence, \
            f"MongoDB should have {num_evidence} evidence records"
        
        for evidence in mongo_evidence:
            assert evidence["session_id"] == str(session_id), \
                f"Evidence session_id must match: expected {session_id}, got {evidence['session_id']}"
            assert evidence["user_id"] == str(test_user), \
                "Evidence user_id must match"
        
        # Property 3: Referential integrity check should pass
        violations = await integrity_checker.check_session_id_consistency(session_id)
        assert len(violations) == 0, \
            f"No referential integrity violations should exist. Found: {violations}"
        
        # Property 4: Verify method should return True
        is_valid = await integrity_checker.verify_referential_integrity(session_id)
        assert is_valid is True, \
            "Referential integrity verification should pass"
        
        # Property 5: Evidence session reference check should find no violations
        session_ref_violations = await integrity_checker.check_evidence_session_references(
            limit=num_evidence + 10
        )
        # Filter to only violations for our session
        our_violations = [
            v for v in session_ref_violations
            if v.session_id == session_id
        ]
        assert len(our_violations) == 0, \
            f"No session reference violations should exist for our session. Found: {our_violations}"
    
    finally:
        # Cleanup
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
    num_events=st.integers(min_value=1, max_value=5)
)
async def test_evidence_event_referential_integrity(
    num_events: int,
    postgres_db,
    mongodb,
    integrity_checker,
    coordinator,
    test_user
):
    """
    **Validates: Requirements 8.4**
    
    Feature: production-ready-browser-extension
    Property 16: Referential Integrity Between Stores
    
    For any MongoDB evidence record with event_id, the referenced PostgreSQL 
    threat event must exist.
    """
    session_id = None
    event_ids = []
    evidence_ids = []
    
    try:
        # Create session
        session_id = await postgres_db.create_session(test_user, "meet")
        
        # Create threat events with evidence using coordinator
        for i in range(num_events):
            event_id, evidence_id = await coordinator.write_threat_analysis(
                session_id=session_id,
                user_id=test_user,
                threat_score=5.0 + i,
                audio_score=5.0,
                visual_score=5.0,
                liveness_score=5.0,
                threat_level="moderate",
                is_alert=False,
                confidence=0.8,
                audio_evidence={"transcript": f"Event {i}"}
            )
            
            assert event_id is not None, f"Event {i} should be created"
            assert evidence_id is not None, f"Evidence {i} should be created"
            
            event_ids.append(event_id)
            evidence_ids.append(evidence_id)
        
        # Property 1: All events must exist in PostgreSQL
        for event_id in event_ids:
            pg_event = await postgres_db.get_threat_event(event_id)
            assert pg_event is not None, \
                f"PostgreSQL event must exist for event_id={event_id}"
            assert pg_event["session_id"] == session_id, \
                "Event session_id must match"
        
        # Property 2: All evidence must reference valid events
        for evidence_id in evidence_ids:
            mongo_evidence = await mongodb.get_evidence(evidence_id)
            assert mongo_evidence is not None, \
                f"MongoDB evidence must exist for evidence_id={evidence_id}"
            
            event_id_str = mongo_evidence.get("event_id")
            assert event_id_str is not None, \
                "Evidence must have event_id field"
            
            event_id = UUID(event_id_str)
            assert event_id in event_ids, \
                f"Evidence must reference a valid event_id: {event_id}"
        
        # Property 3: Event reference check should find no violations
        event_ref_violations = await integrity_checker.check_evidence_event_references(
            limit=num_events + 10
        )
        # Filter to only violations for our evidence
        our_violations = [
            v for v in event_ref_violations
            if v.mongodb_id in evidence_ids
        ]
        assert len(our_violations) == 0, \
            f"No event reference violations should exist. Found: {our_violations}"
        
        # Property 4: Session consistency check should pass
        violations = await integrity_checker.check_session_id_consistency(session_id)
        assert len(violations) == 0, \
            f"No referential integrity violations should exist. Found: {violations}"
    
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
    create_orphan=st.booleans()
)
async def test_orphaned_evidence_detection(
    create_orphan: bool,
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """
    **Validates: Requirements 8.4**
    
    Feature: production-ready-browser-extension
    Property 16: Referential Integrity Between Stores
    
    The integrity checker should detect orphaned evidence records that reference
    non-existent sessions.
    """
    session_id = None
    evidence_id = None
    
    try:
        if create_orphan:
            # Create orphaned evidence (no PostgreSQL session)
            fake_session_id = uuid4()
            evidence_id = await mongodb.create_evidence(
                session_id=fake_session_id,
                user_id=test_user,
                audio={"transcript": "Orphaned evidence"}
            )
            
            # Property 1: Orphaned evidence should be detected
            violations = await integrity_checker.check_evidence_session_references(
                limit=100
            )
            
            # Find violations for our fake session
            orphan_violations = [
                v for v in violations
                if v.session_id == fake_session_id or
                (v.details and v.details.get("session_id") == str(fake_session_id))
            ]
            
            assert len(orphan_violations) > 0, \
                "Orphaned evidence should be detected as a violation"
            
            assert any(v.violation_type == "dangling_session_reference" for v in orphan_violations), \
                "Violation should be classified as dangling_session_reference"
            
            # Property 2: Orphaned evidence check should find it
            orphaned_violations = await integrity_checker.check_orphaned_evidence(limit=100)
            orphan_found = any(
                v.session_id == fake_session_id or
                (v.details and v.details.get("session_id") == str(fake_session_id))
                for v in orphaned_violations
            )
            assert orphan_found, \
                "Orphaned evidence should be found by check_orphaned_evidence"
        
        else:
            # Create valid evidence with proper session
            session_id = await postgres_db.create_session(test_user, "meet")
            evidence_id = await mongodb.create_evidence(
                session_id=session_id,
                user_id=test_user,
                audio={"transcript": "Valid evidence"}
            )
            
            # Property 3: Valid evidence should not be flagged as orphaned
            violations = await integrity_checker.check_evidence_session_references(
                limit=100
            )
            
            # Filter to only violations for our session
            our_violations = [
                v for v in violations
                if v.session_id == session_id
            ]
            
            assert len(our_violations) == 0, \
                "Valid evidence should not be flagged as orphaned"
            
            # Property 4: Referential integrity should pass
            is_valid = await integrity_checker.verify_referential_integrity(session_id)
            assert is_valid is True, \
                "Valid evidence should pass referential integrity check"
    
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
    num_sessions=st.integers(min_value=1, max_value=3),
    evidence_per_session=st.integers(min_value=0, max_value=3)
)
async def test_multiple_sessions_referential_integrity(
    num_sessions: int,
    evidence_per_session: int,
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """
    **Validates: Requirements 8.4**
    
    Feature: production-ready-browser-extension
    Property 16: Referential Integrity Between Stores
    
    For any number of sessions with evidence, referential integrity should be
    maintained across all sessions.
    """
    session_ids = []
    all_evidence_ids = []
    
    try:
        # Create multiple sessions with evidence
        for i in range(num_sessions):
            session_id = await postgres_db.create_session(test_user, "meet")
            session_ids.append(session_id)
            
            # Create evidence for this session
            for j in range(evidence_per_session):
                evidence_id = await mongodb.create_evidence(
                    session_id=session_id,
                    user_id=test_user,
                    audio={"transcript": f"Session {i}, Evidence {j}"}
                )
                all_evidence_ids.append(evidence_id)
        
        # Property 1: Each session should maintain referential integrity
        for session_id in session_ids:
            violations = await integrity_checker.check_session_id_consistency(session_id)
            assert len(violations) == 0, \
                f"Session {session_id} should have no violations. Found: {violations}"
            
            is_valid = await integrity_checker.verify_referential_integrity(session_id)
            assert is_valid is True, \
                f"Session {session_id} should pass referential integrity check"
        
        # Property 2: All evidence should reference valid sessions
        for session_id in session_ids:
            mongo_evidence = await mongodb.get_session_evidence(session_id)
            assert len(mongo_evidence) == evidence_per_session, \
                f"Session {session_id} should have {evidence_per_session} evidence records"
            
            for evidence in mongo_evidence:
                assert evidence["session_id"] == str(session_id), \
                    "Evidence session_id must match"
        
        # Property 3: Global integrity check should find no violations
        session_ref_violations = await integrity_checker.check_evidence_session_references(
            limit=num_sessions * evidence_per_session + 10
        )
        
        # Filter to only violations for our sessions
        our_violations = [
            v for v in session_ref_violations
            if v.session_id in session_ids
        ]
        
        assert len(our_violations) == 0, \
            f"No violations should exist for our sessions. Found: {our_violations}"
        
        # Property 4: Total evidence count should match
        total_evidence = 0
        for session_id in session_ids:
            evidence = await mongodb.get_session_evidence(session_id)
            total_evidence += len(evidence)
        
        assert total_evidence == num_sessions * evidence_per_session, \
            f"Total evidence count should be {num_sessions * evidence_per_session}"
    
    finally:
        # Cleanup
        for evidence_id in all_evidence_ids:
            try:
                await mongodb.delete_evidence(evidence_id)
            except Exception:
                pass
        
        for session_id in session_ids:
            try:
                await postgres_db.delete_session(session_id)
            except Exception:
                pass


@pytest.mark.property
@pytest.mark.integration
@pytest.mark.asyncio
@settings(
    max_examples=30,
    deadline=10000,  # 10 seconds for comprehensive check
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_valid_sessions=st.integers(min_value=1, max_value=2),
    num_orphaned=st.integers(min_value=0, max_value=2)
)
async def test_integrity_report_generation(
    num_valid_sessions: int,
    num_orphaned: int,
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """
    **Validates: Requirements 8.4**
    
    Feature: production-ready-browser-extension
    Property 16: Referential Integrity Between Stores
    
    The integrity report should accurately identify all violations across the system.
    """
    session_ids = []
    evidence_ids = []
    orphaned_evidence_ids = []
    
    try:
        # Create valid sessions with evidence
        for i in range(num_valid_sessions):
            session_id = await postgres_db.create_session(test_user, "meet")
            session_ids.append(session_id)
            
            evidence_id = await mongodb.create_evidence(
                session_id=session_id,
                user_id=test_user,
                audio={"transcript": f"Valid session {i}"}
            )
            evidence_ids.append(evidence_id)
        
        # Create orphaned evidence
        for i in range(num_orphaned):
            fake_session_id = uuid4()
            evidence_id = await mongodb.create_evidence(
                session_id=fake_session_id,
                user_id=test_user,
                audio={"transcript": f"Orphaned evidence {i}"}
            )
            orphaned_evidence_ids.append(evidence_id)
        
        # Generate integrity report
        report = await integrity_checker.get_integrity_report(check_limit=100)
        
        # Property 1: Report should contain expected sections
        assert "timestamp" in report, "Report should have timestamp"
        assert "checks_performed" in report, "Report should list checks performed"
        assert "total_violations" in report, "Report should have total violations count"
        assert "violations_by_type" in report, "Report should categorize violations"
        assert "violations" in report, "Report should list all violations"
        
        # Property 2: Report should detect orphaned evidence
        if num_orphaned > 0:
            assert report["total_violations"] > 0, \
                "Report should detect violations when orphaned evidence exists"
            
            # Should have dangling_session_reference or orphaned_evidence violations
            violation_types = report["violations_by_type"].keys()
            assert any(
                vtype in ["dangling_session_reference", "orphaned_evidence"]
                for vtype in violation_types
            ), "Report should identify orphaned evidence violations"
        
        # Property 3: Valid sessions should not appear in violations
        for session_id in session_ids:
            session_violations = [
                v for v in report["violations"]
                if v.session_id == session_id
            ]
            assert len(session_violations) == 0, \
                f"Valid session {session_id} should not have violations"
        
        # Property 4: Checks performed should include expected checks
        expected_checks = [
            "evidence_session_references",
            "evidence_event_references",
            "orphaned_evidence"
        ]
        for check in expected_checks:
            assert check in report["checks_performed"], \
                f"Report should include {check} check"
    
    finally:
        # Cleanup
        for evidence_id in evidence_ids + orphaned_evidence_ids:
            try:
                await mongodb.delete_evidence(evidence_id)
            except Exception:
                pass
        
        for session_id in session_ids:
            try:
                await postgres_db.delete_session(session_id)
            except Exception:
                pass
