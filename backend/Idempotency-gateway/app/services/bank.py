import asyncio
import logging
import uuid
from datetime import datetime, timezone

from core.config import settings

logger = logging.getLogger(__name__)


async def mock_bank_processor(amount: float, currency: str) -> dict:
    """
    Simulates an external bank API call.
    The artificial delay gives the race-condition blocker something meaningful to protect.
    In production, this would be an httpx call to a real payment network.
    """
    logger.info("Bank: initiating charge %.2f %s", amount, currency)
    await asyncio.sleep(settings.payment_delay_seconds)

    transaction_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    result = {
        "transaction_id": transaction_id,
        "status": "success",
        "message": f"Charged {amount} {currency}",
        "amount": amount,
        "currency": currency,
        "timestamp": timestamp,
    }

    logger.info("Bank: charge complete — transaction_id=%s", transaction_id)
    return result
