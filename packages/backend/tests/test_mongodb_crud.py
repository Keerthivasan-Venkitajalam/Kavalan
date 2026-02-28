"""
Tests for MongoDB CRUD operations
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta
from app.db.mongodb import MongoDB


@pytest.fixture
async def mongodb():
    """Create MongoDB instance for testing"""
    db = MongoDB(mongodb_url="mongodb://localhost:27017/kavalan_test")
    await db.connect()
    
    # Clean up test collections
    await db.evidence.delete_many({})
    await db.digital_fir.delete_many({})
    
    yield db
    
    # Clean up after tests
    await db.evidence.delete_many({})
    await db.digital_fir.delete_many({})
    await db.disconnect()


class TestEvidenceCollection:
    """Tests for evidence collection CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_evidence(self, mongodb):
        """Test creating evidence document"""
        session_id = uuid4()
        user_id = uuid4()
        
        audio_data = {
            "transcript": "This is a test transcript",
            "language": "en",
            "detected_keywords": {
                "authority": ["police", "CBI"],
                "coercion": ["arrest"]
            },
            "segments": [
                {"text": "This is a test", "start": 0.0, "end": 1.5, "confidence": 0.95}
            ]
        }
        
        visual_data = {
            "frame_url": "https://storage.example.com/frame123.jpg",
            "analysis": "Uniform detected",
            "uniform_detected": True,
            "badge_detected": False,
            "threats": ["uniform"],
            "text_detected": "",
            "confidence": 0.87
        }
        
        liveness_data = {
            "face_detected": True,
            "blink_rate": 15.2,
            "stress_level": 0.65,
            "is_natural": True,
            "landmarks_snapshot": {}
        }
        
        metadata = {
            "platform": "meet",
            "browser": "chrome",
            "extension_version": "1.0.0",
            "encrypted": True,
            "encryption_key_id": "key123"
        }
        
        evidence_id = await mongodb.create_evidence(
            session_id=session_id,
            user_id=user_id,
            audio=audio_data,
            visual=visual_data,
            liveness=liveness_data,
            metadata=metadata
        )
        
        assert evidence_id is not None
        
        # Verify document was created
        evidence = await mongodb.get_evidence(evidence_id)
        assert evidence is not None
        assert evidence["session_id"] == str(session_id)
        assert evidence["user_id"] == str(user_id)
        assert evidence["audio"]["transcript"] == "This is a test transcript"
        assert evidence["visual"]["uniform_detected"] is True
        assert evidence["liveness"]["blink_rate"] == 15.2
        assert evidence["metadata"]["platform"] == "meet"
    
    @pytest.mark.asyncio
    async def test_get_evidence_not_found(self, mongodb):
        """Test getting non-existent evidence"""
        evidence = await mongodb.get_evidence("507f1f77bcf86cd799439011")
        assert evidence is None
    
    @pytest.mark.asyncio
    async def test_get_session_evidence(self, mongodb):
        """Test getting all evidence for a session"""
        session_id = uuid4()
        user_id = uuid4()
        
        # Create multiple evidence documents
        for i in range(3):
            await mongodb.create_evidence(
                session_id=session_id,
                user_id=user_id,
                audio={"transcript": f"Transcript {i}"},
                visual={},
                liveness={},
                metadata={}
            )
        
        # Get all evidence for session
        evidence_list = await mongodb.get_session_evidence(session_id)
        assert len(evidence_list) == 3
        
        # Verify they're sorted by timestamp (newest first)
        timestamps = [e["timestamp"] for e in evidence_list]
        assert timestamps == sorted(timestamps, reverse=True)
    
    @pytest.mark.asyncio
    async def test_get_user_evidence(self, mongodb):
        """Test getting all evidence for a user"""
        user_id = uuid4()
        session_id1 = uuid4()
        session_id2 = uuid4()
        
        # Create evidence for multiple sessions
        await mongodb.create_evidence(
            session_id=session_id1,
            user_id=user_id,
            audio={"transcript": "Session 1"},
            visual={},
            liveness={},
            metadata={}
        )
        
        await mongodb.create_evidence(
            session_id=session_id2,
            user_id=user_id,
            audio={"transcript": "Session 2"},
            visual={},
            liveness={},
            metadata={}
        )
        
        # Get all evidence for user
        evidence_list = await mongodb.get_user_evidence(user_id)
        assert len(evidence_list) == 2
    
    @pytest.mark.asyncio
    async def test_update_evidence(self, mongodb):
        """Test updating evidence document"""
        session_id = uuid4()
        user_id = uuid4()
        
        evidence_id = await mongodb.create_evidence(
            session_id=session_id,
            user_id=user_id,
            audio={"transcript": "Original"},
            visual={},
            liveness={},
            metadata={}
        )
        
        # Update audio data
        updated = await mongodb.update_evidence(
            evidence_id=evidence_id,
            audio={"transcript": "Updated"}
        )
        assert updated is True
        
        # Verify update
        evidence = await mongodb.get_evidence(evidence_id)
        assert evidence["audio"]["transcript"] == "Updated"
    
    @pytest.mark.asyncio
    async def test_delete_evidence(self, mongodb):
        """Test deleting evidence document"""
        session_id = uuid4()
        user_id = uuid4()
        
        evidence_id = await mongodb.create_evidence(
            session_id=session_id,
            user_id=user_id,
            audio={},
            visual={},
            liveness={},
            metadata={}
        )
        
        # Delete evidence
        deleted = await mongodb.delete_evidence(evidence_id)
        assert deleted is True
        
        # Verify deletion
        evidence = await mongodb.get_evidence(evidence_id)
        assert evidence is None
    
    @pytest.mark.asyncio
    async def test_delete_session_evidence(self, mongodb):
        """Test deleting all evidence for a session"""
        session_id = uuid4()
        user_id = uuid4()
        
        # Create multiple evidence documents
        for i in range(3):
            await mongodb.create_evidence(
                session_id=session_id,
                user_id=user_id,
                audio={},
                visual={},
                liveness={},
                metadata={}
            )
        
        # Delete all evidence for session
        count = await mongodb.delete_session_evidence(session_id)
        assert count == 3
        
        # Verify deletion
        evidence_list = await mongodb.get_session_evidence(session_id)
        assert len(evidence_list) == 0
    
    @pytest.mark.asyncio
    async def test_delete_user_evidence(self, mongodb):
        """Test deleting all evidence for a user (DPDP compliance)"""
        user_id = uuid4()
        session_id1 = uuid4()
        session_id2 = uuid4()
        
        # Create evidence for multiple sessions
        await mongodb.create_evidence(
            session_id=session_id1,
            user_id=user_id,
            audio={},
            visual={},
            liveness={},
            metadata={}
        )
        
        await mongodb.create_evidence(
            session_id=session_id2,
            user_id=user_id,
            audio={},
            visual={},
            liveness={},
            metadata={}
        )
        
        # Delete all evidence for user
        count = await mongodb.delete_user_evidence(user_id)
        assert count == 2
        
        # Verify deletion
        evidence_list = await mongodb.get_user_evidence(user_id)
        assert len(evidence_list) == 0


