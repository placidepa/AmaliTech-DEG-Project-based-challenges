from pydantic import BaseModel, Field, field_validator


class PaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Payment amount, must be greater than zero")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code, e.g. GHS, USD, RWF")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        # Normalise so "ghs" and "GHS" are treated as the same payload,
        # preventing false 409s on retries that differ only in case.
        return v.upper()


class PaymentResponse(BaseModel):
    """Consistent response envelope returned for every successful payment outcome."""
    transaction_id: str = Field(..., description="UUID v4 assigned at processing time")
    status: str = Field(..., description="'success' for completed payments")
    message: str = Field(..., description="Human-readable outcome, e.g. 'Charged 100.0 GHS'")
    amount: float = Field(..., description="Payment amount as submitted")
    currency: str = Field(..., description="Normalised ISO 4217 currency code")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of when the charge was made")
