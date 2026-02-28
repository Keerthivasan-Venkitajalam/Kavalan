"""
Property-based tests for audit log creation

Feature: production-ready-browser-extension
Property 14: Audit Log Creation for Data Access

For any data access operation (read, write, delete) on user data, an audit log
entry should be created with timestamp, user ID, action type, and resource ID.

**Validates: Requirements 7.6, 17.7**
"""
import pytest
import asyncio
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
from app.db.postgres import PostgresDB
from app.db.mongodb import MongoDB
from app.db.audit_logger import AuditLogger
from app.db.audited_operations import AuditedPostgresOperations, AuditedMongoOperations


# ==================== HYPOTHESIS STRATEGIES ====================

# Valid action types
action_strategy = st.sampled_from(['read', 'write', 'delete'])

# Valid resource types
resource_type_strategy = st.sampled_from([
    'user', 'session', 'threat_event', 'evidence', 'digital_fir'
])

# UUID strategy
uuid_strategy = st.uuids()

# Optional IP address strategy
ip_address_strategy = st.one_of(
    st.none(),
    st.from_regex(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', fullmatch=True)
)

# Optional user agent strategy
user_agent_strategy = st.one_of(
    st.none(),
    st.text(min_size=10, max_size=200, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P', 'Zs'),
        blacklist_characters='\x00\n\r\t'
    ))
)


# ==================== FIXTURES ====================

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
async def audit_logger(postgres_db):
    """Create audit logger instance"""
    return AuditLogger()


@pytest.fixture
async def audited_postgres(postgres_db):
    """Create audited PostgreSQL operations instance"""
    return AuditedPostgresOperations()


@pytest.fixture
async def audited_mongo(mongodb):
    """Create audited MongoDB operations instance"""
    return AuditedMongoOperations()


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



# ==================== PROPERTY TESTS ====================