class TestDigitalFIRCollection:
    """Tests for digital_fir collection CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_digital_fir(self, mongodb):
        """Test creating Digital FIR document"""
        fir_id = f"FIR-{uuid4()}"
        session_id = uuid4()
        user_id = uuid4()
        
        summary = {
            "total_duration": 1800,
            "max_threat_score": 8.5,
            "alert_count": 3,
            "threat_categories": ["authority", "coercion"]
        }
        
        evidence = {
            "transcripts": [
                {"text": "Transcript 1", "timestamp": datetime.utcnow().isoformat()}
            ],
            "frames": ["https://storage.example.com/frame1.jpg"],
            "threat_timeline": [
                {
                    "timestamp": datetime.utcnow(),
                    "score": 8.5,
                    "description": "High threat detected"
                }
            ]
        }
        
        legal = {
            "chain_of_custody": [
                {
                    "action": "created",
                    "timestamp": datetime.utcnow(),
                    "actor": "system"
                }
            ],
            "cryptographic_signature": "sig123",
            "hash": "hash123",
            "retention_until": datetime.utcnow() + timedelta(days=2555)  # 7 years
        }
        
        object_id = await mongodb.create_digital_fir(
            fir_id=fir_id,
            session_id=session_id,
            user_id=user_id,
            summary=summary,
            evidence=evidence,
            legal=legal
        )
        
        assert object_id is not None
        
        # Verify document was created
        fir = await mongodb.get_digital_fir(fir_id)
        assert fir is not None
        assert fir["fir_id"] == fir_id
        assert fir["session_id"] == str(session_id)
        assert fir["user_id"] == str(user_id)
        assert fir["summary"]["max_threat_score"] == 8.5
        assert len(fir["evidence"]["transcripts"]) == 1
        assert fir["legal"]["hash"] == "hash123"
    
    @pytest.mark.asyncio
    async def test_get_digital_fir_not_found(self, mongodb):
        """Test getting non-existent Digital FIR"""
        fir = await mongodb.get_digital_fir("FIR-nonexistent")
        assert fir is None
    
    @pytest.mark.asyncio
    async def test_get_digital_fir_by_object_id(self, mongodb):
        """Test getting Digital FIR by MongoDB ObjectId"""
        fir_id = f"FIR-{uuid4()}"
        session_id = uuid4()
        user_id = uuid4()
        
        object_id = await mongodb.create_digital_fir(
            fir_id=fir_id,
            session_id=session_id,
            user_id=user_id,
            summary={},
            evidence={},
            legal={}
        )
        
        # Get by ObjectId
        fir = await mongodb.get_digital_fir_by_object_id(object_id)
        assert fir is not None
        assert fir["fir_id"] == fir_id
    
    @pytest.mark.asyncio
    async def test_get_session_digital_fir(self, mongodb):
        """Test getting Digital FIR for a session"""
        fir_id = f"FIR-{uuid4()}"
        session_id = uuid4()
        user_id = uuid4()
        
        await mongodb.create_digital_fir(
            fir_id=fir_id,
            session_id=session_id,
            user_id=user_id,
            summary={},
            evidence={},
            legal={}
        )
        
        # Get by session ID
        fir = await mongodb.get_session_digital_fir(session_id)
        assert fir is not None
        assert fir["session_id"] == str(session_id)
    
    @pytest.mark.asyncio
    async def test_get_user_digital_firs(self, mongodb):
        """Test getting all Digital FIRs for a user"""
        user_id = uuid4()
        
        # Create multiple FIRs
        for i in range(3):
            await mongodb.create_digital_fir(
                fir_id=f"FIR-{uuid4()}",
                session_id=uuid4(),
                user_id=user_id,
                summary={"alert_count": i},
                evidence={},
                legal={}
            )
        
        # Get all FIRs for user
        firs = await mongodb.get_user_digital_firs(user_id)
        assert len(firs) == 3
        
        # Verify they're sorted by generated_at (newest first)
        timestamps = [f["generated_at"] for f in firs]
        assert timestamps == sorted(timestamps, reverse=True)
    
    @pytest.mark.asyncio
    async def test_update_digital_fir(self, mongodb):
        """Test updating Digital FIR document"""
        fir_id = f"FIR-{uuid4()}"
        session_id = uuid4()
        user_id = uuid4()
        
        await mongodb.create_digital_fir(
            fir_id=fir_id,
            session_id=session_id,
            user_id=user_id,
            summary={"alert_count": 1},
            evidence={},
            legal={}
        )
        
        # Update summary
        updated = await mongodb.update_digital_fir(
            fir_id=fir_id,
            summary={"alert_count": 5}
        )
        assert updated is True
        
        # Verify update
        fir = await mongodb.get_digital_fir(fir_id)
        assert fir["summary"]["alert_count"] == 5
    
    @pytest.mark.asyncio
    async def test_append_chain_of_custody(self, mongodb):
        """Test appending chain-of-custody entry"""
        fir_id = f"FIR-{uuid4()}"
        session_id = uuid4()
        user_id = uuid4()
        
        await mongodb.create_digital_fir(
            fir_id=fir_id,
            session_id=session_id,
            user_id=user_id,
            summary={},
            evidence={},
            legal={"chain_of_custody": []}
        )
        
        # Append custody entry
        appended = await mongodb.append_chain_of_custody(
            fir_id=fir_id,
            action="accessed",
            actor="user123"
        )
        assert appended is True
        
        # Verify entry was appended
        fir = await mongodb.get_digital_fir(fir_id)
        assert len(fir["legal"]["chain_of_custody"]) == 1
        assert fir["legal"]["chain_of_custody"][0]["action"] == "accessed"
        assert fir["legal"]["chain_of_custody"][0]["actor"] == "user123"
    
    @pytest.mark.asyncio
    async def test_delete_digital_fir(self, mongodb):
        """Test deleting Digital FIR document"""
        fir_id = f"FIR-{uuid4()}"
        session_id = uuid4()
        user_id = uuid4()
        
        await mongodb.create_digital_fir(
            fir_id=fir_id,
            session_id=session_id,
            user_id=user_id,
            summary={},
            evidence={},
            legal={}
        )
        
        # Delete FIR
        deleted = await mongodb.delete_digital_fir(fir_id)
        assert deleted is True
        
        # Verify deletion
        fir = await mongodb.get_digital_fir(fir_id)
        assert fir is None
    
    @pytest.mark.asyncio
    async def test_delete_user_digital_firs(self, mongodb):
        """Test deleting all Digital FIRs for a user (DPDP compliance)"""
        user_id = uuid4()
        
        # Create multiple FIRs
        for i in range(3):
            await mongodb.create_digital_fir(
                fir_id=f"FIR-{uuid4()}",
                session_id=uuid4(),
                user_id=user_id,
                summary={},
                evidence={},
                legal={}
            )
        
        # Delete all FIRs for user
        count = await mongodb.delete_user_digital_firs(user_id)
        assert count == 3
        
        # Verify deletion
        firs = await mongodb.get_user_digital_firs(user_id)
        assert len(firs) == 0
    
    @pytest.mark.asyncio
    async def test_delete_expired_firs(self, mongodb):
        """Test deleting expired Digital FIRs"""
        user_id = uuid4()
        
        # Create FIR with past retention date
        await mongodb.create_digital_fir(
            fir_id=f"FIR-{uuid4()}",
            session_id=uuid4(),
            user_id=user_id,
            summary={},
            evidence={},
            legal={"retention_until": datetime.utcnow() - timedelta(days=1)}
        )
        
        # Create FIR with future retention date
        await mongodb.create_digital_fir(
            fir_id=f"FIR-{uuid4()}",
            session_id=uuid4(),
            user_id=user_id,
            summary={},
            evidence={},
            legal={"retention_until": datetime.utcnow() + timedelta(days=365)}
        )
        
        # Delete expired FIRs
        count = await mongodb.delete_expired_firs(datetime.utcnow())
        assert count == 1
        
        # Verify only one FIR remains
        firs = await mongodb.get_user_digital_firs(user_id)
        assert len(firs) == 1


class TestIndexes:
    """Tests for MongoDB indexes"""
    
    @pytest.mark.asyncio
    async def test_indexes_created(self, mongodb):
        """Test that indexes are created on connect"""
        # Get index information
        evidence_indexes = await mongodb.evidence.index_information()
        fir_indexes = await mongodb.digital_fir.index_information()
        
        # Verify evidence collection indexes
        assert "session_id_1" in evidence_indexes
        assert "user_id_1" in evidence_indexes
        assert "timestamp_1" in evidence_indexes
        
        # Verify digital_fir collection indexes
        assert "fir_id_1" in fir_indexes
        assert "session_id_1" in fir_indexes
        assert "user_id_1" in fir_indexes
        assert "generated_at_1" in fir_indexes
        
        # Verify unique index on fir_id
        assert fir_indexes["fir_id_1"]["unique"] is True
