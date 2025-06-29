from typing import Type, Optional
import httpx
from pydantic import BaseModel

from app.routers.fake_broker import TransferJob, BulkJob


class FakeBrokerClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/internal/jobs"):
        self.base_url = base_url.rstrip("/")

    async def _post_json(self, endpoint: str, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/{endpoint.lstrip('/')}", json=payload)
            response.raise_for_status()
            return response.json()

    async def _get_json(self, endpoint: str, model: Type[BaseModel]) -> Optional[BaseModel]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/{endpoint.lstrip('/')}")
            if response.status_code == 200 and response.content:
                return model(**response.json())
            return None

    async def queue_transfer_job(self, job: TransferJob) -> dict:
        return await self._post_json("internal/jobs/transfer", job.model_dump())

    async def queue_finalize_bulk_job(self, job: BulkJob) -> dict:
        return await self._post_json("internal/jobs/bulk", job.model_dump())

    async def consume_transfer_job(self) -> Optional[TransferJob]:
        return await self._get_json("internal/jobs/transfer", TransferJob)

    async def consume_bulk_job(self) -> Optional[BulkJob]:
        return await self._get_json("internal/jobs/bulk", BulkJob)