@pytest.mark.property
@pytest.mark.asyncio
@given(
    user_id=uuid_strategy,
    action=action_strategy,
    resource_type=resource_type_strategy,
    resource_id=uuid_strategy,
    ip_address=ip_address_strategy,
    user_agent=user_agent_strategy
)
@settings(
    max_examples=100,
    deadline=5000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_audit_log_created_for_any_operation(
    postgres_db,
    audit_logger,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID,
    ip_address: str,
    user_agent: str
):
    """
    Feature: production-ready-browser-extension
    Property 14: Audit Log Creation for Data Access
    
    For any data access operation (read, write, delete), an audit log entry
    should be created with timestamp, user_id, action, resource_type, and resource_id.
    
    **Validates: Requirements 7.6, 17.7**
    """
    # Record time before operation
    before_time = datetime.now()
    
    # Perform the audit logging operation based on action type
    if action == 'read':
        log_id = await audit_logger.log_read(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    elif action == 'write':
        log_id = await audit_logger.log_write(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    else:  # delete
        log_id = await audit_logger.log_delete(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    # Record time after operation
    after_time = datetime.now()
    
    # Property 1: Log ID should be created
    assert log_id is not None, "Audit log should return a valid log ID"
    assert isinstance(log_id, UUID), "Log ID should be a UUID"
    
    # Property 2: Audit log entry should exist in database
    logs = await postgres_db.get_audit_logs(limit=1)
    assert len(logs) > 0, "At least one audit log should exist"
    
    # Find the specific log we just created
    recent_log = None
    for log in logs:
        if log.get('log_id') == log_id:
            recent_log = log
            break
    
    # If not found in first result, search by user_id
    if recent_log is None:
        user_logs = await audit_logger.get_user_audit_trail(user_id, limit=10)
        for log in user_logs:
            if log.get('log_id') == log_id:
                recent_log = log
                break
    
    assert recent_log is not None, f"Audit log with ID {log_id} should exist in database"
    
    # Property 3: Log should contain correct user_id
    assert recent_log['user_id'] == user_id, \
        f"Audit log user_id should be {user_id}, got {recent_log['user_id']}"
    
    # Property 4: Log should contain correct action
    assert recent_log['action'] == action, \
        f"Audit log action should be '{action}', got '{recent_log['action']}'"
    
    # Property 5: Log should contain correct resource_type
    assert recent_log['resource_type'] == resource_type, \
        f"Audit log resource_type should be '{resource_type}', got '{recent_log['resource_type']}'"
    
    # Property 6: Log should contain correct resource_id
    assert recent_log['resource_id'] == resource_id, \
        f"Audit log resource_id should be {resource_id}, got {recent_log['resource_id']}"
    
    # Property 7: Log should have a timestamp within reasonable bounds
    log_timestamp = recent_log['timestamp']
    assert isinstance(log_timestamp, datetime), "Timestamp should be a datetime object"
    assert before_time <= log_timestamp <= after_time + timedelta(seconds=1), \
        f"Timestamp should be between {before_time} and {after_time}, got {log_timestamp}"
    
    # Property 8: IP address should match (if provided)
    if ip_address is not None:
        assert recent_log['ip_address'] == ip_address, \
            f"IP address should be '{ip_address}', got '{recent_log['ip_address']}'"
    
    # Property 9: User agent should match (if provided)
    if user_agent is not None:
        assert recent_log['user_agent'] == user_agent, \
            f"User agent should be '{user_agent}', got '{recent_log['user_agent']}'"



@pytest.mark.property
@pytest.mark.asyncio
@given(
    email=st.emails(),
    ip_address=ip_address_strategy,
    user_agent=user_agent_strategy
)
@settings(
    max_examples=50,
    deadline=10000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_audited_postgres_operations_create_logs(
    postgres_db,
    audited_postgres,
    audit_logger,
    email: str,
    ip_address: str,
    user_agent: str
):
    """
    Feature: production-ready-browser-extension
    Property 14: Audit Log Creation for Data Access
    
    For any PostgreSQL operation through audited_postgres, an audit log
    should be automatically created.
    
    **Validates: Requirements 7.6, 17.7**
    """
    # Create user through audited operations
    user_id = await audited_postgres.create_user(
        email=email,
        consent_given=True,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    try:
        # Property 1: User creation should create audit log
        create_logs = await audit_logger.get_user_audit_trail(user_id, limit=10)
        create_log = next((log for log in create_logs if log['action'] == 'write'), None)
        
        assert create_log is not None, "User creation should create audit log"
        assert create_log['resource_type'] == 'user'
        assert create_log['resource_id'] == user_id
        
        # Read user through audited operations
        user = await audited_postgres.get_user(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        assert user is not None, "User should exist"
        
        # Property 2: User read should create audit log
        read_logs = await audit_logger.get_user_audit_trail(user_id, limit=10)
        read_log = next((log for log in read_logs if log['action'] == 'read'), None)
        
        assert read_log is not None, "User read should create audit log"
        assert read_log['resource_type'] == 'user'
        assert read_log['resource_id'] == user_id
        
        # Update user through audited operations
        preferences = {"language": "en", "theme": "dark"}
        success = await audited_postgres.update_user(
            user_id=user_id,
            preferences=preferences,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        assert success is True, "User update should succeed"
        
        # Property 3: User update should create audit log
        update_logs = await audit_logger.get_user_audit_trail(user_id, limit=10)
        # Count write logs (should have at least 2: create + update)
        write_logs = [log for log in update_logs if log['action'] == 'write']
        assert len(write_logs) >= 2, "User update should create additional audit log"
        
        # Delete user through audited operations
        delete_success = await audited_postgres.delete_user(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        assert delete_success is True, "User deletion should succeed"
        
        # Property 4: User deletion should create audit log
        delete_logs = await audit_logger.get_user_audit_trail(user_id, limit=10)
        delete_log = next((log for log in delete_logs if log['action'] == 'delete'), None)
        
        assert delete_log is not None, "User deletion should create audit log"
        assert delete_log['resource_type'] == 'user'
        assert delete_log['resource_id'] == user_id
        
    except Exception as e:
        # Cleanup on error
        try:
            await postgres_db.delete_user(user_id)
        except:
            pass
        raise e



@pytest.mark.property
@pytest.mark.asyncio
@given(
    platform=st.sampled_from(['meet', 'zoom', 'teams']),
    ip_address=ip_address_strategy
)
@settings(
    max_examples=50,
    deadline=10000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_audited_session_operations_create_logs(
    postgres_db,
    audited_postgres,
    audit_logger,
    platform: str,
    ip_address: str
):
    """
    Feature: production-ready-browser-extension
    Property 14: Audit Log Creation for Data Access
    
    For any session operation through audited_postgres, an audit log
    should be automatically created.
    
    **Validates: Requirements 7.6, 17.7**
    """
    # Create a real user first (required for foreign key)
    real_user_id = await postgres_db.create_user(
        email=f"test_{uuid4()}@example.com",
        consent_given=True
    )
    
    try:
        # Create session through audited operations
        session_id = await audited_postgres.create_session(
            user_id=real_user_id,
            platform=platform,
            ip_address=ip_address
        )
        
        try:
            # Property 1: Session creation should create audit log
            create_logs = await audit_logger.get_resource_audit_trail('session', limit=10)
            create_log = next(
                (log for log in create_logs 
                 if log['action'] == 'write' and log['resource_id'] == session_id),
                None
            )
            
            assert create_log is not None, "Session creation should create audit log"
            assert create_log['resource_type'] == 'session'
            
            # Read session through audited operations
            session = await audited_postgres.get_session(
                session_id=session_id,
                user_id=real_user_id,
                ip_address=ip_address
            )
            
            assert session is not None, "Session should exist"
            
            # Property 2: Session read should create audit log
            read_logs = await audit_logger.get_resource_audit_trail('session', limit=10)
            read_log = next(
                (log for log in read_logs 
                 if log['action'] == 'read' and log['resource_id'] == session_id),
                None
            )
            
            assert read_log is not None, "Session read should create audit log"
            
            # Delete session through audited operations
            delete_success = await audited_postgres.delete_session(
                session_id=session_id,
                user_id=real_user_id,
                ip_address=ip_address
            )
            
            assert delete_success is True, "Session deletion should succeed"
            
            # Property 3: Session deletion should create audit log
            delete_logs = await audit_logger.get_resource_audit_trail('session', limit=10)
            delete_log = next(
                (log for log in delete_logs 
                 if log['action'] == 'delete' and log['resource_id'] == session_id),
                None
            )
            
            assert delete_log is not None, "Session deletion should create audit log"
            
        except Exception as e:
            # Cleanup session on error
            try:
                await postgres_db.delete_session(session_id)
            except:
                pass
            raise e
            
    finally:
        # Cleanup user
        await postgres_db.delete_user(real_user_id)


@pytest.mark.property
@pytest.mark.asyncio
@given(
    ip_address=ip_address_strategy
)
@settings(
    max_examples=50,
    deadline=10000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_audited_mongo_operations_create_logs(
    postgres_db,
    mongodb,
    audited_mongo,
    audit_logger,
    ip_address: str
):
    """
    Feature: production-ready-browser-extension
    Property 14: Audit Log Creation for Data Access
    
    For any MongoDB operation through audited_mongo, an audit log
    should be automatically created in PostgreSQL.
    
    **Validates: Requirements 7.6, 17.7**
    """
    # Create a real user and session first
    real_user_id = await postgres_db.create_user(
        email=f"test_{uuid4()}@example.com",
        consent_given=True
    )
    session_id = await postgres_db.create_session(real_user_id, 'meet')
    
    try:
        # Create evidence through audited operations
        evidence_id = await audited_mongo.create_evidence(
            session_id=session_id,
            user_id=real_user_id,
            audio={"transcript": "Test transcript"},
            ip_address=ip_address
        )
        
        try:
            # Property 1: Evidence creation should create audit log
            create_logs = await audit_logger.get_resource_audit_trail('evidence', limit=10)
            create_log = next(
                (log for log in create_logs if log['action'] == 'write'),
                None
            )
            
            assert create_log is not None, "Evidence creation should create audit log"
            assert create_log['resource_type'] == 'evidence'
            
            # Read evidence through audited operations
            evidence_list = await audited_mongo.get_session_evidence(
                session_id=session_id,
                user_id=real_user_id,
                ip_address=ip_address
            )
            
            assert len(evidence_list) > 0, "Evidence should exist"
            
            # Property 2: Evidence read should create audit log
            read_logs = await audit_logger.get_resource_audit_trail('evidence', limit=10)
            read_log = next(
                (log for log in read_logs if log['action'] == 'read'),
                None
            )
            
            assert read_log is not None, "Evidence read should create audit log"
            
            # Delete evidence through audited operations
            delete_success = await audited_mongo.delete_evidence(
                evidence_id=evidence_id,
                user_id=real_user_id,
                ip_address=ip_address
            )
            
            assert delete_success is True, "Evidence deletion should succeed"
            
            # Property 3: Evidence deletion should create audit log
            delete_logs = await audit_logger.get_resource_audit_trail('evidence', limit=10)
            delete_log = next(
                (log for log in delete_logs if log['action'] == 'delete'),
                None
            )
            
            assert delete_log is not None, "Evidence deletion should create audit log"
            
        except Exception as e:
            # Cleanup evidence on error
            try:
                await mongodb.delete_evidence(evidence_id)
            except:
                pass
            raise e
            
    finally:
        # Cleanup session and user
        await postgres_db.delete_session(session_id)
        await postgres_db.delete_user(real_user_id)


@pytest.mark.property
@pytest.mark.asyncio
@given(
    action=action_strategy,
    resource_type=resource_type_strategy
)
@settings(
    max_examples=50,
    deadline=5000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_audit_log_with_null_user_id(
    postgres_db,
    audit_logger,
    action: str,
    resource_type: str
):
    """
    Feature: production-ready-browser-extension
    Property 14: Audit Log Creation for Data Access
    
    System operations (with null user_id) should also create audit logs.
    
    **Validates: Requirements 7.6, 17.7**
    """
    resource_id = uuid4()
    
    # Perform operation with null user_id (system operation)
    if action == 'read':
        log_id = await audit_logger.log_read(
            user_id=None,
            resource_type=resource_type,
            resource_id=resource_id
        )
    elif action == 'write':
        log_id = await audit_logger.log_write(
            user_id=None,
            resource_type=resource_type,
            resource_id=resource_id
        )
    else:  # delete
        log_id = await audit_logger.log_delete(
            user_id=None,
            resource_type=resource_type,
            resource_id=resource_id
        )
    
    # Property: System operations should create audit logs
    assert log_id is not None, "System operation should create audit log"
    
    # Verify log exists
    logs = await postgres_db.get_audit_logs(limit=10)
    system_log = next((log for log in logs if log['log_id'] == log_id), None)
    
    assert system_log is not None, "System audit log should exist"
    assert system_log['user_id'] is None, "System log should have null user_id"
    assert system_log['action'] == action
    assert system_log['resource_type'] == resource_type
