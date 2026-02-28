"""
Unit tests for PostgreSQL CRUD operations
"""
import pytest
import asyncio
from uuid import uuid4, UUID
from datetime import datetime
from app.db.postgres import PostgresDB

# Test database URL
TEST_DATABASE_URL = 'postgresql://kavalan_user:kavalan_dev_password@localhost:5432/kavalan'


@pytest.fixture
async def db():
    """Create database connection for tests"""
    db = PostgresDB(database_url=TEST_DATABASE_URL)
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def test_user(db):
    """Create a test user"""
    user_id = await db.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    yield user_id
    # Cleanup
    await db.delete_user(user_id)


@pytest.fixture
async def test_session(db, test_user):
    """Create a test session"""
    session_id = await db.create_session(
        user_id=test_user,
        platform="meet"
    )
    yield session_id
    # Cleanup
    await db.delete_session(session_id)


# ==================== USER CRUD TESTS ====================

@pytest.mark.asyncio
async def test_create_user(db):
    """Test creating a new user"""
    email = f"test_{uuid4()}@example.com"
    user_id = await db.create_user(
        email=email,
        preferences={"language": "en", "theme": "dark"},
        consent_given=True
    )
    
    assert isinstance(user_id, UUID)
    
    # Verify user was created
    user = await db.get_user(user_id)
    assert user is not None
    assert user['email'] == email
    assert user['preferences']['language'] == 'en'
    assert user['consent_given'] is True
    
    # Cleanup
    await db.delete_user(user_id)


@pytest.mark.asyncio
async def test_get_user_by_email(db):
    """Test retrieving user by email"""
    email = f"test_{uuid4()}@example.com"
    user_id = await db.create_user(email=email)
    
    user = await db.get_user_by_email(email)
    assert user is not None
    assert user['user_id'] == user_id
    assert user['email'] == email
    
    # Cleanup
    await db.delete_user(user_id)


@pytest.mark.asyncio
async def test_update_user(db, test_user):
    """Test updating user preferences"""
    new_preferences = {"language": "hi", "notifications": True}
    last_active = datetime.now()
    
    success = await db.update_user(
        user_id=test_user,
        preferences=new_preferences,
        last_active=last_active
    )
    
    assert success is True
    
    # Verify update
    user = await db.get_user(test_user)
    assert user['preferences']['language'] == 'hi'
    assert user['last_active'] is not None


@pytest.mark.asyncio
async def test_delete_user(db):
    """Test deleting a user"""
    email = f"test_{uuid4()}@example.com"
    user_id = await db.create_user(email=email)
    
    success = await db.delete_user(user_id)
    assert success is True
    
    # Verify deletion
    user = await db.get_user(user_id)
    assert user is None


@pytest.mark.asyncio
async def test_delete_nonexistent_user(db):
    """Test deleting a user that doesn't exist"""
    fake_id = uuid4()
    success = await db.delete_user(fake_id)
    assert success is False


# ==================== SESSION CRUD TESTS ====================

@pytest.mark.asyncio
async def test_create_session(db, test_user):
    """Test creating a new session"""
    session_id = await db.create_session(
        user_id=test_user,
        platform="zoom"
    )
    
    assert isinstance(session_id, UUID)
    
    # Verify session was created
    session = await db.get_session(session_id)
    assert session is not None
    assert session['user_id'] == test_user
    assert session['platform'] == 'zoom'
    assert session['alert_count'] == 0
    
    # Cleanup
    await db.delete_session(session_id)


@pytest.mark.asyncio
async def test_get_user_sessions(db, test_user):
    """Test retrieving all sessions for a user"""
    # Create multiple sessions
    session_ids = []
    for platform in ['meet', 'zoom', 'teams']:
        session_id = await db.create_session(test_user, platform)
        session_ids.append(session_id)
    
    sessions = await db.get_user_sessions(test_user)
    assert len(sessions) >= 3
    
    # Verify sessions belong to user
    for session in sessions:
        assert session['user_id'] == test_user
    
    # Cleanup
    for session_id in session_ids:
        await db.delete_session(session_id)


@pytest.mark.asyncio
async def test_update_session(db, test_session):
    """Test updating session details"""
    end_time = datetime.now()
    duration = 1800  # 30 minutes
    max_score = 8.5
    alert_count = 3
    
    success = await db.update_session(
        session_id=test_session,
        end_time=end_time,
        duration_seconds=duration,
        max_threat_score=max_score,
        alert_count=alert_count
    )
    
    assert success is True
    
    # Verify update
    session = await db.get_session(test_session)
    assert session['duration_seconds'] == duration
    assert float(session['max_threat_score']) == max_score
    assert session['alert_count'] == alert_count


