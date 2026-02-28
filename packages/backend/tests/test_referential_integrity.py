"""
Unit tests for referential integrity checker

Tests specific examples and edge cases for the referential integrity checker.
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime

from app.db.postgres import PostgresDB
from app.db.mongodb import MongoDB
from app.db.referential_integrity import (
    ReferentialIntegrityChecker,
    IntegrityViolation,
    create_integrity_checker
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
async def test_user(postgres_db):
    """Create a test user"""
    user_id = await postgres_db.create_user(
        email=f"test_{uuid4()}@example.com",
        consent_given=True
    )
    yield user_id
    try:
        await postgres_db.delete_user(user_id)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_check_valid_session_evidence(
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """Test that valid session-evidence relationship passes integrity check"""
    # Create session
    session_id = await postgres_db.create_session(test_user, "meet")
    
    # Create evidence
    evidence_id = await mongodb.create_evidence(
        session_id=session_id,
        user_id=test_user,
        audio={"transcript": "Test transcript"}
    )
    
    try:
        # Check integrity
        violations = await integrity_checker.check_session_id_consistency(session_id)
        
        assert len(violations) == 0, "Valid relationship should have no violations"
        
        # Verify method should return True
        is_valid = await integrity_checker.verify_referential_integrity(session_id)
        assert is_valid is True
    
    finally:
        await mongodb.delete_evidence(evidence_id)
        await postgres_db.delete_session(session_id)


@pytest.mark.asyncio
async def test_detect_missing_session(
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """Test detection of evidence referencing non-existent session"""
    # Create evidence with fake session_id
    fake_session_id = uuid4()
    evidence_id = await mongodb.create_evidence(
        session_id=fake_session_id,
        user_id=test_user,
        audio={"transcript": "Orphaned evidence"}
    )
    
    try:
        # Check for violations
        violations = await integrity_checker.check_evidence_session_references(limit=100)
        
        # Find violations for our fake session
        relevant_violations = [
            v for v in violations
            if v.session_id == fake_session_id or
            (v.details and v.details.get("session_id") == str(fake_session_id))
        ]
        
        assert len(relevant_violations) > 0, "Should detect dangling session reference"
        assert any(
            v.violation_type == "dangling_session_reference"
            for v in relevant_violations
        )
    
    finally:
        await mongodb.delete_evidence(evidence_id)


@pytest.mark.asyncio
async def test_detect_missing_event(
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """Test detection of evidence referencing non-existent threat event"""
    from bson import ObjectId
    
    # Create valid session
    session_id = await postgres_db.create_session(test_user, "meet")
    
    # Create evidence with fake event_id
    fake_event_id = uuid4()
    evidence_id = await mongodb.create_evidence(
        session_id=session_id,
        user_id=test_user,
        audio={"transcript": "Test"}
    )
    
    # Manually add event_id to evidence
    await mongodb.evidence.update_one(
        {"_id": ObjectId(evidence_id)},
        {"$set": {"event_id": str(fake_event_id)}}
    )
    
    try:
        # Check for violations
        violations = await integrity_checker.check_evidence_event_references(limit=100)
        
        # Find violations for our fake event
        relevant_violations = [
            v for v in violations
            if v.postgres_id == fake_event_id or
            (v.details and v.details.get("event_id") == str(fake_event_id))
        ]
        
        assert len(relevant_violations) > 0, "Should detect dangling event reference"
        assert any(
            v.violation_type == "dangling_event_reference"
            for v in relevant_violations
        )
    
    finally:
        await mongodb.delete_evidence(evidence_id)
        await postgres_db.delete_session(session_id)


@pytest.mark.asyncio
async def test_detect_invalid_session_id_format(
    mongodb,
    integrity_checker,
    test_user
):
    """Test detection of evidence with invalid session_id format"""
    # Create evidence with invalid session_id
    result = await mongodb.evidence.insert_one({
        "session_id": "not-a-valid-uuid",
        "user_id": str(test_user),
        "timestamp": datetime.utcnow(),
        "audio": {},
        "visual": {},
        "liveness": {},
        "metadata": {}
    })
    evidence_id = str(result.inserted_id)
    
    try:
        # Check for violations
        violations = await integrity_checker.check_evidence_session_references(limit=100)
        
        # Find violations for our evidence
        relevant_violations = [
            v for v in violations
            if v.mongodb_id == evidence_id
        ]
        
        assert len(relevant_violations) > 0, "Should detect invalid session_id format"
        assert any(
            v.violation_type == "invalid_session_id"
            for v in relevant_violations
        )
    
    finally:
        await mongodb.evidence.delete_one({"_id": result.inserted_id})


@pytest.mark.asyncio
async def test_detect_missing_session_id_field(
    mongodb,
    integrity_checker,
    test_user
):
    """Test detection of evidence missing session_id field"""
    # MongoDB has schema validation that requires session_id, so we need to
    # bypass validation or test with an empty string instead
    # For this test, we'll use an empty string which passes validation but fails integrity check
    result = await mongodb.evidence.insert_one({
        "session_id": "",  # Empty string passes validation but is invalid
        "user_id": str(test_user),
        "timestamp": datetime.utcnow(),
        "audio": {},
        "visual": {},
        "liveness": {},
        "metadata": {}
    })
    evidence_id = str(result.inserted_id)
    
    try:
        # Check for violations
        violations = await integrity_checker.check_evidence_session_references(limit=100)
        
        # Find violations for our evidence
        relevant_violations = [
            v for v in violations
            if v.mongodb_id == evidence_id
        ]
        
        # Empty string should be caught as missing or invalid
        assert len(relevant_violations) > 0, "Should detect missing/invalid session_id"
        assert any(
            v.violation_type in ["missing_session_id", "invalid_session_id"]
            for v in relevant_violations
        )
    
    finally:
        await mongodb.evidence.delete_one({"_id": result.inserted_id})


@pytest.mark.asyncio
async def test_check_orphaned_evidence(
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """Test comprehensive orphaned evidence detection"""
    # Create valid session with evidence
    valid_session_id = await postgres_db.create_session(test_user, "meet")
    valid_evidence_id = await mongodb.create_evidence(
        session_id=valid_session_id,
        user_id=test_user,
        audio={"transcript": "Valid"}
    )
    
    # Create orphaned evidence
    orphan_session_id = uuid4()
    orphan_evidence_id = await mongodb.create_evidence(
        session_id=orphan_session_id,
        user_id=test_user,
        audio={"transcript": "Orphaned"}
    )
    
    try:
        # Check for orphaned evidence
        violations = await integrity_checker.check_orphaned_evidence(limit=100)
        
        # Should find orphaned session
        orphan_violations = [
            v for v in violations
            if v.session_id == orphan_session_id or
            (v.details and v.details.get("session_id") == str(orphan_session_id))
        ]
        
        assert len(orphan_violations) > 0, "Should detect orphaned evidence"
        
        # Should not flag valid session
        valid_violations = [
            v for v in violations
            if v.session_id == valid_session_id
        ]
        
        assert len(valid_violations) == 0, "Should not flag valid evidence as orphaned"
    
    finally:
        await mongodb.delete_evidence(valid_evidence_id)
        await mongodb.delete_evidence(orphan_evidence_id)
        await postgres_db.delete_session(valid_session_id)


@pytest.mark.asyncio
async def test_integrity_report_structure(
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """Test that integrity report has correct structure"""
    # Create some test data
    session_id = await postgres_db.create_session(test_user, "meet")
    evidence_id = await mongodb.create_evidence(
        session_id=session_id,
        user_id=test_user,
        audio={"transcript": "Test"}
    )
    
    try:
        # Generate report
        report = await integrity_checker.get_integrity_report(check_limit=100)
        
        # Verify structure
        assert "timestamp" in report
        assert "checks_performed" in report
        assert "total_violations" in report
        assert "violations_by_type" in report
        assert "violations" in report
        
        # Verify checks were performed
        assert "evidence_session_references" in report["checks_performed"]
        assert "evidence_event_references" in report["checks_performed"]
        assert "orphaned_evidence" in report["checks_performed"]
        
        # Verify timestamp format
        assert isinstance(report["timestamp"], str)
        
        # Verify counts are consistent
        assert report["total_violations"] == len(report["violations"])
        
        # Verify violations_by_type aggregation
        type_count = sum(report["violations_by_type"].values())
        assert type_count == report["total_violations"]
    
    finally:
        await mongodb.delete_evidence(evidence_id)
        await postgres_db.delete_session(session_id)


@pytest.mark.asyncio
async def test_session_consistency_with_multiple_evidence(
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """Test session consistency check with multiple evidence records"""
    # Create session
    session_id = await postgres_db.create_session(test_user, "meet")
    
    # Create multiple evidence records
    evidence_ids = []
    for i in range(3):
        evidence_id = await mongodb.create_evidence(
            session_id=session_id,
            user_id=test_user,
            audio={"transcript": f"Evidence {i}"}
        )
        evidence_ids.append(evidence_id)
    
    try:
        # Check consistency
        violations = await integrity_checker.check_session_id_consistency(session_id)
        
        assert len(violations) == 0, "All evidence should reference correct session"
        
        # Verify all evidence
        mongo_evidence = await mongodb.get_session_evidence(session_id)
        assert len(mongo_evidence) == 3
        
        for evidence in mongo_evidence:
            assert evidence["session_id"] == str(session_id)
    
    finally:
        for evidence_id in evidence_ids:
            await mongodb.delete_evidence(evidence_id)
        await postgres_db.delete_session(session_id)


@pytest.mark.asyncio
async def test_event_session_mismatch_detection(
    postgres_db,
    mongodb,
    integrity_checker,
    test_user
):
    """Test detection of event belonging to different session"""
    from bson import ObjectId
    
    # Create two sessions
    session1_id = await postgres_db.create_session(test_user, "meet")
    session2_id = await postgres_db.create_session(test_user, "zoom")
    
    # Create event in session1
    event_id = await postgres_db.create_threat_event(
        session_id=session1_id,
        threat_score=5.0,
        audio_score=5.0,
        visual_score=5.0,
        liveness_score=5.0,
        threat_level="moderate",
        is_alert=False,
        confidence=0.8
    )
    
    # Create evidence in session2 that references event from session1
    evidence_id = await mongodb.create_evidence(
        session_id=session2_id,
        user_id=test_user,
        audio={"transcript": "Test"}
    )
    
    # Add event_id to evidence
    await mongodb.evidence.update_one(
        {"_id": ObjectId(evidence_id)},
        {"$set": {"event_id": str(event_id)}}
    )
    
    try:
        # Check session2 consistency
        violations = await integrity_checker.check_session_id_consistency(session2_id)
        
        # Should detect event-session mismatch
        mismatch_violations = [
            v for v in violations
            if v.violation_type == "event_session_mismatch"
        ]
        
        assert len(mismatch_violations) > 0, "Should detect event-session mismatch"
    
    finally:
        await mongodb.delete_evidence(evidence_id)
        await postgres_db.delete_threat_event(event_id)
        await postgres_db.delete_session(session1_id)
        await postgres_db.delete_session(session2_id)


@pytest.mark.asyncio
async def test_empty_database_integrity_check(
    integrity_checker
):
    """Test integrity check on empty database"""
    # Generate report on empty database
    report = await integrity_checker.get_integrity_report(check_limit=100)
    
    # Should complete without errors
    assert report["total_violations"] == 0
    assert len(report["violations"]) == 0
    assert len(report["checks_performed"]) > 0


@pytest.mark.asyncio
async def test_verify_nonexistent_session(
    integrity_checker
):
    """Test verification of non-existent session"""
    fake_session_id = uuid4()
    
    # Check consistency for non-existent session
    violations = await integrity_checker.check_session_id_consistency(fake_session_id)
    
    # Should detect missing session
    assert len(violations) > 0
    assert any(v.violation_type == "missing_session" for v in violations)
    
    # Verify method should return False
    is_valid = await integrity_checker.verify_referential_integrity(fake_session_id)
    assert is_valid is False
