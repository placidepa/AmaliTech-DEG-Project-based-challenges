import hashlib
import json
import logging
from typing import Callable, Awaitable, Tuple

from fastapi import HTTPException

from services import store

logger = logging.getLogger(__name__)


def _get_hash(payload: dict) -> str:
    payload_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_str.encode()).hexdigest()


async def execute_idempotent_request(
    key: str,
    payload: dict,
    process_payment_action: Callable[[], Awaitable[dict]],
) -> Tuple[dict, bool]:
    """
    Central idempotency gate. Returns (response_dict, is_cache_hit).

    Scenario 1 — Brand new key:        process payment, store result, return (result, False)
    Scenario 2 — Duplicate key:        return cached result without reprocessing, return (result, True)
    Scenario 3 — Same key, diff body:  raise 409 Conflict (fraud/tampering)

    Race-condition safety:
      The asyncio.Lock is acquired BEFORE reading the record. If Request A holds the
      lock while processing, Request B blocks at `async with lock`. When A releases,
      B reads the now-COMPLETED record and returns it as a cache hit — no double charge.
    """
    lock = store.get_lock(key)
    payload_hash = _get_hash(payload)

    async with lock:
        record = await store.get_record(key)

        if record:
            if record["hash"] != payload_hash:
                logger.warning(
                    "Fraud check FAILED for key=%s — hash mismatch (stored=%s, received=%s)",
                    key, record["hash"][:8], payload_hash[:8],
                )
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key already used for a different request body.",
                )

            logger.info("Cache HIT for idempotency_key=%s", key)
            return record["response"], True

        logger.info("New payment request: idempotency_key=%s", key)
        await store.create_record(key, payload_hash)

        result = await process_payment_action()

        await store.complete_record(key, result)
        return result, False