@pytest.mark.asyncio
async def test_delete_session(db, test_user):
    """Test deleting a session"""
    session_id = await db.create_session(test_user, "meet")
    
    success = await db.delete_session(session_id)
    assert success is True
    
    # Verify deletion
    session = await db.get_session(session_id)
    assert session is None


# ==================== THREAT_EVENT CRUD TESTS ====================

@pytest.mark.asyncio
async def test_create_threat_event(db, test_session):
    """Test creating a threat event"""
    event_id = await db.create_threat_event(
        session_id=test_session,
        threat_score=7.5,
        audio_score=8.0,
        visual_score=7.0,
        liveness_score=6.5,
        threat_level="high",
        is_alert=True,
        confidence=0.85
    )
    
    assert isinstance(event_id, UUID)
    
    # Verify event was created
    event = await db.get_threat_event(event_id)
    assert event is not None
    assert event['session_id'] == test_session
    assert float(event['threat_score']) == 7.5
    assert event['threat_level'] == 'high'
    assert event['is_alert'] is True
    
    # Cleanup
    await db.delete_threat_event(event_id)


@pytest.mark.asyncio
async def test_get_session_threat_events(db, test_session):
    """Test retrieving all threat events for a session"""
    # Create multiple events
    event_ids = []
    for score in [3.0, 5.5, 8.0]:
        event_id = await db.create_threat_event(
            session_id=test_session,
            threat_score=score,
            audio_score=score,
            visual_score=score,
            liveness_score=score,
            threat_level="low" if score < 5 else "high",
            is_alert=score >= 7.0,
            confidence=0.8
        )
        event_ids.append(event_id)
    
    events = await db.get_session_threat_events(test_session)
    assert len(events) >= 3
    
    # Verify events belong to session
    for event in events:
        assert event['session_id'] == test_session
    
    # Cleanup
    for event_id in event_ids:
        await db.delete_threat_event(event_id)


@pytest.mark.asyncio
async def test_get_high_threat_events(db, test_session):
    """Test retrieving high-threat events"""
    # Create events with different scores
    high_event_id = await db.create_threat_event(
        session_id=test_session,
        threat_score=8.5,
        audio_score=9.0,
        visual_score=8.0,
        liveness_score=7.5,
        threat_level="critical",
        is_alert=True,
        confidence=0.9
    )
    
    low_event_id = await db.create_threat_event(
        session_id=test_session,
        threat_score=3.0,
        audio_score=3.0,
        visual_score=3.0,
        liveness_score=3.0,
        threat_level="low",
        is_alert=False,
        confidence=0.7
    )
    
    # Get high-threat events (score >= 7.0)
    high_events = await db.get_high_threat_events(min_score=7.0)
    
    # Verify only high-threat events returned
    for event in high_events:
        assert float(event['threat_score']) >= 7.0
    
    # Cleanup
    await db.delete_threat_event(high_event_id)
    await db.delete_threat_event(low_event_id)


@pytest.mark.asyncio
async def test_threat_event_with_null_scores(db, test_session):
    """Test creating threat event with some null modality scores"""
    event_id = await db.create_threat_event(
        session_id=test_session,
        threat_score=5.0,
        audio_score=6.0,
        visual_score=None,  # Visual analysis unavailable
        liveness_score=4.0,
        threat_level="moderate",
        is_alert=False,
        confidence=0.6
    )
    
    event = await db.get_threat_event(event_id)
    assert event is not None
    assert event['audio_score'] is not None
    assert event['visual_score'] is None
    assert event['liveness_score'] is not None
    
    # Cleanup
    await db.delete_threat_event(event_id)


# ==================== AUDIT_LOG CRUD TESTS ====================

@pytest.mark.asyncio
async def test_create_audit_log(db, test_user):
    """Test creating an audit log entry"""
    resource_id = uuid4()
    log_id = await db.create_audit_log(
        user_id=test_user,
        action="read",
        resource_type="session",
        resource_id=resource_id,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0"
    )
    
    assert isinstance(log_id, UUID)
    
    # Verify log was created
    logs = await db.get_audit_logs(user_id=test_user)
    assert len(logs) > 0
    assert logs[0]['action'] == 'read'
    assert logs[0]['resource_type'] == 'session'


