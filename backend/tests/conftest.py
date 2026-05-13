"""Shared test fixtures — dùng TestClient đồng bộ, tránh event loop conflict."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient: 1 DB connection pool cho toàn bộ test session."""
    with TestClient(app) as c:
        yield c
