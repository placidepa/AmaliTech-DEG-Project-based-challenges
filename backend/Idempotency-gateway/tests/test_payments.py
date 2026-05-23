import asyncio

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

PAYMENT_URL = "/process-payment"
DEFAULT_PAYLOAD = {"amount": 100.0, "currency": "GHS"}


async def post_payment(client: AsyncClient, key: str, payload: dict = DEFAULT_PAYLOAD):
    return await client.post(
        PAYMENT_URL,
        json=payload,
        headers={"Idempotency-Key": key},
    )


# ── Health 

async def test_health_check(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ── User Story 1: First request 

async def test_first_payment_returns_201(client):
    r = await post_payment(client, "key-us1")
    assert r.status_code == 201
    assert "X-Cache-Hit" not in r.headers

    body = r.json()
    assert body["status"] == "success"
    assert body["amount"] == 100.0
    assert body["currency"] == "GHS"
    assert body["message"] == "Charged 100.0 GHS"
    assert "transaction_id" in body
    assert "timestamp" in body


# ── User Story 2: Duplicate request 

async def test_duplicate_returns_cache_hit_header(client):
    r1 = await post_payment(client, "key-us2")
    r2 = await post_payment(client, "key-us2")

    assert r2.status_code == 201
    assert r2.headers.get("X-Cache-Hit") == "true"


async def test_duplicate_returns_identical_body(client):
    r1 = await post_payment(client, "key-us2b")
    r2 = await post_payment(client, "key-us2b")

    assert r1.json() == r2.json()


async def test_duplicate_does_not_reprocess(client):
    r1 = await post_payment(client, "key-us2c")
    r2 = await post_payment(client, "key-us2c")

    assert r1.json()["transaction_id"] == r2.json()["transaction_id"]


# ── User Story 3: Fraud / payload mismatch 

async def test_different_body_same_key_returns_409(client):
    await post_payment(client, "key-us3", {"amount": 100.0, "currency": "GHS"})
    r = await post_payment(client, "key-us3", {"amount": 999.0, "currency": "GHS"})

    assert r.status_code == 409
    assert "different request body" in r.json()["detail"]


# ── Validation errors (422) 

async def test_missing_idempotency_key_returns_422(client):
    r = await client.post(PAYMENT_URL, json=DEFAULT_PAYLOAD)
    assert r.status_code == 422


async def test_zero_amount_returns_422(client):
    r = await post_payment(client, "key-val1", {"amount": 0, "currency": "GHS"})
    assert r.status_code == 422


async def test_four_char_currency_returns_422(client):
    r = await post_payment(client, "key-val2", {"amount": 100.0, "currency": "ABCD"})
    assert r.status_code == 422


# ── Currency normalisation 

async def test_lowercase_currency_treated_as_duplicate(client):
    r1 = await post_payment(client, "key-norm", {"amount": 100.0, "currency": "GHS"})
    r2 = await post_payment(client, "key-norm", {"amount": 100.0, "currency": "ghs"})

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r2.headers.get("X-Cache-Hit") == "true"


# ── Bonus: Race condition 

async def test_concurrent_requests_return_same_result(client):
    async def make_request():
        return await post_payment(client, "key-race", {"amount": 200.0, "currency": "GHS"})

    r1, r2 = await asyncio.gather(make_request(), make_request())

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["transaction_id"] == r2.json()["transaction_id"]
