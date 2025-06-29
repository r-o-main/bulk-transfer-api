from collections import deque
from uuid import UUID
from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session
from app.models import db
from app.services import transfer_service, bulk_request_service

from app.models.job import TransferJob, BulkJob

from app.utils.log_formatter import get_logger
logger = get_logger(__name__)

router = APIRouter()

# Fake "topics": all jobs of same type are in the same list (FIFO).
# With a real message broker, the different bulk requests could be processed
# in parallel, using the bulk_request_uuid as routing scope for instance.
TRANSFER_JOB_QUEUE = deque()
FINALIZE_BULK_JOB_QUEUE = deque()
# todo next:
RECONCILIATION_JOB_QUEUE = deque()
SEND_WEBHOOK_JOB_QUEUE = deque()


@router.post("/transfer", status_code=status.HTTP_201_CREATED)
def enqueue_transfer_job(transfer_job: TransferJob):
    TRANSFER_JOB_QUEUE.append(transfer_job)
    logger.info(f"Queued transfer job {transfer_job.transfer_uuid}: {transfer_job} "
                f"[queue:{len(TRANSFER_JOB_QUEUE)} jobs]")
    return {
        "status": "enqueued",
        "transfer_uuid": transfer_job.transfer_uuid,
        "bulk_request_uuid": transfer_job.bulk_request_uuid,
        "type": "process-transfer"
    }


@router.get("/transfer", status_code=status.HTTP_200_OK)
def consume_transfer_job(session: Session = Depends(db.get_session)):
    try:
        transfer_job = TRANSFER_JOB_QUEUE.popleft()
        logger.info(f"Consuming transfer job {transfer_job.transfer_uuid}: {transfer_job} "
                    f"[queue: pending {len(TRANSFER_JOB_QUEUE)} jobs to be processed]")
    except IndexError:
        raise HTTPException(status_code=404, detail="No transfer job in queue")

    transaction = transfer_service.process(session=session, transfer_job=transfer_job)
    if not transaction:
        logger.warning(f"Processing of transfer job {transfer_job.transfer_uuid} failed or was aborted.")
        return JSONResponse(
            status_code=422, content={
                "status": "failed",
                "transfer_uuid": transfer_job.transfer_uuid,
                "bulk_request_uuid": transfer_job.bulk_request_uuid,
                "type": "process-transfer",
                "details": f"Processing of transfer job {transfer_job.transfer_uuid} failed or was aborted"
            }
        )

    return {
        "status": "processed",
        "transfer_id": str(transaction.transfer_uuid),
        "amount_cents": transaction.amount_cents,
        "bulk_request_uuid": transfer_job.bulk_request_uuid,
        "type": "process-transfer"
    }


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def enqueue_finalize_bulk_job(bulk_job: BulkJob):
    FINALIZE_BULK_JOB_QUEUE.append(bulk_job)
    logger.info(f"Queued bulk job {bulk_job.bulk_request_uuid}: {bulk_job} "
                f"[queue: {len(FINALIZE_BULK_JOB_QUEUE)} jobs]")
    return {
        "status": "enqueued",
        "bulk_request_uuid": bulk_job.bulk_request_uuid,
        "type": "finalize-bulk"
    }


@router.get("/bulk", status_code=status.HTTP_200_OK)
def consume_finalize_bulk_job(session: Session = Depends(db.get_session)):
    try:
        bulk_job = FINALIZE_BULK_JOB_QUEUE.popleft()
        logger.info(f"Consuming bulk job {bulk_job.bulk_request_uuid}: {bulk_job} "
                    f"[queue: pending {len(FINALIZE_BULK_JOB_QUEUE)} jobs to be processed]")
    except IndexError:
        raise HTTPException(status_code=404, detail="No bulk job in queue")

    with session.begin():
        account: db.BankAccount | None = session.get(db.BankAccount, bulk_job.bank_account_id)
        if not account:
            logger.warning(f"bulk_id={bulk_job.bulk_request_uuid} could not finalize: account not found")
            raise HTTPException(
                status_code=404,
                detail=f"Account not found for bulk request {bulk_job.bulk_request_uuid}"
            )

        bulk_request = db.select_bulk_request_for_update(
            session=session, bulk_request_uuid=UUID(bulk_job.bulk_request_uuid)
        )
        if not bulk_request:
            logger.warning(f"bulk_id={bulk_job.bulk_request_uuid} not found in database")
            raise HTTPException(status_code=404, detail=f"Bulk request {bulk_job.bulk_request_uuid} not found")

        if bulk_job.success:
            final_bulk_request = bulk_request_service.finalize_bulk_transfer(
                session=session,
                bulk_request=bulk_request,
                account=account,
                single_transferred_amount_cents=bulk_job.single_transferred_amount_cents
            )
        else:
            final_bulk_request = bulk_request_service.cancel_bulk_transfer(
                session=session,
                bulk_request=bulk_request,
                account=account,
            )

        if final_bulk_request is None:
            logger.warning(f"Processing of bulk job {bulk_job.bulk_request_uuid} failed or was aborted.")
            # todo next: queue reconciliation job and send ID in the response
            return JSONResponse(
                status_code=422, content={
                    "type": "finalize-bulk",
                    "status": "failed",
                    "bulk_request_uuid": bulk_job.bulk_request_uuid,
                    "total_transferred_amounts_cents": bulk_request.total_amount_cents,
                    "processed_amounts_cents": bulk_request.processed_amount_cents,
                    "details": "Processing of bulk job failed or was aborted",
                    "reconciliation_job_uuid": "todo"
                }
            )

        return {
            "type": "finalize-bulk",
            "status": final_bulk_request.status,
            "bulk_request_uuid": bulk_job.bulk_request_uuid,
            "total_transferred_amounts_cents": bulk_request.total_amount_cents,
            "processed_amounts_cents": bulk_request.processed_amount_cents,
            "completed_at": final_bulk_request.completed_at.isoformat() if final_bulk_request.completed_at else None
        }
