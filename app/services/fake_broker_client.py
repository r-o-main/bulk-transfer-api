from typing import Type, Optional
from pydantic import BaseModel

from app.models.job import TransferJob, BulkJob


class FakeBrokerClient:
    def __init__(self):
        from app.main import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    def _post_json(self, endpoint: str, payload: dict) -> dict:
        response = self.client.post(f"/internal/jobs/{endpoint.lstrip('/')}", json=payload)
        response.raise_for_status()
        return response.json()

    def _get_json(self, endpoint: str, model: Type[BaseModel]) -> Optional[BaseModel]:
        response = self.client.get(f"/internal/jobs/{endpoint.lstrip('/')}")
        if response.status_code == 200 and response.content:
            return model(**response.json())
        return None

    def queue_transfer_job(self, job: TransferJob) -> dict:
        return self._post_json("/transfer", job.model_dump())

    def queue_finalize_bulk_job(self, job: BulkJob) -> dict:
        return self._post_json("/bulk", job.model_dump())

    def consume_transfer_job(self) -> Optional[TransferJob]:
        return self._get_json("/transfer", TransferJob)

    def consume_bulk_job(self) -> Optional[BulkJob]:
        return self._get_json("/bulk", BulkJob)
