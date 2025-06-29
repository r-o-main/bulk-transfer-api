import datetime
from typing import cast, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Select
from sqlmodel import Session, select

from app.models import db
from app.models.adapter import CreditTransfer
from app.services.fake_broker_client import FakeBrokerClient, build_transfer_job

from app.utils.log_formatter import get_logger
logger = get_logger(__name__)


async def schedule_transfers(
        session: Session, bulk_request_uuid: str, account: db.BankAccount, total_transfer_amounts_cents: int, credit_transfers: List[CreditTransfer]
) -> db.BulkRequest:
    bulk_request = db.create_bulk_request(
        session=session,
        bulk_request_uuid=UUID(bulk_request_uuid),
        bank_account_id=account.id,
        total_amounts_cents=total_transfer_amounts_cents
    )
    session.flush()
    db.reserve_funds(session=session, account=account, total_transfer_amounts=total_transfer_amounts_cents)

    fake_broker_client = FakeBrokerClient()
    for credit_transfer in credit_transfers:
        response = await fake_broker_client.queue_transfer_job(
            job=build_transfer_job(
                bulk_request_uuid=bulk_request_uuid,
                transfer_uuid=str(uuid4()),
                bank_account_id=account.id,
                credit_transfer=credit_transfer
            )
        )
        logger.warning(f"queued transfer job: {response}")
    logger.warning(f"queued all transfer jobs")

    return bulk_request


# def finalize_bulk_transfer(
#         session: Session,
#         bulk_request_uuid: UUID,
#         account: db.BankAccount,
#         total_transfer_amounts_cents: int,
#         transferred_amount_cents: int,
# ):
def finalize_bulk_transfer(
        session: Session,
        bulk_request: db.BulkRequest,
        account: db.BankAccount,
        single_transferred_amount_cents: int
) -> Optional[db.BulkRequest]:
    # bulk_request = db.select_bulk_request_for_update(session=session, bulk_request_uuid=bulk_request_uuid)
    bulk_request_uuid = bulk_request.request_uuid
    logger.info(f"bulk_id={bulk_request_uuid} FINALIZE account_id={account.id} "
                f"single_transferred_amount_cents={single_transferred_amount_cents}")

    if not bulk_request:
        logger.warning(f"bulk_id={bulk_request_uuid} not found in database")
        return None

    if bulk_request.status in [db.RequestStatus.FAILED, db.RequestStatus.COMPLETED]:
        logger.warning(f"bulk_id={bulk_request_uuid} already finalized status={bulk_request.status}")
        return bulk_request

    bulk_request.processed_amount_cents += single_transferred_amount_cents
    if bulk_request.processed_amount_cents < bulk_request.total_amount_cents:
        session.add(bulk_request)
        logger.info(f"bulk_id={bulk_request_uuid} status={bulk_request.status} not yet fully processed "
                    f"(processed_amount_cents={bulk_request.processed_amount_cents}|"
                    f"total_transferred_amounts_cents={bulk_request.total_amount_cents})")
        return bulk_request

    account.ongoing_transfer_cents -= bulk_request.total_amount_cents
    account.balance_cents -= bulk_request.total_amount_cents
    # todo add safety guards on balance_cents > 0 and ongoing_transfer_cents > 0
    bulk_request.status = db.RequestStatus.COMPLETED
    bulk_request.completed_at = datetime.datetime.now(datetime.UTC)

    logger.info(f"bulk_id={bulk_request_uuid} FINALIZE END bulk_request={bulk_request}")

    session.add_all([bulk_request, account])
    return bulk_request


# def cancel_bulk_transfer(session: Session, bulk_request_uuid: UUID, account: db.BankAccount, total_transfer_amounts: int):
def cancel_bulk_transfer(
        session: Session,
        bulk_request: db.BulkRequest,
        account: db.BankAccount
) -> Optional[db.BulkRequest]:
    # bulk_request = db.select_bulk_request_for_update(session=session, bulk_request_uuid=bulk_request_uuid)
    bulk_request_uuid = bulk_request.request_uuid
    logger.info(f"bulk_id={bulk_request_uuid} CANCEL account_id={account.id} "
                f"total_transfer_amounts={bulk_request.total_amount_cents}")

    if not bulk_request:
        logger.warning(f"bulk_id={bulk_request_uuid} not found in database")
        return None

    if bulk_request.status == db.RequestStatus.FAILED:
        logger.info(f"bulk_id={bulk_request_uuid} already cancelled status={bulk_request.status}")
        return None

    account.ongoing_transfer_cents -= bulk_request.total_amount_cents
    # todo add safety guards on ongoing_transfer_cents > 0

    bulk_request.status = db.RequestStatus.FAILED
    bulk_request.completed_at = datetime.datetime.now(datetime.UTC)
    logger.info(f"bulk_id={bulk_request_uuid} FINALIZE END bulk_request={bulk_request}")

    session.add_all([bulk_request, account])
    return bulk_request