@pytest.mark.asyncio
async def test_get_audit_logs_with_filters(db, test_user):
    """Test retrieving audit logs with filters"""
    # Create multiple log entries
    await db.create_audit_log(
        user_id=test_user,
        action="read",
        resource_type="user",
        resource_id=test_user
    )
    
    await db.create_audit_log(
        user_id=test_user,
        action="write",
        resource_type="session",
        resource_id=uuid4()
    )
    
    # Filter by action
    read_logs = await db.get_audit_logs(user_id=test_user, action="read")
    assert all(log['action'] == 'read' for log in read_logs)
    
    # Filter by resource type
    session_logs = await db.get_audit_logs(
        user_id=test_user,
        resource_type="session"
    )
    assert all(log['resource_type'] == 'session' for log in session_logs)


@pytest.mark.asyncio
async def test_audit_log_with_null_user(db):
    """Test creating audit log for system actions (no user)"""
    log_id = await db.create_audit_log(
        user_id=None,  # System action
        action="system_cleanup",
        resource_type="audit_logs",
        resource_id=None
    )
    
    assert isinstance(log_id, UUID)
    
    # Verify log was created
    logs = await db.get_audit_logs(action="system_cleanup")
    assert len(logs) > 0
    assert logs[0]['user_id'] is None


# ==================== CASCADE DELETE TESTS ====================

@pytest.mark.asyncio
async def test_user_deletion_cascades_to_sessions(db):
    """Test that deleting a user cascades to sessions"""
    # Create user and session
    user_id = await db.create_user(email=f"test_{uuid4()}@example.com")
    session_id = await db.create_session(user_id, "meet")
    
    # Delete user
    await db.delete_user(user_id)
    
    # Verify session was also deleted
    session = await db.get_session(session_id)
    assert session is None


@pytest.mark.asyncio
async def test_session_deletion_cascades_to_threat_events(db, test_user):
    """Test that deleting a session cascades to threat events"""
    # Create session and threat event
    session_id = await db.create_session(test_user, "zoom")
    event_id = await db.create_threat_event(
        session_id=session_id,
        threat_score=5.0,
        audio_score=5.0,
        visual_score=5.0,
        liveness_score=5.0,
        threat_level="moderate",
        is_alert=False,
        confidence=0.7
    )
    
    # Delete session
    await db.delete_session(session_id)
    
    # Verify threat event was also deleted
    event = await db.get_threat_event(event_id)
    assert event is None


# ==================== EDGE CASE TESTS ====================

@pytest.mark.asyncio
async def test_get_nonexistent_user(db):
    """Test getting a user that doesn't exist"""
    fake_id = uuid4()
    user = await db.get_user(fake_id)
    assert user is None


@pytest.mark.asyncio
async def test_get_nonexistent_session(db):
    """Test getting a session that doesn't exist"""
    fake_id = uuid4()
    session = await db.get_session(fake_id)
    assert session is None


@pytest.mark.asyncio
async def test_get_nonexistent_threat_event(db):
    """Test getting a threat event that doesn't exist"""
    fake_id = uuid4()
    event = await db.get_threat_event(fake_id)
    assert event is None


@pytest.mark.asyncio
async def test_update_nonexistent_user(db):
    """Test updating a user that doesn't exist"""
    fake_id = uuid4()
    success = await db.update_user(fake_id, preferences={"test": "value"})
    assert success is False


@pytest.mark.asyncio
async def test_update_nonexistent_session(db):
    """Test updating a session that doesn't exist"""
    fake_id = uuid4()
    success = await db.update_session(fake_id, alert_count=5)
    assert success is False


@pytest.mark.asyncio
async def test_empty_user_sessions(db, test_user):
    """Test getting sessions for user with no sessions"""
    # Delete any existing sessions
    sessions = await db.get_user_sessions(test_user)
    for session in sessions:
        await db.delete_session(session['session_id'])
    
    # Verify empty list
    sessions = await db.get_user_sessions(test_user)
    assert len(sessions) == 0


@pytest.mark.asyncio
async def test_empty_session_threat_events(db, test_session):
    """Test getting threat events for session with no events"""
    # Delete any existing events
    events = await db.get_session_threat_events(test_session)
    for event in events:
        await db.delete_threat_event(event['event_id'])
    
    # Verify empty list
    events = await db.get_session_threat_events(test_session)
    assert len(events) == 0
