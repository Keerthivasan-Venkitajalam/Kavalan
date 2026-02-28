"""
PostgreSQL database connection and operations
"""
import asyncpg
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from app.config import settings


class PostgresDB:
    """PostgreSQL database manager with connection pooling"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = database_url or settings.DATABASE_URL
    
    async def connect(self):
        """Create connection pool"""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def execute(self, query: str, *args):
        """Execute a query"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch single row"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    # ==================== USERS TABLE CRUD ====================
    
    async def create_user(
        self,
        email: str,
        preferences: Optional[Dict[str, Any]] = None,
        consent_given: bool = False
    ) -> UUID:
        """
        Create a new user
        
        Args:
            email: User email address
            preferences: User preferences as JSON
            consent_given: Whether user gave DPDP consent
            
        Returns:
            UUID of created user
        """
        query = """
            INSERT INTO users (email, preferences, consent_given, consent_timestamp)
            VALUES ($1, $2::jsonb, $3, $4)
            RETURNING user_id
        """
        consent_timestamp = datetime.now() if consent_given else None
        preferences_json = json.dumps(preferences or {})
        
        row = await self.fetchrow(
            query,
            email,
            preferences_json,
            consent_given,
            consent_timestamp
        )
        return row['user_id']
    
    async def get_user(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get user by ID
        
        Args:
            user_id: User UUID
            
        Returns:
            User record as dict or None if not found
        """
        query = """
            SELECT user_id, email, created_at, last_active, 
                   preferences, consent_given, consent_timestamp
            FROM users
            WHERE user_id = $1
        """
        row = await self.fetchrow(query, user_id)
        if not row:
            return None
        
        result = dict(row)
        # Parse JSONB field if it's a string
        if isinstance(result.get('preferences'), str):
            result['preferences'] = json.loads(result['preferences'])
        return result
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email
        
        Args:
            email: User email address
            
        Returns:
            User record as dict or None if not found
        """
        query = """
            SELECT user_id, email, created_at, last_active, 
                   preferences, consent_given, consent_timestamp
            FROM users
            WHERE email = $1
        """
        row = await self.fetchrow(query, email)
        if not row:
            return None
        
        result = dict(row)
        # Parse JSONB field if it's a string
        if isinstance(result.get('preferences'), str):
            result['preferences'] = json.loads(result['preferences'])
        return result
    
    async def update_user(
        self,
        user_id: UUID,
        preferences: Optional[Dict[str, Any]] = None,
        last_active: Optional[datetime] = None
    ) -> bool:
        """
        Update user preferences and last active time
        
        Args:
            user_id: User UUID
            preferences: Updated preferences
            last_active: Last active timestamp
            
        Returns:
            True if user was updated, False if not found
        """
        preferences_json = json.dumps(preferences) if preferences is not None else None
        
        query = """
            UPDATE users
            SET preferences = COALESCE($2::jsonb, preferences),
                last_active = COALESCE($3, last_active)
            WHERE user_id = $1
        """
        result = await self.execute(query, user_id, preferences_json, last_active)
        return result != "UPDATE 0"
    
    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete user (cascades to sessions, threat_events)
        
        Args:
            user_id: User UUID
            
        Returns:
            True if user was deleted, False if not found
        """
        query = "DELETE FROM users WHERE user_id = $1"
        result = await self.execute(query, user_id)
        return result != "DELETE 0"
    
    # ==================== SESSIONS TABLE CRUD ====================
    
    async def create_session(
        self,
        user_id: UUID,
        platform: str
    ) -> UUID:
        """
        Create a new session
        
        Args:
            user_id: User UUID
            platform: Platform name ('meet', 'zoom', 'teams')
            
        Returns:
            UUID of created session
        """
        query = """
            INSERT INTO sessions (user_id, platform)
            VALUES ($1, $2)
            RETURNING session_id
        """
        row = await self.fetchrow(query, user_id, platform)
        return row['session_id']
    
    async def get_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get session by ID
        
        Args:
            session_id: Session UUID
            
        Returns:
            Session record as dict or None if not found
        """
        query = """
            SELECT session_id, user_id, platform, start_time, end_time,
                   duration_seconds, max_threat_score, alert_count
            FROM sessions
            WHERE session_id = $1
        """
        row = await self.fetchrow(query, session_id)
        return dict(row) if row else None
    
    async def get_user_sessions(
        self,
        user_id: UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user
        
        Args:
            user_id: User UUID
            limit: Maximum number of sessions to return
            
        Returns:
            List of session records
        """
        query = """
            SELECT session_id, user_id, platform, start_time, end_time,
                   duration_seconds, max_threat_score, alert_count
            FROM sessions
            WHERE user_id = $1
            ORDER BY start_time DESC
            LIMIT $2
        """
        rows = await self.fetch(query, user_id, limit)
        return [dict(row) for row in rows]
    
    async def update_session(
        self,
        session_id: UUID,
        end_time: Optional[datetime] = None,
        duration_seconds: Optional[int] = None,
        max_threat_score: Optional[float] = None,
        alert_count: Optional[int] = None
    ) -> bool:
        """
        Update session details
        
        Args:
            session_id: Session UUID
            end_time: Session end time
            duration_seconds: Total duration in seconds
            max_threat_score: Maximum threat score during session
            alert_count: Number of alerts triggered
            
        Returns:
            True if session was updated, False if not found
        """
        query = """
            UPDATE sessions
            SET end_time = COALESCE($2, end_time),
                duration_seconds = COALESCE($3, duration_seconds),
                max_threat_score = COALESCE($4, max_threat_score),
                alert_count = COALESCE($5, alert_count)
            WHERE session_id = $1
        """
        result = await self.execute(
            query,
            session_id,
            end_time,
            duration_seconds,
            max_threat_score,
            alert_count
        )
        return result != "UPDATE 0"
    
    async def delete_session(self, session_id: UUID) -> bool:
        """
        Delete session (cascades to threat_events)
        
        Args:
            session_id: Session UUID
            
        Returns:
            True if session was deleted, False if not found
        """
        query = "DELETE FROM sessions WHERE session_id = $1"
        result = await self.execute(query, session_id)
        return result != "DELETE 0"
    
    # ==================== THREAT_EVENTS TABLE CRUD ====================
    
    async def create_threat_event(
        self,
        session_id: UUID,
        threat_score: float,
        audio_score: Optional[float],
        visual_score: Optional[float],
        liveness_score: Optional[float],
        threat_level: str,
        is_alert: bool,
        confidence: Optional[float]
    ) -> UUID:
        """
        Create a new threat event
        
        Args:
            session_id: Session UUID
            threat_score: Unified threat score (0-10)
            audio_score: Audio modality score (0-10)
            visual_score: Visual modality score (0-10)
            liveness_score: Liveness modality score (0-10)
            threat_level: Threat level ('low', 'moderate', 'high', 'critical')
            is_alert: Whether this triggered an alert
            confidence: Confidence score (0-1)
            
        Returns:
            UUID of created threat event
        """
        query = """
            INSERT INTO threat_events (
                session_id, threat_score, audio_score, visual_score,
                liveness_score, threat_level, is_alert, confidence
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING event_id
        """
        row = await self.fetchrow(
            query,
            session_id,
            threat_score,
            audio_score,
            visual_score,
            liveness_score,
            threat_level,
            is_alert,
            confidence
        )
        return row['event_id']
    
    async def get_threat_event(self, event_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get threat event by ID
        
        Args:
            event_id: Event UUID
            
        Returns:
            Threat event record as dict or None if not found
        """
        query = """
            SELECT event_id, session_id, timestamp, threat_score,
                   audio_score, visual_score, liveness_score,
                   threat_level, is_alert, confidence
            FROM threat_events
            WHERE event_id = $1
        """
        row = await self.fetchrow(query, event_id)
        return dict(row) if row else None
    
    async def get_session_threat_events(
        self,
        session_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all threat events for a session
        
        Args:
            session_id: Session UUID
            limit: Maximum number of events to return
            
        Returns:
            List of threat event records
        """
        query = """
            SELECT event_id, session_id, timestamp, threat_score,
                   audio_score, visual_score, liveness_score,
                   threat_level, is_alert, confidence
            FROM threat_events
            WHERE session_id = $1
            ORDER BY timestamp DESC
            LIMIT $2
        """
        rows = await self.fetch(query, session_id, limit)
        return [dict(row) for row in rows]
    
    async def get_high_threat_events(
        self,
        min_score: float = 7.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get high-threat events across all sessions
        
        Args:
            min_score: Minimum threat score threshold
            limit: Maximum number of events to return
            
        Returns:
            List of threat event records
        """
        query = """
            SELECT event_id, session_id, timestamp, threat_score,
                   audio_score, visual_score, liveness_score,
                   threat_level, is_alert, confidence
            FROM threat_events
            WHERE threat_score >= $1
            ORDER BY timestamp DESC
            LIMIT $2
        """
        rows = await self.fetch(query, min_score, limit)
        return [dict(row) for row in rows]
    
    async def delete_threat_event(self, event_id: UUID) -> bool:
        """
        Delete threat event
        
        Args:
            event_id: Event UUID
            
        Returns:
            True if event was deleted, False if not found
        """
        query = "DELETE FROM threat_events WHERE event_id = $1"
        result = await self.execute(query, event_id)
        return result != "DELETE 0"
    
    # ==================== AUDIT_LOGS TABLE CRUD ====================
    
    async def create_audit_log(
        self,
        user_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[UUID],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UUID:
        """
        Create an audit log entry (DPDP compliance)
        
        Args:
            user_id: User UUID (can be None for system actions)
            action: Action performed (e.g., 'read', 'write', 'delete')
            resource_type: Type of resource (e.g., 'user', 'session', 'threat_event')
            resource_id: UUID of the resource
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            UUID of created audit log
        """
        query = """
            INSERT INTO audit_logs (
                user_id, action, resource_type, resource_id,
                ip_address, user_agent
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING log_id
        """
        row = await self.fetchrow(
            query,
            user_id,
            action,
            resource_type,
            resource_id,
            ip_address,
            user_agent
        )
        return row['log_id']
    
    async def get_audit_logs(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs with optional filters
        
        Args:
            user_id: Filter by user UUID
            action: Filter by action type
            resource_type: Filter by resource type
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log records
        """
        conditions = []
        params = []
        param_count = 1
        
        if user_id is not None:
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)
            param_count += 1
        
        if action is not None:
            conditions.append(f"action = ${param_count}")
            params.append(action)
            param_count += 1
        
        if resource_type is not None:
            conditions.append(f"resource_type = ${param_count}")
            params.append(resource_type)
            param_count += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        params.append(limit)
        
        query = f"""
            SELECT log_id, user_id, action, resource_type, resource_id,
                   timestamp, ip_address, user_agent
            FROM audit_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_count}
        """
        
        rows = await self.fetch(query, *params)
        return [dict(row) for row in rows]
    
    async def delete_old_audit_logs(self, days: int = 90) -> int:
        """
        Delete audit logs older than specified days
        
        Args:
            days: Number of days to retain
            
        Returns:
            Number of logs deleted
        """
        query = """
            DELETE FROM audit_logs
            WHERE timestamp < NOW() - INTERVAL '%s days'
        """
        result = await self.execute(query, days)
        # Extract count from result string like "DELETE 42"
        return int(result.split()[-1]) if result else 0


# Global database instance
postgres_db = PostgresDB()
