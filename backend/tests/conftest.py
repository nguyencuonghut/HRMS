"""Shared test fixtures for the backend test suite."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.core.database import AsyncSessionLocal, engine
from app.main import app
from app.seeds import rbac


async def _ensure_test_auth_identities() -> None:
    """Seed roles/permissions/local users cho test suite, không phụ thuộc CLI seeder."""
    async with AsyncSessionLocal() as session:
        await rbac.run(session, include_users=True)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def ensure_test_auth_identities():
    """Seed test auth data inside pytest-asyncio's managed session loop."""
    await _ensure_test_auth_identities()
    yield


@pytest.fixture(scope="session")
def client(ensure_test_auth_identities):
    """Session-scoped TestClient: 1 DB connection pool cho toàn bộ test session."""
    with TestClient(app) as c:
        yield c
