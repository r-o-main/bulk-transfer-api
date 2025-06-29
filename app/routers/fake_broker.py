import logging
from uuid import UUID

from fastapi import APIRouter, status, Depends, HTTPException
from sqlmodel import Session
from app.models.db import get_session

from pydantic import BaseModel


# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)
# from app.utils.log_formatter import logger
from app.utils.log_formatter import get_logger
logger = get_logger(__name__)

router = APIRouter()

# Fake "topics": all jobs of same type are in the same list (FIFO).
# With a real message broker, the different bulk requests could be processed
# in parallel, using the bulk_request_uuid as routing scope for instance.
TRANSFER_JOB_QUEUE = []
FINALIZE_BULK_JOB_QUEUE = []


class TransferJob(BaseModel):
    transfer_uuid: UUID
    bulk_request_uuid: UUID
    bank_account_id: int
    counterparty_name: str
    counterparty_iban: str
    counterparty_bic: str
    amount_cents: int
    amount_currency: str
    description: str


class BulkJob(BaseModel):
    bulk_request_uuid: UUID
    bank_account_id: int
    total_transfer_amounts: int


@router.post("/transfer", status_code=status.HTTP_201_CREATED)
async def enqueue_transfer_job(transfer_job: TransferJob):
    TRANSFER_JOB_QUEUE.append(transfer_job)
    logger.info(f"Queued transfer job {transfer_job.transfer_uuid}: {transfer_job} "
                f"[queue:{len(TRANSFER_JOB_QUEUE)} jobs]")
    return {
        "status": "enqueued",
        "transfer_id": transfer_job.transfer_uuid,
        "bulk_request_uuid": transfer_job.bulk_request_uuid,
        "type": "process-transfer"
    }

@router.get("/transfer", response_model=TransferJob, status_code=status.HTTP_200_OK)
async def consume_transfer_job(session: Session = Depends(get_session)):
    try:
        transfer_job = TRANSFER_JOB_QUEUE.pop()
        logger.info(f"Consuming transfer job {transfer_job.transfer_uuid}: {transfer_job} "
                    f"[queue: pending {len(TRANSFER_JOB_QUEUE)} jobs to be processed]")
    except IndexError:
        raise HTTPException(status_code=404, detail="No transfer job in queue")
    return transfer_job


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def enqueue_finalize_bulk_job(bulk_job: BulkJob):
    FINALIZE_BULK_JOB_QUEUE.append(bulk_job)
    logger.info(f"Queued bulk job {bulk_job.bulk_request_uuid}: {bulk_job} "
                f"[queue: {len(FINALIZE_BULK_JOB_QUEUE)} jobs]")
    return {
        "status": "enqueued",
        "bulk_request_uuid": bulk_job.bulk_request_uuid,
        "type": "finalize-bulk"
    }

@router.get("/bulk", response_model=BulkJob, status_code=status.HTTP_200_OK)
async def consume_finalize_bulk_job(session: Session = Depends(get_session)):
    try:
        bulk_job = FINALIZE_BULK_JOB_QUEUE.pop()
        logger.info(f"Consuming bulk job {bulk_job.bulk_request_uuid}: {bulk_job} "
                    f"[queue: pending {len(FINALIZE_BULK_JOB_QUEUE)} jobs to be processed]")
    except IndexError:
        raise HTTPException(status_code=404, detail="No bulk job in queue")
    return bulk_job
