import asyncio
import json
import logging

import redis.asyncio as aioredis

from core.config import settings

logger = logging.getLogger(__name__)

_locks: dict = {}
_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    await _redis.ping()
    logger.info("Redis connection established: %s", settings.redis_url)


async def close_redis() -> None:
    if _redis:
        await _redis.aclose()


def get_lock(key: str) -> asyncio.Lock:
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


async def get_record(key: str) -> dict | None:
    raw = await _redis.get(f"idempotency:{key}")
    return json.loads(raw) if raw else None


async def create_record(key: str, payload_hash: str) -> None:
    ttl = settings.idempotency_ttl_hours * 3600
    record = {"status": "IN_PROGRESS", "hash": payload_hash, "response": None}
    await _redis.set(f"idempotency:{key}", json.dumps(record), ex=ttl)


async def complete_record(key: str, response: dict) -> None:
    raw = await _redis.get(f"idempotency:{key}")
    if raw:
        record = json.loads(raw)
        record["status"] = "COMPLETED"
        record["response"] = response
        await _redis.set(f"idempotency:{key}", json.dumps(record), keepttl=True)


async def clear_store() -> None:
    """Wipe the store clean. Used only by pytest fixtures."""
    await _redis.flushdb()
    _locks.clear()
