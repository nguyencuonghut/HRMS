from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app import main


class _SessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_seed_rbac_if_possible_skips_when_users_table_missing(monkeypatch):
    session = AsyncMock()
    session.execute.side_effect = [
        SimpleNamespace(scalar=lambda: False),
    ]
    run_mock = AsyncMock()

    monkeypatch.setattr(main, "AsyncSessionLocal", lambda: _SessionContext(session))
    monkeypatch.setattr(main.rbac_seed, "run", run_mock)

    await main.seed_rbac_if_possible()

    assert session.execute.await_count == 1
    run_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_rbac_if_possible_runs_when_users_table_exists_and_empty(monkeypatch):
    session = AsyncMock()
    session.execute.side_effect = [
        SimpleNamespace(scalar=lambda: True),
        SimpleNamespace(scalar=lambda: 0),
    ]
    run_mock = AsyncMock()

    monkeypatch.setattr(main, "AsyncSessionLocal", lambda: _SessionContext(session))
    monkeypatch.setattr(main.rbac_seed, "run", run_mock)

    await main.seed_rbac_if_possible()

    assert session.execute.await_count == 2
    run_mock.assert_awaited_once_with(session)


@pytest.mark.asyncio
async def test_seed_rbac_if_possible_skips_in_production(monkeypatch):
    session = AsyncMock()
    run_mock = AsyncMock()

    monkeypatch.setattr(main, "AsyncSessionLocal", lambda: _SessionContext(session))
    monkeypatch.setattr(main.rbac_seed, "run", run_mock)
    monkeypatch.setattr(main.settings, "ENVIRONMENT", "production")

    await main.seed_rbac_if_possible()

    assert session.execute.await_count == 0
    run_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_notifications_if_possible_skips_in_production(monkeypatch):
    session = AsyncMock()
    run_mock = AsyncMock()

    monkeypatch.setattr(main, "AsyncSessionLocal", lambda: _SessionContext(session))
    monkeypatch.setattr(main.notif_seed, "seed_notification_templates", run_mock)
    monkeypatch.setattr(main.settings, "ENVIRONMENT", "production")

    await main.seed_notifications_if_possible()

    assert session.execute.await_count == 0
    run_mock.assert_not_awaited()
