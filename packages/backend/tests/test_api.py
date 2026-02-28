"""
Basic API tests
"""
import pytest
from app.middleware.auth import jwt_auth


def test_root_endpoint(client):
    """Test root endpoint returns health status"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "kavalan-api"


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_analyze_audio_endpoint_requires_auth(client):
    """Test audio analysis endpoint requires authentication"""
    response = client.post(
        "/api/v1/analyze/audio",
        json={
            "encrypted_data": "base64_encoded_data",
            "iv": "base64_encoded_iv",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": 1234567890.0,
            "sample_rate": 16000,
            "duration": 3.0
        }
    )
    assert response.status_code == 403  # No auth header


def test_analyze_visual_endpoint_requires_auth(client):
    """Test visual analysis endpoint requires authentication"""
    response = client.post(
        "/api/v1/analyze/visual",
        json={
            "encrypted_data": "base64_encoded_data",
            "iv": "base64_encoded_iv",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": 1234567890.0,
            "width": 640,
            "height": 480
        }
    )
    assert response.status_code == 403  # No auth header


def test_analyze_liveness_endpoint_requires_auth(client):
    """Test liveness analysis endpoint requires authentication"""
    response = client.post(
        "/api/v1/analyze/liveness",
        json={
            "encrypted_data": "base64_encoded_data",
            "iv": "base64_encoded_iv",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": 1234567890.0,
            "width": 640,
            "height": 480
        }
    )
    assert response.status_code == 403  # No auth header


def test_session_status_endpoint_requires_auth(client, mock_session_id):
    """Test session status endpoint requires authentication"""
    response = client.get(f"/api/v1/sessions/{mock_session_id}/status")
    assert response.status_code == 403  # No auth header


def test_jwt_token_creation(mock_user_id, mock_session_id):
    """Test JWT token creation"""
    token = jwt_auth.create_token(mock_user_id, mock_session_id)
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0
