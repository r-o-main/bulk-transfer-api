from typing import List
from pydantic import BaseModel, Field

from app.amounts.converters import to_cents


class CreditTransfer(BaseModel):
    amount: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=3, max_length=3)
    counterparty_name: str = Field(..., min_length=1)
    counterparty_bic: str = Field(..., min_length=1)  # todo check BIC length
    counterparty_iban: str = Field(..., min_length=1)  # todo check IBAN length
    description: str = Field(..., min_length=10)

    model_config = {
        "extra": "forbid"
    }

    def amount_to_cents(self) -> int:
        return to_cents(self.amount)


class BulkTransferRequest(BaseModel):
    request_id: str
    organization_bic: str = Field(..., min_length=1)  # todo check BIC length
    organization_iban: str = Field(..., min_length=1)  # todo check IBAN length
    credit_transfers: List[CreditTransfer]

    model_config = {
        "extra": "forbid"
    }


class BulkTransferSuccessResponse(BaseModel):
    bulk_id: str  #  UUID
    message: str
    # todo add status endpoint for this bulk request in the response:
    # status_url: str


class ErrorDetails(BaseModel):
    reason: str  # todo Enum
    details: str


class BulkTransferErrorResponse(BulkTransferSuccessResponse):
    error: ErrorDetails
