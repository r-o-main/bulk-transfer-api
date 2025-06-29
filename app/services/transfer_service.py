from typing import Optional
from uuid import UUID

from sqlmodel import Session

from app.models import db
# from app.services import bulk_request_service
from app.services.fake_broker_client import FakeBrokerClient
from app.models.job import TransferJob, BulkJob

from app.utils.log_formatter import get_logger
logger = get_logger(__name__)


# async def process(session: Session, transfer_job: TransferJob) -> Optional[db.Transaction]:
def process(session: Session, transfer_job: TransferJob) -> Optional[db.Transaction]:
    with session.begin():
        # account = db.select_account_for_update(session=session, bic=request.organization_bic,
        #                                        iban=request.organization_iban)  # todo by id
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
        # is_remote_transfer_successful = await transfer_funds(transfer_job=transfer_job)
        is_remote_transfer_successful = transfer_funds(transfer_job=transfer_job)
        if not is_remote_transfer_successful:
            cancel_bulk_job = BulkJob(
                bulk_request_uuid=transfer_job.bulk_request_uuid,
                bank_account_id=account.id,
                single_transferred_amount_cents=transfer_job.amount_cents,
                success=False
            )
            # response = await fake_broker_client.queue_finalize_bulk_job(job=cancel_bulk_job)  # cancel
            response = fake_broker_client.queue_finalize_bulk_job(job=cancel_bulk_job)  # cancel
            logger.info(f"queued cancel bulk request job: {response}")
            # session.rollback()
            return None

        # bulk_request_service.finalize_bulk_transfer(
        #     session=session,
        #     bulk_request_uuid=transfer_job.bulk_request_uuid,
        #     account=account,
        #     # total_transfer_amounts_cents=total_transfer_amounts_cents,
        #     transferred_amount_cents=transfer_job.amount_cents
        # )
        success_bulk_job = BulkJob(
            bulk_request_uuid=transfer_job.bulk_request_uuid,
            bank_account_id=account.id,
            single_transferred_amount_cents=transfer_job.amount_cents,
            success=True
        )
        # response = await fake_broker_client.queue_finalize_bulk_job(job=success_bulk_job)
        response = fake_broker_client.queue_finalize_bulk_job(job=success_bulk_job)
        logger.info(f"queued complete bulk request job: {response}")

        return transaction


# async def transfer_funds(transfer_job: TransferJob) -> bool:
def transfer_funds(transfer_job: TransferJob) -> bool:
    # return False  # TEST
    logger.info(f"Fake transfer to external system: {transfer_job.transfer_uuid}")
    try:
        # Assume it works
        return True
    except Exception as e:
        logger.error(f"Failed to transfer {transfer_job.transfer_uuid} to external system: {e}")
        return False