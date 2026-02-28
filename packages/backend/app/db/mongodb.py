"""
MongoDB database connection and operations
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from bson import ObjectId
from app.config import settings


class MongoDB:
    """MongoDB database manager with async operations"""
    
    def __init__(self, mongodb_url: Optional[str] = None):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.mongodb_url = mongodb_url or settings.MONGODB_URL
    
    async def connect(self):
        """Create MongoDB client and initialize indexes"""
        self.client = AsyncIOMotorClient(self.mongodb_url)
        self.db = self.client.kavalan
        
        # Create indexes for performance
        await self._create_indexes()
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
    
    async def _create_indexes(self):
        """Create indexes for evidence and digital_fir collections"""
        # Evidence collection indexes
        await self.evidence.create_index("session_id")
        await self.evidence.create_index("user_id")
        await self.evidence.create_index("timestamp")
        await self.evidence.create_index([("session_id", 1), ("timestamp", -1)])
        
        # Digital FIR collection indexes
        await self.digital_fir.create_index("fir_id", unique=True)
        await self.digital_fir.create_index("session_id")
        await self.digital_fir.create_index("user_id")
        await self.digital_fir.create_index("generated_at")
        await self.digital_fir.create_index([("user_id", 1), ("generated_at", -1)])
    
    @property
    def evidence(self):
        """Evidence collection"""
        return self.db.evidence
    
    @property
    def digital_fir(self):
        """Digital FIR collection"""
        return self.db.digital_fir
    
    # ==================== EVIDENCE COLLECTION CRUD ====================
    
    async def create_evidence(
        self,
        session_id: UUID,
        user_id: UUID,
        audio: Optional[Dict[str, Any]] = None,
        visual: Optional[Dict[str, Any]] = None,
        liveness: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new evidence document
        
        Args:
            session_id: Session UUID
            user_id: User UUID
            audio: Audio evidence data (transcript, keywords, segments)
            visual: Visual evidence data (frame_url, analysis, detections)
            liveness: Liveness evidence data (face_detected, blink_rate, stress_level)
            metadata: Metadata (platform, browser, extension_version, encryption info)
            
        Returns:
            ObjectId of created evidence document as string
        """
        document = {
            "session_id": str(session_id),
            "user_id": str(user_id),
            "timestamp": datetime.utcnow(),
            "audio": audio or {},
            "visual": visual or {},
            "liveness": liveness or {},
            "metadata": metadata or {}
        }
        
        result = await self.evidence.insert_one(document)
        return str(result.inserted_id)
    
    async def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """
        Get evidence document by ID
        
        Args:
            evidence_id: Evidence ObjectId as string
            
        Returns:
            Evidence document or None if not found
        """
        try:
            document = await self.evidence.find_one({"_id": ObjectId(evidence_id)})
            if document:
                document["_id"] = str(document["_id"])
            return document
        except Exception:
            return None
    
    async def get_session_evidence(
        self,
        session_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all evidence documents for a session
        
        Args:
            session_id: Session UUID
            limit: Maximum number of documents to return
            
        Returns:
            List of evidence documents
        """
        cursor = self.evidence.find(
            {"session_id": str(session_id)}
        ).sort("timestamp", -1).limit(limit)
        
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
        
        return documents
    
    async def get_user_evidence(
        self,
        user_id: UUID,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all evidence documents for a user
        
        Args:
            user_id: User UUID
            limit: Maximum number of documents to return
            
        Returns:
            List of evidence documents
        """
        cursor = self.evidence.find(
            {"user_id": str(user_id)}
        ).sort("timestamp", -1).limit(limit)
        
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
        
        return documents
    
    async def update_evidence(
        self,
        evidence_id: str,
        audio: Optional[Dict[str, Any]] = None,
        visual: Optional[Dict[str, Any]] = None,
        liveness: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update evidence document
        
        Args:
            evidence_id: Evidence ObjectId as string
            audio: Updated audio evidence data
            visual: Updated visual evidence data
            liveness: Updated liveness evidence data
            metadata: Updated metadata
            
        Returns:
            True if document was updated, False if not found
        """
        try:
            update_fields = {}
            if audio is not None:
                update_fields["audio"] = audio
            if visual is not None:
                update_fields["visual"] = visual
            if liveness is not None:
                update_fields["liveness"] = liveness
            if metadata is not None:
                update_fields["metadata"] = metadata
            
            if not update_fields:
                return False
            
            result = await self.evidence.update_one(
                {"_id": ObjectId(evidence_id)},
                {"$set": update_fields}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    async def delete_evidence(self, evidence_id: str) -> bool:
        """
        Delete evidence document
        
        Args:
            evidence_id: Evidence ObjectId as string
            
        Returns:
            True if document was deleted, False if not found
        """
        try:
            result = await self.evidence.delete_one({"_id": ObjectId(evidence_id)})
            return result.deleted_count > 0
        except Exception:
            return False
    
    async def delete_session_evidence(self, session_id: UUID) -> int:
        """
        Delete all evidence documents for a session
        
        Args:
            session_id: Session UUID
            
        Returns:
            Number of documents deleted
        """
        result = await self.evidence.delete_many({"session_id": str(session_id)})
        return result.deleted_count
    
    async def delete_user_evidence(self, user_id: UUID) -> int:
        """
        Delete all evidence documents for a user (DPDP compliance)
        
        Args:
            user_id: User UUID
            
        Returns:
            Number of documents deleted
        """
        result = await self.evidence.delete_many({"user_id": str(user_id)})
        return result.deleted_count
    
    # ==================== DIGITAL FIR COLLECTION CRUD ====================
    
    async def create_digital_fir(
        self,
        fir_id: str,
        session_id: UUID,
        user_id: UUID,
        summary: Dict[str, Any],
        evidence: Dict[str, Any],
        legal: Dict[str, Any]
    ) -> str:
        """
        Create a new Digital FIR document
        
        Args:
            fir_id: Unique FIR identifier
            session_id: Session UUID
            user_id: User UUID
            summary: Summary data (total_duration, max_threat_score, alert_count, threat_categories)
            evidence: Evidence package (transcripts, frames, threat_timeline)
            legal: Legal metadata (chain_of_custody, cryptographic_signature, hash, retention_until)
            
        Returns:
            ObjectId of created FIR document as string
        """
        document = {
            "fir_id": fir_id,
            "session_id": str(session_id),
            "user_id": str(user_id),
            "generated_at": datetime.utcnow(),
            "summary": summary,
            "evidence": evidence,
            "legal": legal
        }
        
        result = await self.digital_fir.insert_one(document)
        return str(result.inserted_id)
    
    async def get_digital_fir(
        self,
        fir_id: str,
        actor: Optional[str] = None,
        track_access: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get Digital FIR document by FIR ID
        
        Args:
            fir_id: Unique FIR identifier
            actor: Actor accessing the FIR (for chain-of-custody tracking)
            track_access: Whether to record access in chain-of-custody
            
        Returns:
            Digital FIR document or None if not found
        """
        document = await self.digital_fir.find_one({"fir_id": fir_id})
        if document:
            document["_id"] = str(document["_id"])
            
            # Track access in chain-of-custody
            if track_access and actor:
                await self.append_chain_of_custody(
                    fir_id=fir_id,
                    action="FIR_ACCESSED",
                    actor=actor
                )
        
        return document
    
    async def get_digital_fir_by_object_id(
        self,
        object_id: str,
        actor: Optional[str] = None,
        track_access: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get Digital FIR document by MongoDB ObjectId
        
        Args:
            object_id: MongoDB ObjectId as string
            actor: Actor accessing the FIR (for chain-of-custody tracking)
            track_access: Whether to record access in chain-of-custody
            
        Returns:
            Digital FIR document or None if not found
        """
        try:
            document = await self.digital_fir.find_one({"_id": ObjectId(object_id)})
            if document:
                document["_id"] = str(document["_id"])
                
                # Track access in chain-of-custody
                if track_access and actor and "fir_id" in document:
                    await self.append_chain_of_custody(
                        fir_id=document["fir_id"],
                        action="FIR_ACCESSED",
                        actor=actor
                    )
            
            return document
        except Exception:
            return None
    
    async def get_session_digital_fir(
        self,
        session_id: UUID,
        actor: Optional[str] = None,
        track_access: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get Digital FIR document for a session
        
        Args:
            session_id: Session UUID
            actor: Actor accessing the FIR (for chain-of-custody tracking)
            track_access: Whether to record access in chain-of-custody
            
        Returns:
            Digital FIR document or None if not found
        """
        document = await self.digital_fir.find_one({"session_id": str(session_id)})
        if document:
            document["_id"] = str(document["_id"])
            
            # Track access in chain-of-custody
            if track_access and actor and "fir_id" in document:
                await self.append_chain_of_custody(
                    fir_id=document["fir_id"],
                    action="FIR_ACCESSED",
                    actor=actor
                )
        
        return document
    
    async def get_user_digital_firs(
        self,
        user_id: UUID,
        limit: int = 50,
        actor: Optional[str] = None,
        track_access: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all Digital FIR documents for a user
        
        Args:
            user_id: User UUID
            limit: Maximum number of documents to return
            actor: Actor accessing the FIRs (for chain-of-custody tracking)
            track_access: Whether to record access in chain-of-custody
            
        Returns:
            List of Digital FIR documents
        """
        cursor = self.digital_fir.find(
            {"user_id": str(user_id)}
        ).sort("generated_at", -1).limit(limit)
        
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
            
            # Track access in chain-of-custody for each FIR
            if track_access and actor and "fir_id" in doc:
                await self.append_chain_of_custody(
                    fir_id=doc["fir_id"],
                    action="FIR_ACCESSED",
                    actor=actor
                )
        
        return documents
    
    async def update_digital_fir(
        self,
        fir_id: str,
        summary: Optional[Dict[str, Any]] = None,
        evidence: Optional[Dict[str, Any]] = None,
        legal: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = None
    ) -> bool:
        """
        Update Digital FIR document
        
        Args:
            fir_id: Unique FIR identifier
            summary: Updated summary data
            evidence: Updated evidence package
            legal: Updated legal metadata
            actor: Actor modifying the FIR (for chain-of-custody tracking)
            
        Returns:
            True if document was updated, False if not found
        """
        update_fields = {}
        modified_sections = []
        
        if summary is not None:
            update_fields["summary"] = summary
            modified_sections.append("summary")
        if evidence is not None:
            update_fields["evidence"] = evidence
            modified_sections.append("evidence")
        if legal is not None:
            update_fields["legal"] = legal
            modified_sections.append("legal")
        
        if not update_fields:
            return False
        
        result = await self.digital_fir.update_one(
            {"fir_id": fir_id},
            {"$set": update_fields}
        )
        
        # Track modification in chain-of-custody
        if result.modified_count > 0 and actor:
            details = f"Modified sections: {', '.join(modified_sections)}"
            await self.append_chain_of_custody(
                fir_id=fir_id,
                action="FIR_MODIFIED",
                actor=actor,
                details=details
            )
        
        return result.modified_count > 0
    
    async def append_chain_of_custody(
        self,
        fir_id: str,
        action: str,
        actor: str,
        details: Optional[str] = None
    ) -> bool:
        """
        Append a chain-of-custody entry to a Digital FIR
        
        Args:
            fir_id: Unique FIR identifier
            action: Action performed (e.g., 'FIR_ACCESSED', 'FIR_MODIFIED', 'FIR_EXPORTED')
            actor: Actor who performed the action (user ID, system, or service name)
            details: Optional additional details about the action
            
        Returns:
            True if entry was appended, False if FIR not found
        """
        custody_entry = {
            "action": action,
            "timestamp": datetime.utcnow(),
            "actor": actor
        }
        
        if details:
            custody_entry["details"] = details
        
        result = await self.digital_fir.update_one(
            {"fir_id": fir_id},
            {"$push": {"legal.chain_of_custody": custody_entry}}
        )
        return result.modified_count > 0
    
    async def delete_digital_fir(self, fir_id: str) -> bool:
        """
        Delete Digital FIR document
        
        Args:
            fir_id: Unique FIR identifier
            
        Returns:
            True if document was deleted, False if not found
        """
        result = await self.digital_fir.delete_one({"fir_id": fir_id})
        return result.deleted_count > 0
    
    async def delete_user_digital_firs(self, user_id: UUID) -> int:
        """
        Delete all Digital FIR documents for a user (DPDP compliance)
        
        Args:
            user_id: User UUID
            
        Returns:
            Number of documents deleted
        """
        result = await self.digital_fir.delete_many({"user_id": str(user_id)})
        return result.deleted_count
    
    async def delete_expired_firs(self, retention_date: datetime) -> int:
        """
        Delete Digital FIR documents past their retention date
        
        Args:
            retention_date: Delete FIRs with retention_until before this date
            
        Returns:
            Number of documents deleted
        """
        result = await self.digital_fir.delete_many({
            "legal.retention_until": {"$lt": retention_date}
        })
        return result.deleted_count


# Global database instance
mongodb = MongoDB()
