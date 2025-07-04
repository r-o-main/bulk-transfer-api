from typing import Optional
from uuid import UUID

from sqlmodel import Session

from app.models import db
from app.services.fake_broker_client import FakeBrokerClient
from app.models.job import TransferJob, BulkJob
from app.utils.log_formatter import get_logger


logger = get_logger(__name__)


def process(session: Session, transfer_job: TransferJob) -> Optional[db.Transaction]:
    """
    Process an individual transfer job atomically.

    Executes a single credit transfer from a bulk request, creating a transaction
    record and handling both success and failure scenarios.

    Args:
        session: Database session for atomic operations (must be in transaction)
        transfer_job: Transfer job containing all transfer details

    Returns:
        Transaction record if successful, None if failed or already processed

    Side Effects:
        - Creates transaction record in database
        - Calls external bank system for fund transfer
        - Queues bulk finalization job (success or failure)

    Idempotency:
        Safe to retry - checks for existing transaction by transfer_uuid
    """
    account = session.get(db.BankAccount, transfer_job.bank_account_id)
    if not account:
        logger.error(f"bulk_id={transfer_job.bulk_request_uuid} could not process request as account unknown")
        return None

    already_processed_transaction = db.find_transfer_transaction(
        session=session, transfer_uuid=UUID(transfer_job.transfer_uuid)
    )
    if already_processed_transaction:
        logger.error(f"bulk_id={transfer_job.bulk_request_uuid} transaction {transfer_job.transfer_uuid} "
                     f"already processed")
        return None

    logger.info(f"bulk_id={transfer_job.bulk_request_uuid} account balance={account.balance_cents} "
                f"| ongoing transfers={account.ongoing_transfer_cents}")

    transaction = db.create_transfer_transaction(session=session, transfer_job_data=transfer_job)

    logger.info(f"bulk_id={transfer_job.bulk_request_uuid} transfer_uuid={transaction.transfer_uuid} "
                f"transaction recorded amount={transaction.amount_cents}")

    fake_broker_client = FakeBrokerClient()
    is_remote_transfer_successful = transfer_funds(transfer_job=transfer_job)
    if not is_remote_transfer_successful:
        cancel_bulk_job = BulkJob(
            bulk_request_uuid=transfer_job.bulk_request_uuid,
            bank_account_id=account.id,
            single_transferred_amount_cents=transfer_job.amount_cents,
            success=False
        )
        response = fake_broker_client.queue_finalize_bulk_job(job=cancel_bulk_job)
        logger.debug(f"queued cancel bulk request job: {response}")
        return None

    success_bulk_job = BulkJob(
        bulk_request_uuid=transfer_job.bulk_request_uuid,
        bank_account_id=account.id,
        single_transferred_amount_cents=transfer_job.amount_cents,
        success=True
    )
    response = fake_broker_client.queue_finalize_bulk_job(job=success_bulk_job)
    logger.info(f"queued complete bulk request job: {response}")

    return transaction


def transfer_funds(transfer_job: TransferJob) -> bool:
    # return False  # Simulate failure
    logger.info(f"Fake transfer to external system: {transfer_job.transfer_uuid}")
    try:
        # Assume it works:
        return True
    except Exception as e:  # timeout, etc.
        logger.error(f"Failed to transfer {transfer_job.transfer_uuid} to external system: {e}")
        return False
