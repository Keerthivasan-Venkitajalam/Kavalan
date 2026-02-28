"""
Audited database operations wrapper

This module wraps PostgreSQL and MongoDB operations with automatic audit logging.
All data access operations (read, write, delete) are logged for DPDP compliance.
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.db.postgres import postgres_db
from app.db.mongodb import mongodb
from app.db.audit_logger import audit_logger


class AuditedPostgresOperations:
    """
    PostgreSQL operations with automatic audit logging
    
    This class wraps all PostgreSQL CRUD operations and automatically logs
    them to the audit_logs table for DPDP Act 2023 compliance.
    """
    
    def __init__(self):
        self.db = postgres_db
        self.audit = audit_logger
    
    # ==================== USERS TABLE WITH AUDIT LOGGING ====================
    
    async def create_user(
        self,
        email: str,
        preferences: Optional[Dict[str, Any]] = None,
        consent_given: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UUID:
        """Create user with audit logging"""
        user_id = await self.db.create_user(email, preferences, consent_given)
        await self.audit.log_write(
            user_id=user_id,
            resource_type='user',
            resource_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return user_id
    
    async def get_user(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get user with audit logging"""
        user = await self.db.get_user(user_id)
        if user:
            await self.audit.log_read(
                user_id=user_id,
                resource_type='user',
                resource_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return user
    
    async def get_user_by_email(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get user by email with audit logging"""
        user = await self.db.get_user_by_email(email)
        if user:
            await self.audit.log_read(
                user_id=user['user_id'],
                resource_type='user',
                resource_id=user['user_id'],
                ip_address=ip_address,
                user_agent=user_agent
            )
        return user
    
    async def update_user(
        self,
        user_id: UUID,
        preferences: Optional[Dict[str, Any]] = None,
        last_active: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Update user with audit logging"""
        success = await self.db.update_user(user_id, preferences, last_active)
        if success:
            await self.audit.log_write(
                user_id=user_id,
                resource_type='user',
                resource_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return success
    
    async def delete_user(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Delete user with audit logging"""
        success = await self.db.delete_user(user_id)
        if success:
            await self.audit.log_delete(
                user_id=user_id,
                resource_type='user',
                resource_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return success
    
    # ==================== SESSIONS TABLE WITH AUDIT LOGGING ====================
    
    async def create_session(
        self,
        user_id: UUID,
        platform: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UUID:
        """Create session with audit logging"""
        session_id = await self.db.create_session(user_id, platform)
        await self.audit.log_write(
            user_id=user_id,
            resource_type='session',
            resource_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return session_id
    
    async def get_session(
        self,
        session_id: UUID,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get session with audit logging"""
        session = await self.db.get_session(session_id)
        if session:
            await self.audit.log_read(
                user_id=user_id or session.get('user_id'),
                resource_type='session',
                resource_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return session
    
    async def get_user_sessions(
        self,
        user_id: UUID,
        limit: int = 50,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user sessions with audit logging"""
        sessions = await self.db.get_user_sessions(user_id, limit)
        if sessions:
            await self.audit.log_read(
                user_id=user_id,
                resource_type='session',
                resource_id=None,  # Multiple resources
                ip_address=ip_address,
                user_agent=user_agent
            )
        return sessions
    
    async def update_session(
        self,
        session_id: UUID,
        user_id: Optional[UUID] = None,
        end_time: Optional[datetime] = None,
        duration_seconds: Optional[int] = None,
        max_threat_score: Optional[float] = None,
        alert_count: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Update session with audit logging"""
        success = await self.db.update_session(
            session_id, end_time, duration_seconds, max_threat_score, alert_count
        )
        if success:
            await self.audit.log_write(
                user_id=user_id,
                resource_type='session',
                resource_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return success
    
    async def delete_session(
        self,
        session_id: UUID,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Delete session with audit logging"""
        success = await self.db.delete_session(session_id)
        if success:
            await self.audit.log_delete(
                user_id=user_id,
                resource_type='session',
                resource_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return success
    
    # ==================== THREAT_EVENTS TABLE WITH AUDIT LOGGING ====================
    
    async def create_threat_event(
        self,
        session_id: UUID,
        user_id: Optional[UUID],
        threat_score: float,
        audio_score: Optional[float],
        visual_score: Optional[float],
        liveness_score: Optional[float],
        threat_level: str,
        is_alert: bool,
        confidence: Optional[float],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UUID:
        """Create threat event with audit logging"""
        event_id = await self.db.create_threat_event(
            session_id, threat_score, audio_score, visual_score,
            liveness_score, threat_level, is_alert, confidence
        )
        await self.audit.log_write(
            user_id=user_id,
            resource_type='threat_event',
            resource_id=event_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return event_id
    
    async def get_threat_event(
        self,
        event_id: UUID,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get threat event with audit logging"""
        event = await self.db.get_threat_event(event_id)
        if event:
            await self.audit.log_read(
                user_id=user_id,
                resource_type='threat_event',
                resource_id=event_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return event
    
    async def get_session_threat_events(
        self,
        session_id: UUID,
        user_id: Optional[UUID] = None,
        limit: int = 100,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get session threat events with audit logging"""
        events = await self.db.get_session_threat_events(session_id, limit)
        if events:
            await self.audit.log_read(
                user_id=user_id,
                resource_type='threat_event',
                resource_id=None,  # Multiple resources
                ip_address=ip_address,
                user_agent=user_agent
            )
        return events
    
    async def delete_threat_event(
        self,
        event_id: UUID,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Delete threat event with audit logging"""
        success = await self.db.delete_threat_event(event_id)
        if success:
            await self.audit.log_delete(
                user_id=user_id,
                resource_type='threat_event',
                resource_id=event_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return success


class AuditedMongoOperations:
    """
    MongoDB operations with automatic audit logging
    
    This class wraps all MongoDB CRUD operations and automatically logs
    them to the PostgreSQL audit_logs table for DPDP Act 2023 compliance.
    """
    
    def __init__(self):
        self.db = mongodb
        self.audit = audit_logger
    
    # ==================== EVIDENCE COLLECTION WITH AUDIT LOGGING ====================
    
    async def create_evidence(
        self,
        session_id: UUID,
        user_id: UUID,
        audio: Optional[Dict[str, Any]] = None,
        visual: Optional[Dict[str, Any]] = None,
        liveness: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Create evidence with audit logging"""
        evidence_id = await self.db.create_evidence(
            session_id, user_id, audio, visual, liveness, metadata
        )
        # Log to audit table (use session_id as resource_id since evidence uses ObjectId)
        await self.audit.log_write(
            user_id=user_id,
            resource_type='evidence',
            resource_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return evidence_id
    
    async def get_evidence(
        self,
        evidence_id: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get evidence with audit logging"""
        evidence = await self.db.get_evidence(evidence_id)
        if evidence:
            await self.audit.log_read(
                user_id=user_id,
                resource_type='evidence',
                resource_id=None,  # ObjectId, not UUID
                ip_address=ip_address,
                user_agent=user_agent
            )
        return evidence
    
    async def get_session_evidence(
        self,
        session_id: UUID,
        user_id: Optional[UUID] = None,
        limit: int = 100,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get session evidence with audit logging"""
        evidence_list = await self.db.get_session_evidence(session_id, limit)
        if evidence_list:
            await self.audit.log_read(
                user_id=user_id,
                resource_type='evidence',
                resource_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return evidence_list
    
    async def delete_evidence(
        self,
        evidence_id: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Delete evidence with audit logging"""
        success = await self.db.delete_evidence(evidence_id)
        if success:
            await self.audit.log_delete(
                user_id=user_id,
                resource_type='evidence',
                resource_id=None,  # ObjectId, not UUID
                ip_address=ip_address,
                user_agent=user_agent
            )
        return success
    
    async def delete_session_evidence(
        self,
        session_id: UUID,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """Delete session evidence with audit logging"""
        count = await self.db.delete_session_evidence(session_id)
        if count > 0:
            await self.audit.log_delete(
                user_id=user_id,
                resource_type='evidence',
                resource_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return count
    
    # ==================== DIGITAL FIR COLLECTION WITH AUDIT LOGGING ====================
    
    async def create_digital_fir(
        self,
        fir_id: str,
        session_id: UUID,
        user_id: UUID,
        summary: Dict[str, Any],
        evidence: Dict[str, Any],
        legal: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Create Digital FIR with audit logging"""
        object_id = await self.db.create_digital_fir(
            fir_id, session_id, user_id, summary, evidence, legal
        )
        await self.audit.log_write(
            user_id=user_id,
            resource_type='digital_fir',
            resource_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return object_id
    
    async def get_digital_fir(
        self,
        fir_id: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get Digital FIR with audit logging and chain-of-custody tracking"""
        # Determine actor for chain-of-custody
        actor = str(user_id) if user_id else "anonymous"
        
        fir = await self.db.get_digital_fir(fir_id, actor=actor, track_access=True)
        if fir:
            await self.audit.log_read(
                user_id=user_id,
                resource_type='digital_fir',
                resource_id=None,  # FIR ID is string, not UUID
                ip_address=ip_address,
                user_agent=user_agent
            )
        return fir
    
    async def get_session_digital_fir(
        self,
        session_id: UUID,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get session Digital FIR with audit logging and chain-of-custody tracking"""
        # Determine actor for chain-of-custody
        actor = str(user_id) if user_id else "anonymous"
        
        fir = await self.db.get_session_digital_fir(session_id, actor=actor, track_access=True)
        if fir:
            await self.audit.log_read(
                user_id=user_id,
                resource_type='digital_fir',
                resource_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        return fir
    
    async def delete_digital_fir(
        self,
        fir_id: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Delete Digital FIR with audit logging"""
        success = await self.db.delete_digital_fir(fir_id)
        if success:
            await self.audit.log_delete(
                user_id=user_id,
                resource_type='digital_fir',
                resource_id=None,  # FIR ID is string, not UUID
                ip_address=ip_address,
                user_agent=user_agent
            )
        return success


# Global audited operations instances
audited_postgres = AuditedPostgresOperations()
audited_mongo = AuditedMongoOperations()
