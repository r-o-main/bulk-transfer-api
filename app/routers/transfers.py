import uuid
import decimal
import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
# from app.models.schemas import BulkTransferRequest
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from uuid import UUID


logger = logging.getLogger(__name__)


router = APIRouter()  # https://fastapi.tiangolo.com/reference/apirouter


class CreditTransfer(BaseModel):  # todo enforce strict mode
    transfer_id: Optional[UUID] = None
    amount: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=3, max_length=3)
    counterparty_name: str = Field(..., min_length=1)
    counterparty_bic: str = Field(..., min_length=1)  # todo check BIC length
    counterparty_iban: str = Field(..., min_length=1)  # todo check IBAN length
    description: str = Field(..., min_length=10)

    model_config = {
        "extra": "forbid"
    }


    # @field_validator("amount", mode="after")
    # @classmethod
    # def validate_amount(cls, value):
    #     to_cents(amount_in_euros_str=value)
    #     return value

    def amount_to_cents(self) -> int:
        return to_cents(self.amount)


class BulkTransferRequest(BaseModel):  # todo enforce strict mode
    # bulk_id: UUID  # todo Milestone 3
    organization_bic: str = Field(..., min_length=1)  # todo check BIC length
    organization_iban: str = Field(..., min_length=1)  # todo check IBAN length
    credit_transfers: List[CreditTransfer]

    model_config = {
        "extra": "forbid"
    }


class BulkTransferSuccessResponse(BaseModel):
    bulk_id: str  #  UUID
    message: str


class ErrorDetails(BaseModel):
    reason: str  # todo Enum
    details: str


class BulkTransferErrorResponse(BulkTransferSuccessResponse):
    error: ErrorDetails


def _bulk_error(bulk_id: UUID, reason: str, error_details: str) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=BulkTransferErrorResponse(
            bulk_id=str(bulk_id), message="Bulk transfer denied", error=ErrorDetails(reason=reason, details=error_details)
        ).model_dump()
    )

def reply_not_enough_funds_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=bulk_id,
        reason='insufficient-account-balance',  # todo ENUM
        error_details=error_details if error_details else "Not enough funds"
    )

def reply_amounts_should_be_positive_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=bulk_id,
        reason='negative-or-null-amounts',  # todo ENUM
        error_details=error_details if error_details else "All amounts should be strictly greater than zero"
    )


def reply_amounts_invalid_format_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=bulk_id,
        reason='invalid-amount',  # todo ENUM
        error_details=error_details if error_details else "All amounts should be numbers and not have more than 2 decimal places"
    )


def to_cents(amount_in_euros_str: str) -> int:
    try:
        amount_in_euros = decimal.Decimal(amount_in_euros_str)
    except Exception:
        raise ValueError(f"Invalid amount: {amount_in_euros_str}")
    rounded_amount_in_euros = amount_in_euros.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)
    if amount_in_euros != rounded_amount_in_euros:
        raise ValueError(f"More than 2 decimal places is not allowed: {amount_in_euros_str}")
    amount_in_cents = rounded_amount_in_euros * 100
    return int(amount_in_cents)


@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    response_model=BulkTransferSuccessResponse,
    responses={  # https://fastapi.tiangolo.com/advanced/additional-responses/
        400: {"model": BulkTransferErrorResponse, "description": "Bad Request"},
        404: {"model": BulkTransferErrorResponse, "description": "Organization or Account not found"},
        # 422: {"description": "Payload does not match spec"},
        422: {"model": BulkTransferErrorResponse, "description": "Bulk transfer denied"},  # todo list of reasons (provide details in response) + handle mismatch patload vs Pydantic model
    }
)
def create_bulk_transfer(request: BulkTransferRequest):  # todo check async
    """
    /docs
    """
    # todo
    bulk_id = uuid.uuid4()  # todo handle idempotency
    # checks: first additional validation (such as amounts are positive and can be converted to int), amounts are enough, etc.
    # decimal_context = decimal.getcontext()
    # decimal_context.prec = 2
    # decimal_context.rounding = decimal.ROUND_HALF_UP

    amounts_in_cents = []
    try:
        amounts_in_cents = [to_cents(amount_in_euros_str=credit_transfer.amount) for credit_transfer in
                            request.credit_transfers]
    except ValueError as e:
        logger.error(f"bulk_id={bulk_id} could not process request: {e}")  # todo add logging context
        return reply_amounts_invalid_format_error(bulk_id=bulk_id, error_details=str(e))

    all_transfer_amounts_are_valid = all(amount > 0 for amount in amounts_in_cents)
    if not all_transfer_amounts_are_valid:
        logger.error(f"bulk_id={bulk_id} could not process request as not all amounts are > 0: {amounts_in_cents}")  # todo add logging context
        return reply_amounts_should_be_positive_error(bulk_id=bulk_id)
        # raise HTTPException(status_code=422, detail="Bulk transfer denied")

    # return {"message": "Bulk transfer accepted", "bulk_id": str(request.bulk_id)}
    return {"message": "Bulk transfer accepted", "bulk_id": str(bulk_id)}
    # return JSONResponse(
    #     status_code=201,
    #     content=BulkTransferSuccessResponse(bulk_id=str(bulk_id), message="Bulk transfer accepted").model_dump()
    # )
