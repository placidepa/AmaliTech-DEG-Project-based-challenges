import logging

from fastapi import APIRouter, Header, Response

from schemas.payment_dto import PaymentRequest, PaymentResponse
from services.bank import mock_bank_processor
from services.idempotency import execute_idempotent_request

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payments"])


@router.post(
    "/process-payment",
    status_code=201,
    response_model=PaymentResponse,
    summary="Process a Payment (Idempotent)",
    responses={
        201: {"description": "First request: payment charged and result stored. Duplicate request: cached result replayed (X-Cache-Hit: true header will be present)."},
        409: {"description": "Idempotency key reused with a different request body (fraud/tampering)"},
        422: {"description": "Validation error — invalid amount, bad currency code, or missing header"},
    },
)
async def process_payment(
    payload: PaymentRequest,
    response: Response,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        description="Unique client-generated key (UUID v4 recommended). Must be identical on retries.",
    ),
) -> PaymentResponse:
    """
    Submit a payment for processing with idempotency guarantees.

    - **First call**: payment is processed and stored → **201**, no `X-Cache-Hit` header.
    - **Retry (same key + same body)**: cached result returned instantly → **201** + `X-Cache-Hit: true`.
    - **Same key, different body**: **409 Conflict** — key is locked to its original payload.
    - **Concurrent duplicate**: second request blocks until first completes, then returns its result.
    """
    logger.info(
        "Incoming payment: idempotency_key=%s amount=%.2f currency=%s",
        idempotency_key, payload.amount, payload.currency,
    )

    async def payment_action() -> dict:
        return await mock_bank_processor(payload.amount, payload.currency)

    result, is_cache_hit = await execute_idempotent_request(
        key=idempotency_key,
        payload=payload.model_dump(),
        process_payment_action=payment_action,
    )

    response.headers["X-Transaction-ID"] = result.get("transaction_id", "")

    if is_cache_hit:
        response.headers["X-Cache-Hit"] = "true"

    return PaymentResponse(**result)
