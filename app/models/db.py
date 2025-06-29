# https://fastapi.tiangolo.com/tutorial/sql-databases/
import datetime
import logging
from enum import Enum
from typing import Optional, cast
from uuid import UUID, uuid4

from sqlalchemy import Select
from sqlmodel import create_engine, SQLModel, Field, Column, DateTime, select, Session

from app.models import adapter

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)
# from app.utils.log_formatter import logger
from app.utils.log_formatter import get_logger
logger = get_logger(__name__)


DATABASE_PATH = "./qonto_accounts.sqlite"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def get_session():
    with Session(engine) as session:
        yield session


class BankAccount(SQLModel, table=True):
    __tablename__ = "bank_accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    organization_name: str = Field(nullable=False)
    iban: str = Field(nullable=False)
    bic: str = Field(nullable=False)
    balance_cents: int = Field(default=0, nullable=False)
    ongoing_transfer_cents: int = Field(default=0, nullable=False)


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    transfer_uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    bulk_request_uuid: UUID
    counterparty_name: str = Field(nullable=False)
    counterparty_iban: str = Field(nullable=False)
    counterparty_bic: str = Field(nullable=False)
    amount_cents: int = Field(nullable=False)
    amount_currency: str = Field(nullable=False)
    bank_account_id: int = Field(nullable=False)
    description: str = Field(nullable=False)
    # todo add timestamp


class RequestStatus(str, Enum):
    """
    Enum for bulk request and individual transfer requests status values
    """
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BulkRequest(SQLModel, table=True):
    __tablename__ = "bulk_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    request_uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    bank_account_id: int = Field(nullable=False)
    status: RequestStatus = Field(default=RequestStatus.PENDING, nullable=False)
    total_amount_cents: int = Field(default=0, nullable=False)
    processed_amount_cents: int = Field(default=0, nullable=False)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    )
    completed_at: Optional[datetime.datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )


def find_account_for_update(session: Session, bic: str, iban: str) -> Optional[BankAccount]:
    statement = select(BankAccount).where(
        BankAccount.bic == bic.strip(),
        BankAccount.iban == iban.strip()
    ).with_for_update()
    statement = cast(Select, statement)
    return session.exec(statement).first()


def reserve_funds(session: Session, account: BankAccount, total_transfer_amounts: int):
    account.ongoing_transfer_cents += total_transfer_amounts
    session.add(account)


def finalize_bulk_transfer(
        session: Session,
        bulk_request_uuid: UUID,
        account: BankAccount,
        total_transfer_amounts_cents: int,
        transferred_amount_cents: int,
):
    statement = select(BulkRequest).where(BulkRequest.request_uuid == bulk_request_uuid).with_for_update()
    # statement = select(BulkRequest).where(BulkRequest.id == bulk_request_id).with_for_update()
    statement = cast(Select, statement)
    bulk_request = session.exec(statement).first()
    logger.info(f"bulk_id={bulk_request_uuid} FINALIZE account_id={account.id} total_transfer_amounts={total_transfer_amounts_cents}")

    if not bulk_request:
        logger.warning(f"bulk_id={bulk_request_uuid} not found in databse")
        return

    if bulk_request.status in [RequestStatus.FAILED, RequestStatus.COMPLETED]:
        logger.warning(f"bulk_id={bulk_request_uuid} already finalized status={bulk_request.status}")
        return

    bulk_request.processed_amount_cents += transferred_amount_cents
    if bulk_request.processed_amount_cents < total_transfer_amounts_cents:
        session.add(bulk_request)
        logger.info(f"bulk_id={bulk_request_uuid} status={bulk_request.status} not yet fully processed "
                       f"(processed_amount_cents={bulk_request.processed_amount_cents}|"
                       f"total_transfer_amounts_cents={total_transfer_amounts_cents})")
        return

    account.ongoing_transfer_cents -= total_transfer_amounts_cents
    account.balance_cents -= total_transfer_amounts_cents
    # session.add(account)
    # todo add safety guards on balance_cents > 0 and ongoing_transfer_cents > 0

    bulk_request.status = RequestStatus.COMPLETED
    bulk_request.completed_at = datetime.datetime.now(datetime.UTC)

    # todo update counters
    logger.info(f"bulk_id={bulk_request_uuid} FINALIZE END bulk_request={bulk_request}")

    session.add_all([bulk_request, account])


def cancel_bulk_transfer(session: Session, bulk_request_uuid: UUID, account: BankAccount, total_transfer_amounts: int):
    statement = select(BulkRequest).where(BulkRequest.request_uuid == bulk_request_uuid).with_for_update()
    statement = cast(Select, statement)
    bulk_request = session.exec(statement).first()
    logger.info(f"bulk_id={bulk_request_uuid} CANCEL account_id={account.id} total_transfer_amounts={total_transfer_amounts}")

    if not bulk_request:
        logger.warning(f"bulk_id={bulk_request_uuid} not found in database")
        return
    if bulk_request.status == RequestStatus.FAILED:
        logger.info(f"bulk_id={bulk_request_uuid} already cancelled status={bulk_request.status}")
        return

    account.ongoing_transfer_cents -= total_transfer_amounts
    # todo add safety guards on ongoing_transfer_cents > 0

    bulk_request.status = RequestStatus.FAILED
    bulk_request.completed_at = datetime.datetime.now(datetime.UTC)
    # todo update counters
    logger.info(f"bulk_id={bulk_request_uuid} FINALIZE END bulk_request={bulk_request}")

    session.add_all([bulk_request, account])


def create_transfer_transaction(
        session: Session, bank_account_id: int, credit_transfer: adapter.CreditTransfer, bulk_request_id: Optional[UUID] = None
) -> Transaction:
    transfer_transaction = Transaction(
        # transfer_uuid=credit_transfer.transfer_id if credit_transfer.transfer_id else uuid.uuid4(),
        transfer_uuid=uuid4(),  # todo use the one from the job
        bulk_request_uuid=bulk_request_id if bulk_request_id else None,
        counterparty_name=credit_transfer.counterparty_name,
        counterparty_iban=credit_transfer.counterparty_iban,
        counterparty_bic=credit_transfer.counterparty_bic,
        amount_cents=-credit_transfer.amount_to_cents(),
        amount_currency=credit_transfer.currency,
        bank_account_id=bank_account_id,
        description=credit_transfer.description
    )
    session.add(transfer_transaction)
    # session.refresh(transfer_transaction)
    return transfer_transaction


def find_bulk_request(session: Session, bulk_request_uuid: UUID) -> Optional[BulkRequest]:
    statement = select(BulkRequest).where(BulkRequest.request_uuid == bulk_request_uuid)
    statement = cast(Select, statement)
    return session.exec(statement).first()


def create_bulk_request(
        session: Session, bank_account_id: int, bulk_request_uuid: UUID, total_amounts_cents: int
) -> BulkRequest:
    bulk_request = BulkRequest(
        request_uuid=bulk_request_uuid,
        bank_account_id=bank_account_id,
        total_amount_cents=total_amounts_cents,
        processed_amount_cents=0,
        status=RequestStatus.PENDING,
        created_at=datetime.datetime.now(datetime.UTC)
    )
    session.add(bulk_request)
    return bulk_request
