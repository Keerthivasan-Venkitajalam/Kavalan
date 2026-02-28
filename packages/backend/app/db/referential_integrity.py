"""
Referential integrity checker for polyglot store (PostgreSQL + MongoDB)

Validates that MongoDB references correctly point to existing PostgreSQL records
and that session_id consistency is maintained across both stores.

Validates: Requirements 8.4
"""
import logging
from typing import List, Dict, Any, Optional, Set
from uuid import UUID
from dataclasses import dataclass

from app.db.postgres import PostgresDB
from app.db.mongodb import MongoDB


logger = logging.getLogger(__name__)


@dataclass
class IntegrityViolation:
    """Represents a referential integrity violation"""
    violation_type: str
    description: str
    postgres_id: Optional[UUID] = None
    mongodb_id: Optional[str] = None
    session_id: Optional[UUID] = None
    details: Optional[Dict[str, Any]] = None


class ReferentialIntegrityChecker:
    """
    Checks referential integrity between PostgreSQL and MongoDB.
    
    Ensures that:
    1. MongoDB evidence records reference existing PostgreSQL sessions
    2. MongoDB evidence records reference existing PostgreSQL threat events (when event_id present)
    3. session_id values are consistent between stores
    4. No orphaned records exist in either store
    """
    
    def __init__(self, postgres_db: PostgresDB, mongodb: MongoDB):
        self.postgres_db = postgres_db
        self.mongodb = mongodb
    
    async def check_evidence_session_references(
        self,
        limit: Optional[int] = None
    ) -> List[IntegrityViolation]:
        """
        Check that all MongoDB evidence records reference existing PostgreSQL sessions.
        
        Args:
            limit: Maximum number of evidence records to check (None = check all)
            
        Returns:
            List of integrity violations found
        """
        violations = []
        
        # Get all evidence records from MongoDB
        cursor = self.mongodb.evidence.find({})
        if limit:
            cursor = cursor.limit(limit)
        
        checked_count = 0
        async for evidence in cursor:
            checked_count += 1
            evidence_id = str(evidence["_id"])
            session_id_str = evidence.get("session_id")
            
            if not session_id_str or session_id_str == "":
                violations.append(IntegrityViolation(
                    violation_type="missing_session_id",
                    description="Evidence record missing or empty session_id field",
                    mongodb_id=evidence_id
                ))
                continue
            
            try:
                session_id = UUID(session_id_str)
            except (ValueError, AttributeError):
                violations.append(IntegrityViolation(
                    violation_type="invalid_session_id",
                    description=f"Evidence has invalid session_id format: {session_id_str}",
                    mongodb_id=evidence_id,
                    details={"session_id_str": session_id_str}
                ))
                continue
            
            # Check if PostgreSQL session exists
            pg_session = await self.postgres_db.get_session(session_id)
            if pg_session is None:
                violations.append(IntegrityViolation(
                    violation_type="dangling_session_reference",
                    description=f"Evidence references non-existent session",
                    mongodb_id=evidence_id,
                    session_id=session_id,
                    details={"session_id": str(session_id)}
                ))
        
        logger.info(
            f"Checked {checked_count} evidence records, "
            f"found {len(violations)} session reference violations"
        )
        return violations
    
    async def check_evidence_event_references(
        self,
        limit: Optional[int] = None
    ) -> List[IntegrityViolation]:
        """
        Check that MongoDB evidence records with event_id reference existing PostgreSQL events.
        
        Args:
            limit: Maximum number of evidence records to check (None = check all)
            
        Returns:
            List of integrity violations found
        """
        violations = []
        
        # Get evidence records that have event_id field
        cursor = self.mongodb.evidence.find({"event_id": {"$exists": True}})
        if limit:
            cursor = cursor.limit(limit)
        
        checked_count = 0
        async for evidence in cursor:
            checked_count += 1
            evidence_id = str(evidence["_id"])
            event_id_str = evidence.get("event_id")
            
            if not event_id_str:
                continue  # event_id field exists but is null/empty
            
            try:
                event_id = UUID(event_id_str)
            except (ValueError, AttributeError):
                violations.append(IntegrityViolation(
                    violation_type="invalid_event_id",
                    description=f"Evidence has invalid event_id format: {event_id_str}",
                    mongodb_id=evidence_id,
                    details={"event_id_str": event_id_str}
                ))
                continue
            
            # Check if PostgreSQL threat event exists
            pg_event = await self.postgres_db.get_threat_event(event_id)
            if pg_event is None:
                violations.append(IntegrityViolation(
                    violation_type="dangling_event_reference",
                    description=f"Evidence references non-existent threat event",
                    mongodb_id=evidence_id,
                    postgres_id=event_id,
                    details={"event_id": str(event_id)}
                ))
        
        logger.info(
            f"Checked {checked_count} evidence records with event_id, "
            f"found {len(violations)} event reference violations"
        )
        return violations
    
    async def check_session_id_consistency(
        self,
        session_id: UUID
    ) -> List[IntegrityViolation]:
        """
        Check session_id consistency for a specific session.
        
        Verifies that:
        1. PostgreSQL session exists
        2. All MongoDB evidence for this session has matching session_id
        3. All PostgreSQL threat events for this session exist
        4. MongoDB evidence references match PostgreSQL events
        
        Args:
            session_id: Session UUID to check
            
        Returns:
            List of integrity violations found
        """
        violations = []
        
        # Check PostgreSQL session exists
        pg_session = await self.postgres_db.get_session(session_id)
        if pg_session is None:
            violations.append(IntegrityViolation(
                violation_type="missing_session",
                description=f"Session does not exist in PostgreSQL",
                session_id=session_id
            ))
            return violations  # Can't check further without session
        
        # Get all MongoDB evidence for this session
        mongo_evidence = await self.mongodb.get_session_evidence(session_id)
        
        # Check each evidence record
        for evidence in mongo_evidence:
            evidence_id = evidence["_id"]
            evidence_session_id_str = evidence.get("session_id")
            
            # Verify session_id matches
            if evidence_session_id_str != str(session_id):
                violations.append(IntegrityViolation(
                    violation_type="session_id_mismatch",
                    description=f"Evidence session_id doesn't match query session_id",
                    mongodb_id=evidence_id,
                    session_id=session_id,
                    details={
                        "expected": str(session_id),
                        "actual": evidence_session_id_str
                    }
                ))
            
            # If evidence has event_id, verify it references a valid event for this session
            event_id_str = evidence.get("event_id")
            if event_id_str:
                try:
                    event_id = UUID(event_id_str)
                    pg_event = await self.postgres_db.get_threat_event(event_id)
                    
                    if pg_event is None:
                        violations.append(IntegrityViolation(
                            violation_type="dangling_event_reference",
                            description=f"Evidence references non-existent event",
                            mongodb_id=evidence_id,
                            postgres_id=event_id,
                            session_id=session_id
                        ))
                    elif pg_event["session_id"] != session_id:
                        violations.append(IntegrityViolation(
                            violation_type="event_session_mismatch",
                            description=f"Event belongs to different session",
                            mongodb_id=evidence_id,
                            postgres_id=event_id,
                            session_id=session_id,
                            details={
                                "event_session_id": str(pg_event["session_id"]),
                                "evidence_session_id": str(session_id)
                            }
                        ))
                except (ValueError, AttributeError):
                    violations.append(IntegrityViolation(
                        violation_type="invalid_event_id",
                        description=f"Evidence has invalid event_id format",
                        mongodb_id=evidence_id,
                        session_id=session_id,
                        details={"event_id_str": event_id_str}
                    ))
        
        # Get all PostgreSQL threat events for this session
        pg_events = await self.postgres_db.get_session_threat_events(session_id)
        
        # Check that each event has corresponding evidence (optional check)
        # Note: Not all events may have evidence, so this is informational
        event_ids_with_evidence = set()
        for evidence in mongo_evidence:
            event_id_str = evidence.get("event_id")
            if event_id_str:
                event_ids_with_evidence.add(event_id_str)
        
        for pg_event in pg_events:
            event_id = pg_event["event_id"]
            if str(event_id) not in event_ids_with_evidence:
                # This is not necessarily a violation - events may not have evidence yet
                logger.debug(
                    f"Event {event_id} in session {session_id} has no evidence record"
                )
        
        logger.info(
            f"Checked session {session_id} consistency, "
            f"found {len(violations)} violations"
        )
        return violations
    
    async def check_orphaned_evidence(
        self,
        limit: Optional[int] = None
    ) -> List[IntegrityViolation]:
        """
        Find MongoDB evidence records that reference non-existent PostgreSQL sessions.
        
        This is a comprehensive check that identifies orphaned evidence that should
        be cleaned up.
        
        Args:
            limit: Maximum number of evidence records to check (None = check all)
            
        Returns:
            List of orphaned evidence records
        """
        violations = []
        
        # Get all unique session_ids from MongoDB evidence
        pipeline = [
            {"$group": {"_id": "$session_id"}},
            {"$limit": limit} if limit else {"$match": {}}
        ]
        
        # Remove empty match stage if no limit
        if not limit:
            pipeline = [{"$group": {"_id": "$session_id"}}]
        
        session_ids_in_mongo = set()
        async for doc in self.mongodb.evidence.aggregate(pipeline):
            session_id_str = doc["_id"]
            if session_id_str:
                session_ids_in_mongo.add(session_id_str)
        
        # Check each session_id exists in PostgreSQL
        for session_id_str in session_ids_in_mongo:
            try:
                session_id = UUID(session_id_str)
                pg_session = await self.postgres_db.get_session(session_id)
                
                if pg_session is None:
                    # Count orphaned evidence for this session
                    count = await self.mongodb.evidence.count_documents(
                        {"session_id": session_id_str}
                    )
                    
                    violations.append(IntegrityViolation(
                        violation_type="orphaned_evidence",
                        description=f"Found {count} orphaned evidence records",
                        session_id=session_id,
                        details={
                            "session_id": session_id_str,
                            "evidence_count": count
                        }
                    ))
            except (ValueError, AttributeError):
                violations.append(IntegrityViolation(
                    violation_type="invalid_session_id",
                    description=f"Invalid session_id in evidence: {session_id_str}",
                    details={"session_id_str": session_id_str}
                ))
        
        logger.info(
            f"Checked {len(session_ids_in_mongo)} unique sessions in MongoDB, "
            f"found {len(violations)} orphaned evidence groups"
        )
        return violations
    
    async def verify_referential_integrity(
        self,
        session_id: UUID
    ) -> bool:
        """
        Verify complete referential integrity for a session.
        
        This is the main method to check if a session maintains proper
        referential integrity between PostgreSQL and MongoDB.
        
        Args:
            session_id: Session UUID to verify
            
        Returns:
            True if referential integrity is maintained, False otherwise
        """
        violations = await self.check_session_id_consistency(session_id)
        
        if violations:
            logger.warning(
                f"Referential integrity violations found for session {session_id}: "
                f"{len(violations)} violations"
            )
            for violation in violations:
                logger.warning(f"  - {violation.violation_type}: {violation.description}")
            return False
        
        logger.info(f"Referential integrity verified for session {session_id}")
        return True
    
    async def get_integrity_report(
        self,
        check_limit: Optional[int] = 1000
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive integrity report.
        
        Args:
            check_limit: Maximum records to check per category
            
        Returns:
            Dictionary containing integrity report with violation counts and details
        """
        report = {
            "timestamp": None,
            "checks_performed": [],
            "total_violations": 0,
            "violations_by_type": {},
            "violations": []
        }
        
        from datetime import datetime
        report["timestamp"] = datetime.utcnow().isoformat()
        
        # Check 1: Evidence session references
        session_violations = await self.check_evidence_session_references(limit=check_limit)
        report["checks_performed"].append("evidence_session_references")
        report["violations"].extend(session_violations)
        
        # Check 2: Evidence event references
        event_violations = await self.check_evidence_event_references(limit=check_limit)
        report["checks_performed"].append("evidence_event_references")
        report["violations"].extend(event_violations)
        
        # Check 3: Orphaned evidence
        orphaned_violations = await self.check_orphaned_evidence(limit=check_limit)
        report["checks_performed"].append("orphaned_evidence")
        report["violations"].extend(orphaned_violations)
        
        # Aggregate statistics
        report["total_violations"] = len(report["violations"])
        
        for violation in report["violations"]:
            vtype = violation.violation_type
            report["violations_by_type"][vtype] = \
                report["violations_by_type"].get(vtype, 0) + 1
        
        logger.info(
            f"Integrity report generated: {report['total_violations']} total violations, "
            f"{len(report['violations_by_type'])} violation types"
        )
        
        return report


# Factory function to create checker with global database instances
def create_integrity_checker(
    postgres_db: PostgresDB,
    mongodb: MongoDB
) -> ReferentialIntegrityChecker:
    """
    Create a referential integrity checker with database instances.
    
    Args:
        postgres_db: PostgreSQL database instance
        mongodb: MongoDB database instance
        
    Returns:
        ReferentialIntegrityChecker instance
    """
    return ReferentialIntegrityChecker(postgres_db, mongodb)
