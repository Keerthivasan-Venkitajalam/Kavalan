"""
Audit logging module for DPDP Act 2023 compliance

This module provides automatic audit logging for all data access operations
(read, write, delete) on user data. It wraps database operations and logs
them to the audit_logs table with timestamp, user_id, action, resource_id,
and IP address.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.db.postgres import postgres_db


class AuditLogger:
    """
    Audit logger for tracking all data access operations
    
    This class provides methods to log data access operations for DPDP compliance.
    All operations are logged with:
    - timestamp: When the operation occurred
    - user_id: Which user performed or was affected by the operation
    - action: Type of operation (read, write, delete)
    - resource_type: Type of resource accessed (user, session, threat_event, evidence, digital_fir)
    - resource_id: ID of the specific resource
    - ip_address: Client IP address (optional)
    - user_agent: Client user agent (optional)
    """
    
    def __init__(self):
        self.db = postgres_db
    
    async def log_read(
        self,
        user_id: Optional[UUID],
        resource_type: str,
        resource_id: Optional[UUID],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UUID:
        """
        Log a read operation
        
        Args:
            user_id: User who performed the read (None for system operations)
            resource_type: Type of resource read (e.g., 'user', 'session', 'threat_event')
            resource_id: ID of the resource read
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            UUID of created audit log entry
        """
        return await self.db.create_audit_log(
            user_id=user_id,
            action='read',
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def log_write(
        self,
        user_id: Optional[UUID],
        resource_type: str,
        resource_id: Optional[UUID],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UUID:
        """
        Log a write operation (create or update)
        
        Args:
            user_id: User who performed the write (None for system operations)
            resource_type: Type of resource written (e.g., 'user', 'session', 'threat_event')
            resource_id: ID of the resource written
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            UUID of created audit log entry
        """
        return await self.db.create_audit_log(
            user_id=user_id,
            action='write',
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def log_delete(
        self,
        user_id: Optional[UUID],
        resource_type: str,
        resource_id: Optional[UUID],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UUID:
        """
        Log a delete operation
        
        Args:
            user_id: User who performed the delete (None for system operations)
            resource_type: Type of resource deleted (e.g., 'user', 'session', 'threat_event')
            resource_id: ID of the resource deleted
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            UUID of created audit log entry
        """
        return await self.db.create_audit_log(
            user_id=user_id,
            action='delete',
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def get_user_audit_trail(
        self,
        user_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get complete audit trail for a user
        
        Args:
            user_id: User UUID
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log entries
        """
        return await self.db.get_audit_logs(user_id=user_id, limit=limit)
    
    async def get_resource_audit_trail(
        self,
        resource_type: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for a specific resource type
        
        Args:
            resource_type: Type of resource (e.g., 'user', 'session')
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log entries
        """
        return await self.db.get_audit_logs(resource_type=resource_type, limit=limit)
    
    async def get_action_audit_trail(
        self,
        action: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for a specific action type
        
        Args:
            action: Action type ('read', 'write', 'delete')
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log entries
        """
        return await self.db.get_audit_logs(action=action, limit=limit)


# Global audit logger instance
audit_logger = AuditLogger()
