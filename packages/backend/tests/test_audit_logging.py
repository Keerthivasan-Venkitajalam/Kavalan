"""
Unit tests for audit logging functionality

Tests verify that all data access operations (read, write, delete) are
properly logged to the audit_logs table for DPDP Act 2023 compliance.
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from app.db.postgres import postgres_db
from app.db.mongodb import mongodb
from app.db.audit_logger import audit_logger
from app.db.audited_operations import audited_postgres, audited_mongo


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def setup_databases():
    """Setup database connections"""
    await postgres_db.connect()
    await mongodb.connect()
    yield
    await postgres_db.disconnect()
    await mongodb.disconnect()


@pytest.fixture
async def test_user():
    """Create a test user"""
    user_id = await postgres_db.create_user(
        email=f"test_{uuid4()}@example.com",
        consent_given=True
    )
    yield user_id
    # Cleanup
    await postgres_db.delete_user(user_id)


@pytest.fixture
async def test_session(test_user):
    """Create a test session"""
    session_id = await postgres_db.create_session(test_user, "meet")
    yield session_id
    # Cleanup
    await postgres_db.delete_session(session_id)


# ==================== AUDIT LOGGER TESTS ====================


@pytest.mark.asyncio
async def test_log_read_operation(test_user):
    """Test that read operations are logged"""
    resource_id = uuid4()
    ip_address = "192.168.1.1"
    user_agent = "Mozilla/5.0"
    
    log_id = await audit_logger.log_read(
        user_id=test_user,
        resource_type='user',
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    assert log_id is not None
    
    # Verify log was created
    logs = await audit_logger.get_user_audit_trail(test_user, limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'read'
    assert logs[0]['resource_type'] == 'user'
    assert logs[0]['resource_id'] == resource_id
    assert logs[0]['ip_address'] == ip_address
    assert logs[0]['user_agent'] == user_agent


@pytest.mark.asyncio
async def test_log_write_operation(test_user):
    """Test that write operations are logged"""
    resource_id = uuid4()
    
    log_id = await audit_logger.log_write(
        user_id=test_user,
        resource_type='session',
        resource_id=resource_id
    )
    
    assert log_id is not None
    
    # Verify log was created
    logs = await audit_logger.get_action_audit_trail('write', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'write'
    assert logs[0]['user_id'] == test_user


@pytest.mark.asyncio
async def test_log_delete_operation(test_user):
    """Test that delete operations are logged"""
    resource_id = uuid4()
    
    log_id = await audit_logger.log_delete(
        user_id=test_user,
        resource_type='threat_event',
        resource_id=resource_id
    )
    
    assert log_id is not None
    
    # Verify log was created
    logs = await audit_logger.get_action_audit_trail('delete', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'delete'
    assert logs[0]['resource_type'] == 'threat_event'


@pytest.mark.asyncio
async def test_get_user_audit_trail(test_user):
    """Test retrieving complete audit trail for a user"""
    # Create multiple log entries
    await audit_logger.log_read(test_user, 'user', test_user)
    await audit_logger.log_write(test_user, 'session', uuid4())
    await audit_logger.log_delete(test_user, 'threat_event', uuid4())
    
    # Get audit trail
    logs = await audit_logger.get_user_audit_trail(test_user, limit=10)
    
    assert len(logs) >= 3
    assert all(log['user_id'] == test_user for log in logs)


@pytest.mark.asyncio
async def test_get_resource_audit_trail():
    """Test retrieving audit trail for a specific resource type"""
    user_id = uuid4()
    
    # Create logs for different resource types
    await audit_logger.log_read(user_id, 'session', uuid4())
    await audit_logger.log_read(user_id, 'session', uuid4())
    
    # Get audit trail for sessions
    logs = await audit_logger.get_resource_audit_trail('session', limit=10)
    
    assert len(logs) >= 2
    assert all(log['resource_type'] == 'session' for log in logs)


# ==================== AUDITED POSTGRES OPERATIONS TESTS ====================


@pytest.mark.asyncio
async def test_audited_create_user():
    """Test that user creation is audited"""
    email = f"audit_test_{uuid4()}@example.com"
    ip_address = "10.0.0.1"
    
    user_id = await audited_postgres.create_user(
        email=email,
        consent_given=True,
        ip_address=ip_address
    )
    
    assert user_id is not None
    
    # Verify audit log was created
    logs = await audit_logger.get_user_audit_trail(user_id, limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'write'
    assert logs[0]['resource_type'] == 'user'
    assert logs[0]['resource_id'] == user_id
    assert logs[0]['ip_address'] == ip_address
    
    # Cleanup
    await postgres_db.delete_user(user_id)


@pytest.mark.asyncio
async def test_audited_get_user(test_user):
    """Test that user read is audited"""
    ip_address = "10.0.0.2"
    
    user = await audited_postgres.get_user(
        user_id=test_user,
        ip_address=ip_address
    )
    
    assert user is not None
    assert user['user_id'] == test_user
    
    # Verify audit log was created
    logs = await audit_logger.get_user_audit_trail(test_user, limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'read'
    assert logs[0]['resource_type'] == 'user'
    assert logs[0]['ip_address'] == ip_address


@pytest.mark.asyncio
async def test_audited_update_user(test_user):
    """Test that user update is audited"""
    preferences = {"language": "en", "theme": "dark"}
    
    success = await audited_postgres.update_user(
        user_id=test_user,
        preferences=preferences
    )
    
    assert success is True
    
    # Verify audit log was created
    logs = await audit_logger.get_action_audit_trail('write', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'write'
    assert logs[0]['resource_type'] == 'user'


@pytest.mark.asyncio
async def test_audited_create_session(test_user):
    """Test that session creation is audited"""
    ip_address = "10.0.0.3"
    
    session_id = await audited_postgres.create_session(
        user_id=test_user,
        platform='zoom',
        ip_address=ip_address
    )
    
    assert session_id is not None
    
    # Verify audit log was created
    logs = await audit_logger.get_resource_audit_trail('session', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'write'
    assert logs[0]['resource_type'] == 'session'
    assert logs[0]['resource_id'] == session_id
    
    # Cleanup
    await postgres_db.delete_session(session_id)


@pytest.mark.asyncio
async def test_audited_get_session(test_session, test_user):
    """Test that session read is audited"""
    session = await audited_postgres.get_session(
        session_id=test_session,
        user_id=test_user
    )
    
    assert session is not None
    assert session['session_id'] == test_session
    
    # Verify audit log was created
    logs = await audit_logger.get_action_audit_trail('read', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'read'
    assert logs[0]['resource_type'] == 'session'


@pytest.mark.asyncio
async def test_audited_create_threat_event(test_session, test_user):
    """Test that threat event creation is audited"""
    event_id = await audited_postgres.create_threat_event(
        session_id=test_session,
        user_id=test_user,
        threat_score=7.5,
        audio_score=8.0,
        visual_score=7.0,
        liveness_score=7.5,
        threat_level='high',
        is_alert=True,
        confidence=0.85
    )
    
    assert event_id is not None
    
    # Verify audit log was created
    logs = await audit_logger.get_resource_audit_trail('threat_event', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'write'
    assert logs[0]['resource_type'] == 'threat_event'
    assert logs[0]['resource_id'] == event_id
    
    # Cleanup
    await postgres_db.delete_threat_event(event_id)


@pytest.mark.asyncio
async def test_audited_delete_session(test_user):
    """Test that session deletion is audited"""
    # Create a session to delete
    session_id = await postgres_db.create_session(test_user, 'teams')
    
    # Delete with audit logging
    success = await audited_postgres.delete_session(
        session_id=session_id,
        user_id=test_user
    )
    
    assert success is True
    
    # Verify audit log was created
    logs = await audit_logger.get_action_audit_trail('delete', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'delete'
    assert logs[0]['resource_type'] == 'session'
    assert logs[0]['resource_id'] == session_id


# ==================== AUDITED MONGO OPERATIONS TESTS ====================


@pytest.mark.asyncio
async def test_audited_create_evidence(test_session, test_user):
    """Test that evidence creation is audited"""
    ip_address = "10.0.0.4"
    
    evidence_id = await audited_mongo.create_evidence(
        session_id=test_session,
        user_id=test_user,
        audio={"transcript": "Test transcript"},
        ip_address=ip_address
    )
    
    assert evidence_id is not None
    
    # Verify audit log was created
    logs = await audit_logger.get_resource_audit_trail('evidence', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'write'
    assert logs[0]['resource_type'] == 'evidence'
    assert logs[0]['ip_address'] == ip_address
    
    # Cleanup
    await mongodb.delete_evidence(evidence_id)


@pytest.mark.asyncio
async def test_audited_get_session_evidence(test_session, test_user):
    """Test that evidence read is audited"""
    # Create evidence first
    evidence_id = await mongodb.create_evidence(
        session_id=test_session,
        user_id=test_user,
        audio={"transcript": "Test"}
    )
    
    # Get evidence with audit logging
    evidence_list = await audited_mongo.get_session_evidence(
        session_id=test_session,
        user_id=test_user
    )
    
    assert len(evidence_list) > 0
    
    # Verify audit log was created
    logs = await audit_logger.get_action_audit_trail('read', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'read'
    assert logs[0]['resource_type'] == 'evidence'
    
    # Cleanup
    await mongodb.delete_evidence(evidence_id)


@pytest.mark.asyncio
async def test_audited_create_digital_fir(test_session, test_user):
    """Test that Digital FIR creation is audited"""
    fir_id = f"FIR_{uuid4()}"
    
    object_id = await audited_mongo.create_digital_fir(
        fir_id=fir_id,
        session_id=test_session,
        user_id=test_user,
        summary={"max_threat_score": 8.5},
        evidence={"transcripts": []},
        legal={"chain_of_custody": []}
    )
    
    assert object_id is not None
    
    # Verify audit log was created
    logs = await audit_logger.get_resource_audit_trail('digital_fir', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'write'
    assert logs[0]['resource_type'] == 'digital_fir'
    
    # Cleanup
    await mongodb.delete_digital_fir(fir_id)


@pytest.mark.asyncio
async def test_audited_delete_evidence(test_session, test_user):
    """Test that evidence deletion is audited"""
    # Create evidence to delete
    evidence_id = await mongodb.create_evidence(
        session_id=test_session,
        user_id=test_user,
        audio={"transcript": "Test"}
    )
    
    # Delete with audit logging
    success = await audited_mongo.delete_evidence(
        evidence_id=evidence_id,
        user_id=test_user
    )
    
    assert success is True
    
    # Verify audit log was created
    logs = await audit_logger.get_action_audit_trail('delete', limit=1)
    assert len(logs) > 0
    assert logs[0]['action'] == 'delete'
    assert logs[0]['resource_type'] == 'evidence'


# ==================== EDGE CASES ====================


@pytest.mark.asyncio
async def test_audit_log_with_null_user_id():
    """Test that system operations (null user_id) are logged"""
    resource_id = uuid4()
    
    log_id = await audit_logger.log_write(
        user_id=None,  # System operation
        resource_type='system_config',
        resource_id=resource_id
    )
    
    assert log_id is not None
    
    # Verify log was created
    logs = await postgres_db.get_audit_logs(limit=1)
    assert len(logs) > 0
    assert logs[0]['user_id'] is None
    assert logs[0]['resource_type'] == 'system_config'


@pytest.mark.asyncio
async def test_audit_log_with_null_ip_address(test_user):
    """Test that logs without IP address are created"""
    log_id = await audit_logger.log_read(
        user_id=test_user,
        resource_type='user',
        resource_id=test_user,
        ip_address=None  # No IP address
    )
    
    assert log_id is not None
    
    # Verify log was created
    logs = await audit_logger.get_user_audit_trail(test_user, limit=1)
    assert len(logs) > 0
    assert logs[0]['ip_address'] is None


@pytest.mark.asyncio
async def test_multiple_operations_create_multiple_logs(test_user):
    """Test that multiple operations create separate audit logs"""
    initial_count = len(await audit_logger.get_user_audit_trail(test_user, limit=100))
    
    # Perform multiple operations
    await audited_postgres.get_user(test_user)
    await audited_postgres.update_user(test_user, preferences={"test": "value"})
    await audited_postgres.get_user(test_user)
    
    # Verify multiple logs were created
    final_count = len(await audit_logger.get_user_audit_trail(test_user, limit=100))
    assert final_count >= initial_count + 3


@pytest.mark.asyncio
async def test_audit_log_timestamp_is_recent(test_user):
    """Test that audit log timestamps are recent"""
    before = datetime.now()
    
    await audit_logger.log_read(
        user_id=test_user,
        resource_type='user',
        resource_id=test_user
    )
    
    after = datetime.now()
    
    logs = await audit_logger.get_user_audit_trail(test_user, limit=1)
    assert len(logs) > 0
    
    log_time = logs[0]['timestamp']
    assert before <= log_time <= after
