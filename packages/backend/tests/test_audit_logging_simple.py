"""
Simple unit tests for audit logging functionality

These tests verify that audit logging works correctly without complex async fixtures.
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from app.db.postgres import postgres_db
from app.db.mongodb import mongodb
from app.db.audit_logger import audit_logger
from app.db.audited_operations import audited_postgres, audited_mongo


class TestAuditLogging:
    """Test suite for audit logging"""
    
    @pytest.mark.asyncio
    async def test_audit_log_creation(self):
        """Test that audit logs can be created"""
        # Setup
        await postgres_db.connect()
        
        try:
            # Create a user first (required for foreign key)
            user_id = await postgres_db.create_user(
                email=f"test_{uuid4()}@example.com",
                consent_given=True
            )
            resource_id = uuid4()
            
            # Create audit log
            log_id = await audit_logger.log_write(
                user_id=user_id,
                resource_type='test_resource',
                resource_id=resource_id,
                ip_address='192.168.1.1',
                user_agent='Test Agent'
            )
            
            # Verify
            assert log_id is not None
            
            # Retrieve the log
            logs = await postgres_db.get_audit_logs(user_id=user_id, limit=1)
            assert len(logs) > 0
            assert logs[0]['action'] == 'write'
            assert logs[0]['resource_type'] == 'test_resource'
            assert str(logs[0]['ip_address']) == '192.168.1.1'
            
            # Cleanup
            await postgres_db.delete_user(user_id)
            
        finally:
            await postgres_db.disconnect()
    
    @pytest.mark.asyncio
    async def test_all_action_types_logged(self):
        """Test that read, write, and delete actions are all logged"""
        await postgres_db.connect()
        
        try:
            # Create a user first (required for foreign key)
            user_id = await postgres_db.create_user(
                email=f"test_{uuid4()}@example.com",
                consent_given=True
            )
            resource_id = uuid4()
            
            # Log all three action types
            read_log = await audit_logger.log_read(user_id, 'resource', resource_id)
            write_log = await audit_logger.log_write(user_id, 'resource', resource_id)
            delete_log = await audit_logger.log_delete(user_id, 'resource', resource_id)
            
            # Verify all were created
            assert read_log is not None
            assert write_log is not None
            assert delete_log is not None
            
            # Verify we can retrieve them
            logs = await audit_logger.get_user_audit_trail(user_id, limit=10)
            assert len(logs) >= 3
            
            actions = {log['action'] for log in logs if log['user_id'] == user_id}
            assert 'read' in actions
            assert 'write' in actions
            assert 'delete' in actions
            
            # Cleanup
            await postgres_db.delete_user(user_id)
            
        finally:
            await postgres_db.disconnect()
    
    @pytest.mark.asyncio
    async def test_audited_user_operations(self):
        """Test that user CRUD operations are audited"""
        await postgres_db.connect()
        
        try:
            email = f"test_{uuid4()}@example.com"
            ip_address = "10.0.0.1"
            
            # Create user with audit logging
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
            assert str(logs[0]['ip_address']) == ip_address
            
            # Read user with audit logging
            user = await audited_postgres.get_user(user_id, ip_address=ip_address)
            assert user is not None
            
            # Verify read was logged
            logs = await audit_logger.get_user_audit_trail(user_id, limit=2)
            assert len(logs) >= 2
            assert any(log['action'] == 'read' for log in logs)
            
            # Cleanup
            await postgres_db.delete_user(user_id)
            
        finally:
            await postgres_db.disconnect()
    
    @pytest.mark.asyncio
    async def test_audited_session_operations(self):
        """Test that session CRUD operations are audited"""
        await postgres_db.connect()
        
        try:
            # Create a user first
            user_id = await postgres_db.create_user(
                email=f"test_{uuid4()}@example.com",
                consent_given=True
            )
            
            # Create session with audit logging
            session_id = await audited_postgres.create_session(
                user_id=user_id,
                platform='meet',
                ip_address='10.0.0.2'
            )
            
            assert session_id is not None
            
            # Verify audit log was created
            logs = await audit_logger.get_resource_audit_trail('session', limit=1)
            assert len(logs) > 0
            assert logs[0]['action'] == 'write'
            assert logs[0]['resource_type'] == 'session'
            
            # Cleanup
            await postgres_db.delete_session(session_id)
            await postgres_db.delete_user(user_id)
            
        finally:
            await postgres_db.disconnect()
    
    @pytest.mark.asyncio
    async def test_audited_evidence_operations(self):
        """Test that evidence operations are audited"""
        await postgres_db.connect()
        await mongodb.connect()
        
        try:
            # Create user and session
            user_id = await postgres_db.create_user(
                email=f"test_{uuid4()}@example.com",
                consent_given=True
            )
            session_id = await postgres_db.create_session(user_id, 'zoom')
            
            # Create evidence with audit logging
            evidence_id = await audited_mongo.create_evidence(
                session_id=session_id,
                user_id=user_id,
                audio={"transcript": "Test transcript"},
                ip_address='10.0.0.3'
            )
            
            assert evidence_id is not None
            
            # Verify audit log was created
            logs = await audit_logger.get_resource_audit_trail('evidence', limit=1)
            assert len(logs) > 0
            assert logs[0]['action'] == 'write'
            assert logs[0]['resource_type'] == 'evidence'
            
            # Cleanup
            await mongodb.delete_evidence(evidence_id)
            await postgres_db.delete_session(session_id)
            await postgres_db.delete_user(user_id)
            
        finally:
            await postgres_db.disconnect()
            await mongodb.disconnect()
    
    @pytest.mark.asyncio
    async def test_audit_log_with_null_user_id(self):
        """Test that system operations (null user_id) are logged"""
        await postgres_db.connect()
        
        try:
            resource_id = uuid4()
            
            # Log system operation
            log_id = await audit_logger.log_write(
                user_id=None,  # System operation
                resource_type='system_config',
                resource_id=resource_id
            )
            
            assert log_id is not None
            
            # Verify log was created
            logs = await postgres_db.get_audit_logs(limit=1)
            assert len(logs) > 0
            # Find the log we just created
            system_log = next((log for log in logs if log['resource_type'] == 'system_config'), None)
            assert system_log is not None
            assert system_log['user_id'] is None
            
        finally:
            await postgres_db.disconnect()
    
    @pytest.mark.asyncio
    async def test_audit_log_has_timestamp(self):
        """Test that audit logs have timestamps"""
        await postgres_db.connect()
        
        try:
            # Create a user first (required for foreign key)
            user_id = await postgres_db.create_user(
                email=f"test_{uuid4()}@example.com",
                consent_given=True
            )
            
            await audit_logger.log_read(
                user_id=user_id,
                resource_type='test',
                resource_id=uuid4()
            )
            
            logs = await audit_logger.get_user_audit_trail(user_id, limit=1)
            assert len(logs) > 0
            
            # Verify timestamp exists and is a datetime object
            log_time = logs[0]['timestamp']
            assert log_time is not None
            assert isinstance(log_time, datetime)
            
            # Cleanup
            await postgres_db.delete_user(user_id)
            
        finally:
            await postgres_db.disconnect()
