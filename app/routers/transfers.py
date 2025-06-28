from fastapi import APIRouter, status
# from app.models.schemas import BulkTransferRequest
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


router = APIRouter()  # https://fastapi.tiangolo.com/reference/apirouter


class CreditTransfer(BaseModel):
    transfer_id: Optional[UUID] = None
    amount: str
    currency: str
    counterparty_name: str
    counterparty_bic: str
    counterparty_iban: str
    description: str


class BulkTransferRequest(BaseModel):
    bulk_id: UUID
    organization_bic: str
    organization_iban: str
    credit_transfers: List[CreditTransfer]


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def create_bulk_transfer(request: BulkTransferRequest):  # todo check async
    # todo
    return {"message": "Bulk transfer accepted", "bulk_id": str(request.bulk_id)}
