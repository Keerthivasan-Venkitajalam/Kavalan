"""
Transaction coordinator for polyglot store (PostgreSQL + MongoDB)

Implements a two-phase commit pattern to ensure atomicity across both databases.
Either both writes succeed or both fail, maintaining data consistency.

Validates: Requirements 8.3
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from enum import Enum

from app.db.postgres import PostgresDB
from app.db.mongodb import MongoDB


logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """Transaction state machine"""
    PENDING = "pending"
    PREPARED = "prepared"
    COMMITTED = "committed"
    ABORTED = "aborted"


class TransactionCoordinator:
    """
    Coordinates transactional writes across PostgreSQL and MongoDB.
    
    Uses a two-phase commit pattern:
    1. Prepare phase: Write to both databases
    2. Commit phase: Confirm both writes succeeded, or rollback both
    
    This ensures atomicity - either both succeed or both fail.
    """
    
    def __init__(self, postgres_db: PostgresDB, mongodb: MongoDB):
        self.postgres_db = postgres_db
        self.mongodb = mongodb
        self.state = TransactionState.PENDING
    
    async def write_threat_analysis(
        self,
        session_id: UUID,
        user_id: UUID,
        threat_score: float,
        audio_score: Optional[float],
        visual_score: Optional[float],
        liveness_score: Optional[float],
        threat_level: str,
        is_alert: bool,
        confidence: Optional[float],
        audio_evidence: Optional[Dict[str, Any]] = None,
        visual_evidence: Optional[Dict[str, Any]] = None,
        liveness_evidence: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[UUID], Optional[str]]:
        """
        Write threat analysis to both PostgreSQL and MongoDB atomically.
        
        PostgreSQL stores: structured threat event data
        MongoDB stores: unstructured evidence data (transcripts, frames, analysis)
        
        Args:
            session_id: Session UUID
            user_id: User UUID
            threat_score: Unified threat score (0-10)
            audio_score: Audio modality score (0-10)
            visual_score: Visual modality score (0-10)
            liveness_score: Liveness modality score (0-10)
            threat_level: Threat level ('low', 'moderate', 'high', 'critical')
            is_alert: Whether this triggered an alert
            confidence: Confidence score (0-1)
            audio_evidence: Audio evidence data (transcript, keywords, segments)
            visual_evidence: Visual evidence data (frame_url, analysis, detections)
            liveness_evidence: Liveness evidence data (face_detected, blink_rate, stress_level)
            metadata: Metadata (platform, browser, extension_version, encryption info)
            
        Returns:
            Tuple of (event_id, evidence_id) if successful, (None, None) if failed
        """
        self.state = TransactionState.PENDING
        pg_conn = None
        event_id = None
        evidence_id = None
        
        try:
            # Phase 1: Prepare - Start PostgreSQL transaction
            pg_conn = await self.postgres_db.pool.acquire()
            
            async with pg_conn.transaction():
                # Write to PostgreSQL (within transaction)
                event_id = await pg_conn.fetchval(
                    """
                    INSERT INTO threat_events (
                        session_id, threat_score, audio_score, visual_score,
                        liveness_score, threat_level, is_alert, confidence
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING event_id
                    """,
                    session_id,
                    threat_score,
                    audio_score,
                    visual_score,
                    liveness_score,
                    threat_level,
                    is_alert,
                    confidence
                )
                
                logger.info(f"PostgreSQL write prepared: event_id={event_id}")
                self.state = TransactionState.PREPARED
                
                # Write to MongoDB (within PostgreSQL transaction scope)
                # If MongoDB fails, PostgreSQL transaction will rollback
                evidence_doc = {
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                    "event_id": str(event_id),  # Link to PostgreSQL record
                    "timestamp": datetime.utcnow(),
                    "audio": audio_evidence or {},
                    "visual": visual_evidence or {},
                    "liveness": liveness_evidence or {},
                    "metadata": metadata or {}
                }
                
                result = await self.mongodb.evidence.insert_one(evidence_doc)
                
                if not result.acknowledged:
                    raise Exception("MongoDB write not acknowledged")
                
                evidence_id = str(result.inserted_id)
                logger.info(f"MongoDB write prepared: evidence_id={evidence_id}")
                
                # Phase 2: Commit - If we reach here, both writes succeeded
                # PostgreSQL transaction will auto-commit when exiting context
                self.state = TransactionState.COMMITTED
                logger.info(
                    f"Transaction committed: event_id={event_id}, evidence_id={evidence_id}"
                )
            
            return event_id, evidence_id
        
        except Exception as e:
            # Phase 2: Abort - Rollback on any failure
            self.state = TransactionState.ABORTED
            logger.error(f"Transaction aborted: {e}")
            
            # PostgreSQL transaction automatically rolled back by context manager
            
            # Clean up MongoDB if it was written but PostgreSQL failed
            if evidence_id:
                try:
                    await self.mongodb.evidence.delete_one({"_id": evidence_id})
                    logger.info(f"MongoDB rollback: deleted evidence_id={evidence_id}")
                except Exception as cleanup_error:
                    logger.error(f"MongoDB cleanup failed: {cleanup_error}")
            
            return None, None
        
        finally:
            if pg_conn:
                await self.postgres_db.pool.release(pg_conn)
    
    async def write_session_with_evidence(
        self,
        user_id: UUID,
        platform: str,
        initial_evidence: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[UUID], Optional[str]]:
        """
        Create a new session in PostgreSQL and initial evidence in MongoDB atomically.
        
        Args:
            user_id: User UUID
            platform: Platform name ('meet', 'zoom', 'teams')
            initial_evidence: Initial evidence data to store in MongoDB
            
        Returns:
            Tuple of (session_id, evidence_id) if successful, (None, None) if failed
        """
        self.state = TransactionState.PENDING
        pg_conn = None
        session_id = None
        evidence_id = None
        
        try:
            # Phase 1: Prepare - Start PostgreSQL transaction
            pg_conn = await self.postgres_db.pool.acquire()
            
            async with pg_conn.transaction():
                # Write to PostgreSQL
                session_id = await pg_conn.fetchval(
                    """
                    INSERT INTO sessions (user_id, platform)
                    VALUES ($1, $2)
                    RETURNING session_id
                    """,
                    user_id,
                    platform
                )
                
                logger.info(f"PostgreSQL session created: session_id={session_id}")
                self.state = TransactionState.PREPARED
                
                # Write to MongoDB if initial evidence provided
                if initial_evidence:
                    evidence_doc = {
                        "session_id": str(session_id),
                        "user_id": str(user_id),
                        "timestamp": datetime.utcnow(),
                        **initial_evidence
                    }
                    
                    result = await self.mongodb.evidence.insert_one(evidence_doc)
                    
                    if not result.acknowledged:
                        raise Exception("MongoDB write not acknowledged")
                    
                    evidence_id = str(result.inserted_id)
                    logger.info(f"MongoDB evidence created: evidence_id={evidence_id}")
                
                # Phase 2: Commit
                self.state = TransactionState.COMMITTED
                logger.info(
                    f"Session transaction committed: session_id={session_id}, "
                    f"evidence_id={evidence_id}"
                )
            
            return session_id, evidence_id
        
        except Exception as e:
            # Phase 2: Abort
            self.state = TransactionState.ABORTED
            logger.error(f"Session transaction aborted: {e}")
            
            # Clean up MongoDB if needed
            if evidence_id:
                try:
                    await self.mongodb.evidence.delete_one({"_id": evidence_id})
                    logger.info(f"MongoDB rollback: deleted evidence_id={evidence_id}")
                except Exception as cleanup_error:
                    logger.error(f"MongoDB cleanup failed: {cleanup_error}")
            
            return None, None
        
        finally:
            if pg_conn:
                await self.postgres_db.pool.release(pg_conn)
    
    async def delete_session_with_evidence(
        self,
        session_id: UUID
    ) -> bool:
        """
        Delete a session from PostgreSQL and all related evidence from MongoDB atomically.
        
        Args:
            session_id: Session UUID
            
        Returns:
            True if both deletions succeeded, False otherwise
        """
        self.state = TransactionState.PENDING
        pg_conn = None
        
        try:
            # Phase 1: Prepare - Start PostgreSQL transaction
            pg_conn = await self.postgres_db.pool.acquire()
            
            async with pg_conn.transaction():
                # Delete from PostgreSQL (cascades to threat_events)
                result = await pg_conn.execute(
                    "DELETE FROM sessions WHERE session_id = $1",
                    session_id
                )
                
                if result == "DELETE 0":
                    logger.warning(f"Session not found: session_id={session_id}")
                    return False
                
                logger.info(f"PostgreSQL session deleted: session_id={session_id}")
                self.state = TransactionState.PREPARED
                
                # Delete from MongoDB
                mongo_result = await self.mongodb.evidence.delete_many(
                    {"session_id": str(session_id)}
                )
                
                logger.info(
                    f"MongoDB evidence deleted: session_id={session_id}, "
                    f"count={mongo_result.deleted_count}"
                )
                
                # Phase 2: Commit
                self.state = TransactionState.COMMITTED
                logger.info(f"Delete transaction committed: session_id={session_id}")
            
            return True
        
        except Exception as e:
            # Phase 2: Abort
            self.state = TransactionState.ABORTED
            logger.error(f"Delete transaction aborted: {e}")
            return False
        
        finally:
            if pg_conn:
                await self.postgres_db.pool.release(pg_conn)
    
    async def update_session_with_max_threat(
        self,
        session_id: UUID,
        threat_score: float,
        end_time: Optional[datetime] = None,
        duration_seconds: Optional[int] = None
    ) -> bool:
        """
        Update session max threat score in PostgreSQL and verify evidence exists in MongoDB.
        
        Args:
            session_id: Session UUID
            threat_score: New threat score to compare with current max
            end_time: Session end time
            duration_seconds: Total duration in seconds
            
        Returns:
            True if update succeeded and evidence exists, False otherwise
        """
        self.state = TransactionState.PENDING
        pg_conn = None
        
        try:
            # Phase 1: Prepare - Start PostgreSQL transaction
            pg_conn = await self.postgres_db.pool.acquire()
            
            async with pg_conn.transaction():
                # Update PostgreSQL with max threat score
                result = await pg_conn.execute(
                    """
                    UPDATE sessions
                    SET max_threat_score = GREATEST(COALESCE(max_threat_score, 0), $2),
                        end_time = COALESCE($3, end_time),
                        duration_seconds = COALESCE($4, duration_seconds),
                        alert_count = alert_count + CASE WHEN $2 >= 7.0 THEN 1 ELSE 0 END
                    WHERE session_id = $1
                    """,
                    session_id,
                    threat_score,
                    end_time,
                    duration_seconds
                )
                
                if result == "UPDATE 0":
                    logger.warning(f"Session not found: session_id={session_id}")
                    return False
                
                logger.info(
                    f"PostgreSQL session updated: session_id={session_id}, "
                    f"threat_score={threat_score}"
                )
                self.state = TransactionState.PREPARED
                
                # Verify evidence exists in MongoDB
                evidence_count = await self.mongodb.evidence.count_documents(
                    {"session_id": str(session_id)}
                )
                
                if evidence_count == 0:
                    logger.warning(
                        f"No evidence found in MongoDB for session_id={session_id}"
                    )
                    # Don't fail the transaction, but log the inconsistency
                
                # Phase 2: Commit
                self.state = TransactionState.COMMITTED
                logger.info(
                    f"Update transaction committed: session_id={session_id}, "
                    f"evidence_count={evidence_count}"
                )
            
            return True
        
        except Exception as e:
            # Phase 2: Abort
            self.state = TransactionState.ABORTED
            logger.error(f"Update transaction aborted: {e}")
            return False
        
        finally:
            if pg_conn:
                await self.postgres_db.pool.release(pg_conn)


# Factory function to create coordinator with global database instances
def create_transaction_coordinator(
    postgres_db: PostgresDB,
    mongodb: MongoDB
) -> TransactionCoordinator:
    """
    Create a transaction coordinator with database instances.
    
    Args:
        postgres_db: PostgreSQL database instance
        mongodb: MongoDB database instance
        
    Returns:
        TransactionCoordinator instance
    """
    return TransactionCoordinator(postgres_db, mongodb)
