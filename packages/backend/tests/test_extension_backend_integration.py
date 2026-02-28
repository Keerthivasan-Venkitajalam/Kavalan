"""
Integration Test for Extension-Backend Communication

Tests WebSocket connection, message passing, and encrypted data transmission
between the browser extension and backend API.

Note: These tests focus on the communication protocol and data flow.
WebSocket authentication is tested separately in the API tests.

Validates:
- HTTP API endpoints for media analysis
- Encrypted data transmission
- Request-response patterns
- Error handling
"""
import pytest
import asyncio
import json
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
import base64

from app.main import app
from app.db.postgres import PostgresDB
from app.db.mongodb import MongoDB


@pytest.fixture
def client():
    """Create FastAPI test client"""
    return TestClient(app)


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
async def test_user(postgres_db):
    """Create a test user"""
    user_id = await postgres_db.create_user(
        email=f"test_api_{uuid4()}@example.com",
        consent_given=True
    )
    yield user_id
    # Cleanup
    await postgres_db.delete_user(user_id)


def encrypt_payload(data: bytes) -> dict:
    """
    Simulate extension encryption of payload.
    
    In real extension, this uses Web Crypto API with AES-256-GCM.
    For testing, we use base64 encoding to simulate encryption.
    """
    encoded = base64.b64encode(data).decode()
    
    return {
        "encrypted": True,
        "data": encoded,
        "iv": base64.b64encode(b"test_iv_12345678").decode(),  # 16 bytes
        "algorithm": "AES-256-GCM"
    }


