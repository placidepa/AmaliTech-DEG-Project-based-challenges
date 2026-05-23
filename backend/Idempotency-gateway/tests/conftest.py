import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../app"))

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

import services.store as store
from main import app

pytest_plugins = ("anyio",)


@pytest.fixture
async def client():
    store._redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    original_delay = store.settings.payment_delay_seconds
    store.settings.payment_delay_seconds = 0

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    store._redis = None
    store.settings.payment_delay_seconds = original_delay
    store._locks.clear()
