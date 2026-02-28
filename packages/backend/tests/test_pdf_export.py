"""
Unit tests for PDF export functionality

Tests that Digital FIR can be exported to PDF format for legal submission.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from app.services.fir_generator import FIRGenerator
from app.db.mongodb import MongoDB
from app.db.postgres import PostgresDB
import io
from PyPDF2 import PdfReader


@pytest.fixture
async def mongodb():
    """Create MongoDB client for testing"""
    db = MongoDB()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def postgres():
    """Create PostgreSQL client for testing"""
    db = PostgresDB()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def fir_generator(mongodb, postgres):
    """Create FIR generator instance"""
    return FIRGenerator(mongodb, postgres)


@pytest.mark.asyncio
async def test_pdf_export_generates_valid_pdf(mongodb, postgres, fir_generator):
    """Test that PDF export generates a valid PDF document"""
    # Create test user and session
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="meet"
    )
    
    # Insert comprehensive evidence
    await mongodb.create_evidence(
        session_id=session_id,
        user_id=user_id,
        audio={
            "transcript": "I am a police officer. You must transfer money immediately.",
            "language": "en",
            "detected_keywords": {
                "authority": ["police", "officer"],
                "financial": ["transfer", "money"],
                "urgency": ["immediately"]
            },
            "segments": [
                {"text": "I am a police officer", "start": 0.0, "end": 2.5, "speaker": "Speaker_1"},
                {"text": "You must transfer money immediately", "start": 2.5, "end": 5.0, "speaker": "Speaker_1"}
            ],
            "speaker_labels": ["Speaker_1"],
            "word_timestamps": [
                {"word": "I", "start": 0.0, "end": 0.1},
                {"word": "am", "start": 0.1, "end": 0.2},
                {"word": "police", "start": 0.3, "end": 0.8}
            ]
        },
        visual={
            "frame_url": "https://storage.example.com/frames/frame_001.jpg",
            "analysis": "Police uniform detected with badge visible",
            "uniform_detected": True,
            "badge_detected": True,
            "threats": ["uniform", "badge"],
            "text_detected": "POLICE",
            "confidence": 0.92
        },
        liveness={
            "face_detected": True,
            "blink_rate": 12.0,
            "stress_level": 0.75,
            "is_natural": True
        }
    )
    
    # Generate FIR
    result = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=8.7,
        threat_level="critical",
        audio_score=9.2,
        visual_score=8.5,
        liveness_score=8.0,
        confidence=0.91,
        timestamp=datetime.utcnow()
    )
    
    assert result.success is True
    
    # Export to PDF
    pdf_bytes = await fir_generator.export_to_pdf(result.fir_id)
    
    # Verify PDF is valid
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF header"
    
    # Verify PDF can be read
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(pdf_reader.pages) > 0, "PDF should have at least one page"
    
    # Cleanup
    await mongodb.delete_digital_fir(result.fir_id)
    await mongodb.delete_session_evidence(session_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_pdf_export_contains_all_sections(mongodb, postgres, fir_generator):
    """Test that PDF export contains all required sections"""
    # Create test user and session
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="zoom"
    )
    
    # Insert evidence
    await mongodb.create_evidence(
        session_id=session_id,
        user_id=user_id,
        audio={
            "transcript": "Test transcript",
            "language": "en",
            "detected_keywords": {"authority": ["police"]},
            "segments": [{"text": "Test", "start": 0.0, "end": 1.0, "speaker": "Speaker_1"}],
            "speaker_labels": ["Speaker_1"],
            "word_timestamps": [{"word": "Test", "start": 0.0, "end": 1.0}]
        },
        visual={
            "frame_url": "https://example.com/frame.jpg",
            "analysis": "Uniform detected",
            "uniform_detected": True,
            "badge_detected": False,
            "threats": ["uniform"],
            "text_detected": "",
            "confidence": 0.85
        },
        liveness={
            "face_detected": True,
            "blink_rate": 15.0,
            "stress_level": 0.6,
            "is_natural": True
        }
    )
    
    # Generate FIR
    result = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=7.5,
        threat_level="high",
        audio_score=7.0,
        visual_score=8.0,
        liveness_score=7.5,
        confidence=0.85,
        timestamp=datetime.utcnow()
    )
    
    assert result.success is True
    
    # Export to PDF
    pdf_bytes = await fir_generator.export_to_pdf(result.fir_id)
    
    # Read PDF text content
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = ""
    for page in pdf_reader.pages:
        full_text += page.extract_text()
    
    # Verify all required sections are present
    assert "DIGITAL FIRST INFORMATION REPORT" in full_text
    assert result.fir_id in full_text
    assert "THREAT ASSESSMENT SUMMARY" in full_text
    assert "AUDIO TRANSCRIPT EVIDENCE" in full_text
    assert "VISUAL ANALYSIS EVIDENCE" in full_text
    assert "THREAT SCORE TIMELINE" in full_text
    assert "LEGAL METADATA" in full_text
    assert "Chain of Custody" in full_text
    
    # Verify metadata is present
    assert str(session_id) in full_text
    assert str(user_id) in full_text
    
    # Verify threat data is present
    assert "7.5" in full_text or "7.50" in full_text  # Threat score
    assert "high" in full_text.lower() or "HIGH" in full_text
    
    # Cleanup
    await mongodb.delete_digital_fir(result.fir_id)
    await mongodb.delete_session_evidence(session_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_pdf_export_includes_evidence_details(mongodb, postgres, fir_generator):
    """Test that PDF export includes detailed evidence information"""
    # Create test user and session
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="teams"
    )
    
    # Insert evidence with specific content
    test_transcript = "This is a test scam call with specific keywords"
    test_keyword = "specific"
    test_frame_url = "https://storage.example.com/test_frame_12345.jpg"
    
    await mongodb.create_evidence(
        session_id=session_id,
        user_id=user_id,
        audio={
            "transcript": test_transcript,
            "language": "en",
            "detected_keywords": {"coercion": [test_keyword]},
            "segments": [{"text": test_transcript, "start": 0.0, "end": 3.0, "speaker": "Speaker_1"}],
            "speaker_labels": ["Speaker_1"],
            "word_timestamps": [{"word": "test", "start": 0.0, "end": 0.5}]
        },
        visual={
            "frame_url": test_frame_url,
            "analysis": "Test analysis result",
            "uniform_detected": True,
            "badge_detected": True,
            "threats": ["uniform", "badge"],
            "text_detected": "TEST_TEXT",
            "confidence": 0.95
        },
        liveness={
            "face_detected": True,
            "blink_rate": 18.0,
            "stress_level": 0.8,
            "is_natural": True
        }
    )
    
    # Generate FIR
    result = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=8.2,
        threat_level="critical",
        audio_score=8.5,
        visual_score=8.0,
        liveness_score=8.0,
        confidence=0.88,
        timestamp=datetime.utcnow()
    )
    
    assert result.success is True
    
    # Export to PDF
    pdf_bytes = await fir_generator.export_to_pdf(result.fir_id)
    
    # Read PDF text content
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = ""
    for page in pdf_reader.pages:
        full_text += page.extract_text()
    
    # Verify specific evidence details are included
    assert test_transcript in full_text, "Transcript text should be in PDF"
    assert test_keyword in full_text, "Detected keywords should be in PDF"
    assert test_frame_url in full_text, "Frame URL should be in PDF"
    assert "TEST_TEXT" in full_text, "Detected text should be in PDF"
    assert "0.95" in full_text, "Confidence score should be in PDF"
    
    # Verify speaker identification
    assert "Speaker_1" in full_text, "Speaker labels should be in PDF"
    
    # Verify modality scores
    assert "8.5" in full_text or "8.50" in full_text, "Audio score should be in PDF"
    assert "8.0" in full_text or "8.00" in full_text, "Visual/Liveness scores should be in PDF"
    
    # Cleanup
    await mongodb.delete_digital_fir(result.fir_id)
    await mongodb.delete_session_evidence(session_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_pdf_export_includes_cryptographic_signature(mongodb, postgres, fir_generator):
    """Test that PDF export includes cryptographic signature and hash"""
    # Create test user and session
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="meet"
    )
    
    # Insert minimal evidence
    await mongodb.create_evidence(
        session_id=session_id,
        user_id=user_id,
        audio={
            "transcript": "Test",
            "language": "en",
            "detected_keywords": {},
            "segments": [{"text": "Test", "start": 0.0, "end": 1.0, "speaker": "Speaker_1"}],
            "speaker_labels": ["Speaker_1"],
            "word_timestamps": [{"word": "Test", "start": 0.0, "end": 1.0}]
        },
        visual={
            "frame_url": "https://example.com/frame.jpg",
            "analysis": "No threats",
            "uniform_detected": False,
            "badge_detected": False,
            "threats": [],
            "text_detected": "",
            "confidence": 0.5
        },
        liveness={
            "face_detected": True,
            "blink_rate": 15.0,
            "stress_level": 0.5,
            "is_natural": True
        }
    )
    
    # Generate FIR
    result = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=7.0,
        threat_level="high",
        audio_score=7.0,
        visual_score=7.0,
        liveness_score=7.0,
        confidence=0.8,
        timestamp=datetime.utcnow()
    )
    
    assert result.success is True
    
    # Get FIR document to extract signature
    fir_doc = await mongodb.get_digital_fir(result.fir_id)
    legal = fir_doc.get('legal', {})
    signature = legal.get('cryptographic_signature', '')
    content_hash = legal.get('hash', '')
    
    # Export to PDF
    pdf_bytes = await fir_generator.export_to_pdf(result.fir_id)
    
    # Read PDF text content
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = ""
    for page in pdf_reader.pages:
        full_text += page.extract_text()
    
    # Verify cryptographic signature is in PDF (may be split across lines, so check partial match)
    # The signature is 128 characters, check for a significant portion
    assert signature[:64] in full_text or signature in full_text.replace('\n', ''), \
        "Cryptographic signature should be in PDF"
    assert content_hash in full_text, "Content hash should be in PDF"
    assert "SHA-256" in full_text, "Hash algorithm should be mentioned"
    assert "SHA-512" in full_text, "Signature algorithm should be mentioned"
    
    # Verify tamper-proof language
    assert "tamper" in full_text.lower() or "integrity" in full_text.lower()
    
    # Cleanup
    await mongodb.delete_digital_fir(result.fir_id)
    await mongodb.delete_session_evidence(session_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


@pytest.mark.asyncio
async def test_pdf_export_raises_error_for_nonexistent_fir(fir_generator):
    """Test that PDF export raises error for non-existent FIR"""
    fake_fir_id = "FIR-20240101-12345678-abcdef12"
    
    with pytest.raises(ValueError, match="not found"):
        await fir_generator.export_to_pdf(fake_fir_id)


@pytest.mark.asyncio
async def test_pdf_export_formats_for_legal_submission(mongodb, postgres, fir_generator):
    """Test that PDF export is properly formatted for legal submission"""
    # Create test user and session
    user_id = await postgres.create_user(
        email=f"test_{uuid4()}@example.com",
        preferences={"language": "en"},
        consent_given=True
    )
    
    session_id = await postgres.create_session(
        user_id=user_id,
        platform="meet"
    )
    
    # Insert evidence
    await mongodb.create_evidence(
        session_id=session_id,
        user_id=user_id,
        audio={
            "transcript": "Legal evidence transcript",
            "language": "en",
            "detected_keywords": {"authority": ["police"]},
            "segments": [{"text": "Legal evidence", "start": 0.0, "end": 2.0, "speaker": "Speaker_1"}],
            "speaker_labels": ["Speaker_1"],
            "word_timestamps": [{"word": "Legal", "start": 0.0, "end": 0.5}]
        },
        visual={
            "frame_url": "https://example.com/legal_frame.jpg",
            "analysis": "Evidence frame",
            "uniform_detected": True,
            "badge_detected": True,
            "threats": ["uniform"],
            "text_detected": "EVIDENCE",
            "confidence": 0.9
        },
        liveness={
            "face_detected": True,
            "blink_rate": 14.0,
            "stress_level": 0.7,
            "is_natural": True
        }
    )
    
    # Generate FIR
    result = await fir_generator.generate_fir(
        session_id=session_id,
        user_id=user_id,
        threat_score=8.0,
        threat_level="critical",
        audio_score=8.5,
        visual_score=8.0,
        liveness_score=7.5,
        confidence=0.87,
        timestamp=datetime.utcnow()
    )
    
    assert result.success is True
    
    # Export to PDF
    pdf_bytes = await fir_generator.export_to_pdf(result.fir_id)
    
    # Read PDF
    pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = ""
    for page in pdf_reader.pages:
        full_text += page.extract_text()
    
    # Verify legal submission formatting
    assert "Evidence Package for Legal Submission" in full_text
    assert "legally admissible" in full_text.lower()
    assert "Chain of Custody" in full_text
    assert "Retention" in full_text
    assert "7 years" in full_text.lower()
    
    # Verify professional structure
    assert "1." in full_text and "2." in full_text  # Numbered sections
    assert "SUMMARY" in full_text
    assert "EVIDENCE" in full_text
    assert "METADATA" in full_text
    
    # Cleanup
    await mongodb.delete_digital_fir(result.fir_id)
    await mongodb.delete_session_evidence(session_id)
    await postgres.delete_session(session_id)
    await postgres.delete_user(user_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
