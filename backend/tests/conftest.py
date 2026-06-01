"""Shared test fixtures — dùng TestClient đồng bộ, tránh event loop conflict."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.database import AsyncSessionLocal, engine
from app.main import app
from app.seeds import rbac


async def _ensure_test_auth_identities() -> None:
    """Seed roles/permissions/local users cho test suite, không phụ thuộc CLI seeder."""
    async with AsyncSessionLocal() as session:
        await rbac.run(session, include_users=True)
    await engine.dispose()


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient: 1 DB connection pool cho toàn bộ test session."""
    asyncio.run(_ensure_test_auth_identities())
    with TestClient(app) as c:
        yield c
