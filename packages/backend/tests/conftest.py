"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_session_id():
    """Mock session UUID"""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def mock_user_id():
    """Mock user UUID"""
    return "660e8400-e29b-41d4-a716-446655440000"