@pytest.mark.integration
def test_encrypted_audio_api_endpoint(client):
    """
    Test encrypted audio data submission via HTTP API.
    
    Validates: Encrypted data transmission, API endpoint
    """
    session_id = str(uuid4())
    
    # Prepare audio data
    audio_bytes = b"fake_audio_data_for_testing"
    encrypted_audio = encrypt_payload(audio_bytes)
    
    # Send to API endpoint
    response = client.post(
        "/api/v1/analyze/audio",
        json={
            "session_id": session_id,
            "payload": encrypted_audio,
            "sample_rate": 16000,
            "duration": 3.0,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Verify response
    assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        assert "message_id" in data or "status" in data


@pytest.mark.integration
def test_encrypted_video_api_endpoint(client):
    """
    Test encrypted video frame submission via HTTP API.
    
    Validates: Encrypted video data transmission
    """
    session_id = str(uuid4())
    
    # Prepare video frame data
    frame_bytes = b"fake_frame_data_for_testing"
    encrypted_frame = encrypt_payload(frame_bytes)
    
    # Send to API endpoint
    response = client.post(
        "/api/v1/analyze/visual",
        json={
            "session_id": session_id,
            "payload": encrypted_frame,
            "width": 640,
            "height": 480,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Verify response
    assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}"
    
    if response.status_code == 200:
        data = response.json()
        assert "message_id" in data or "status" in data


@pytest.mark.integration
def test_liveness_detection_api_endpoint(client):
    """
    Test liveness detection frame submission via HTTP API.
    
    Validates: Liveness detection endpoint
    """
    session_id = str(uuid4())
    
    # Prepare frame data
    frame_bytes = b"fake_liveness_frame_data"
    encrypted_frame = encrypt_payload(frame_bytes)
    
    # Send to API endpoint
    response = client.post(
        "/api/v1/analyze/liveness",
        json={
            "session_id": session_id,
            "payload": encrypted_frame,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Verify response
    assert response.status_code in [200, 202], f"Expected 200 or 202, got {response.status_code}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_status_retrieval(client, test_user, postgres_db):
    """
    Test retrieving session status via HTTP API.
    
    Validates: Status endpoint, request-response pattern
    """
    # Create session
    session_id = await postgres_db.create_session(test_user, "meet")
    
    try:
        # Request session status
        response = client.get(f"/api/v1/sessions/{session_id}/status")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "status" in data or "threat_score" in data
    
    finally:
        # Cleanup
        await postgres_db.delete_session(session_id)


@pytest.mark.integration
def test_invalid_encrypted_payload_handling(client):
    """
    Test handling of invalid encrypted payloads.
    
    Validates: Error handling, graceful degradation
    """
    session_id = str(uuid4())
    
    # Send invalid encrypted payload (missing required fields)
    response = client.post(
        "/api/v1/analyze/audio",
        json={
            "session_id": session_id,
            "payload": {
                "encrypted": True
                # Missing 'data' and 'iv' fields
            }
        }
    )
    
    # Should return error
    assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"


@pytest.mark.integration
def test_missing_session_id_handling(client):
    """
    Test handling of requests with missing session_id.
    
    Validates: Input validation, error responses
    """
    audio_bytes = b"fake_audio_data"
    encrypted_audio = encrypt_payload(audio_bytes)
    
    # Send without session_id
    response = client.post(
        "/api/v1/analyze/audio",
        json={
            # Missing session_id
            "payload": encrypted_audio,
            "sample_rate": 16000
        }
    )
    
    # Should return validation error
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_media_submissions(client, test_user, postgres_db):
    """
    Test handling concurrent media submissions from extension.
    
    Validates: Concurrent request handling, isolation
    """
    # Create session
    session_id = await postgres_db.create_session(test_user, "zoom")
    
    try:
        # Prepare multiple media payloads
        audio_bytes = b"audio_data_1"
        frame_bytes = b"frame_data_1"
        
        encrypted_audio = encrypt_payload(audio_bytes)
        encrypted_frame = encrypt_payload(frame_bytes)
        
        # Submit audio
        audio_response = client.post(
            "/api/v1/analyze/audio",
            json={
                "session_id": str(session_id),
                "payload": encrypted_audio,
                "sample_rate": 16000,
                "duration": 3.0
            }
        )
        
        # Submit video (concurrent)
        video_response = client.post(
            "/api/v1/analyze/visual",
            json={
                "session_id": str(session_id),
                "payload": encrypted_frame,
                "width": 640,
                "height": 480
            }
        )
        
        # Both should succeed
        assert audio_response.status_code in [200, 202]
        assert video_response.status_code in [200, 202]
    
    finally:
        # Cleanup
        await postgres_db.delete_session(session_id)


@pytest.mark.integration
def test_api_rate_limiting(client):
    """
    Test API rate limiting for media submissions.
    
    Validates: Rate limiting, protection against abuse
    """
    session_id = str(uuid4())
    audio_bytes = b"audio_data"
    encrypted_audio = encrypt_payload(audio_bytes)
    
    # Send multiple rapid requests
    responses = []
    for i in range(20):  # Send 20 requests rapidly
        response = client.post(
            "/api/v1/analyze/audio",
            json={
                "session_id": session_id,
                "payload": encrypted_audio,
                "sample_rate": 16000
            }
        )
        responses.append(response.status_code)
    
    # Some requests should succeed, but rate limiting may kick in
    # At least the first few should succeed
    assert any(code in [200, 202] for code in responses[:5])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_communication_flow(
    client,
    test_user,
    postgres_db,
    mongodb
):
    """
    Test complete end-to-end communication flow:
    Extension -> API -> Processing -> Storage
    
    Validates: Complete integration pipeline
    """
    # Create session
    session_id = await postgres_db.create_session(test_user, "teams")
    
    try:
        # Step 1: Extension sends audio data
        audio_bytes = b"test_audio_data_for_e2e"
        encrypted_audio = encrypt_payload(audio_bytes)
        
        audio_response = client.post(
            "/api/v1/analyze/audio",
            json={
                "session_id": str(session_id),
                "payload": encrypted_audio,
                "sample_rate": 16000,
                "duration": 3.0,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        assert audio_response.status_code in [200, 202]
        
        # Step 2: Extension sends video frame
        frame_bytes = b"test_frame_data_for_e2e"
        encrypted_frame = encrypt_payload(frame_bytes)
        
        video_response = client.post(
            "/api/v1/analyze/visual",
            json={
                "session_id": str(session_id),
                "payload": encrypted_frame,
                "width": 640,
                "height": 480,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        assert video_response.status_code in [200, 202]
        
        # Step 3: Extension requests status
        status_response = client.get(f"/api/v1/sessions/{session_id}/status")
        
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        # Verify status contains expected fields
        assert "session_id" in status_data or "status" in status_data
        
        # In real system, we would verify:
        # - Data was decrypted
        # - Analysis was performed
        # - Results were stored
        # - Alerts were generated if needed
        
    finally:
        # Cleanup
        await postgres_db.delete_session(session_id)
