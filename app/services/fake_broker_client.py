from typing import Type, Optional
from uuid import UUID

import httpx
from pydantic import BaseModel
# from fastapi.testclient import TestClient

# from app.main import app
from app.models.adapter import CreditTransfer


class TransferJob(BaseModel):
    transfer_uuid: str
    bulk_request_uuid: str
    bank_account_id: int
    counterparty_name: str
    counterparty_iban: str
    counterparty_bic: str
    amount_cents: int
    amount_currency: str
    description: str


def build_transfer_job(
        bulk_request_uuid: str, transfer_uuid: str, bank_account_id: int, credit_transfer: CreditTransfer
) -> TransferJob:
    return TransferJob(
        transfer_uuid=transfer_uuid,  # todo check
        bulk_request_uuid=bulk_request_uuid,
        bank_account_id=bank_account_id,
        counterparty_name=credit_transfer.counterparty_name,
        counterparty_iban=credit_transfer.counterparty_iban,
        counterparty_bic=credit_transfer.counterparty_bic,
        amount_cents=credit_transfer.amount_to_cents(),
        amount_currency=credit_transfer.currency,
        description=credit_transfer.description
    )


class BulkJob(BaseModel):
    bulk_request_uuid: str
    bank_account_id: int
    single_transferred_amount_cents: int
    success: bool


class FakeBrokerClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/internal/jobs"):
        # self.client = TestClient(app)
        self.base_url = base_url.rstrip("/")

    # async def _post_json(self, endpoint: str, payload: dict) -> dict:
    def _post_json(self, endpoint: str, payload: dict) -> dict:
        # response = self.client.post(f"/internal/jobs/{endpoint.lstrip('/')}", json=payload)
        # response.raise_for_status()
        # return response.json()
        # async with httpx.AsyncClient() as client:
        with httpx.Client() as client:
            # response = await client.post(f"{self.base_url}/{endpoint.lstrip('/')}", json=payload)
            response = client.post(f"{self.base_url}/{endpoint.lstrip('/')}", json=payload)
            response.raise_for_status()
            return response.json()

    # async def _get_json(self, endpoint: str, model: Type[BaseModel]) -> Optional[BaseModel]:
    def _get_json(self, endpoint: str, model: Type[BaseModel]) -> Optional[BaseModel]:
        # response = self.client.get(f"/internal/jobs/{endpoint.lstrip('/')}")
        # if response.status_code == 200 and response.content:
        #     return model(**response.json())
        # return None
        # async with httpx.AsyncClient() as client:
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/{endpoint.lstrip('/')}")
            # response = await client.get(f"{self.base_url}/{endpoint.lstrip('/')}")
            if response.status_code == 200 and response.content:
                return model(**response.json())
            return None

    # async def queue_transfer_job(self, job: TransferJob) -> dict:
    def queue_transfer_job(self, job: TransferJob) -> dict:
        # return await self._post_json("/transfer", job.model_dump())
        return self._post_json("/transfer", job.model_dump())

    # async def queue_finalize_bulk_job(self, job: BulkJob) -> dict:
    def queue_finalize_bulk_job(self, job: BulkJob) -> dict:
        # return await self._post_json("/bulk", job.model_dump())
        return self._post_json("/bulk", job.model_dump())

    # async def consume_transfer_job(self) -> Optional[TransferJob]:
    def consume_transfer_job(self) -> Optional[TransferJob]:
        # return await self._get_json("/transfer", TransferJob)
        return self._get_json("/transfer", TransferJob)

    def consume_bulk_job(self) -> Optional[BulkJob]:
    # async def consume_bulk_job(self) -> Optional[BulkJob]:
    #     return await self._get_json("/bulk", BulkJob)
        return  self._get_json("/bulk", BulkJob)
