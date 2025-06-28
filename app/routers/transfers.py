import uuid

from fastapi import APIRouter, status
# from app.models.schemas import BulkTransferRequest
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


router = APIRouter()  # https://fastapi.tiangolo.com/reference/apirouter


class CreditTransfer(BaseModel):  # todo enforce strict mode
    transfer_id: Optional[UUID] = None
    amount: str
    currency: str
    counterparty_name: str
    counterparty_bic: str
    counterparty_iban: str
    description: str

    model_config = {
        "extra": "forbid"
    }


class BulkTransferRequest(BaseModel):  # todo enforce strict mode
    # bulk_id: UUID  # todo Milestone 3
    organization_bic: str
    organization_iban: str
    credit_transfers: List[CreditTransfer]

    model_config = {
        "extra": "forbid"
    }


@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Organization not found"},
        422: {"description": "Insufficient funds"},
    }
)
def create_bulk_transfer(request: BulkTransferRequest):  # todo check async
    # todo
    # checks: first additional validation (such as amounts are positive and can be converted to int), amounts are enough, etc.
    # return {"message": "Bulk transfer accepted", "bulk_id": str(request.bulk_id)}
    return {"message": "Bulk transfer accepted", "bulk_id": str(uuid.uuid4())}
