import datetime
from enum import Enum
from typing import Optional, cast
from uuid import UUID, uuid4
from sqlalchemy import Select
from sqlmodel import create_engine, SQLModel, Field, Column, DateTime, select, Session

from app.models.job import TransferJob
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

#--- Bank Account


def select_account_for_update(session: Session, bic: str, iban: str) -> Optional[BankAccount]:
    statement = select(BankAccount).where(
        BankAccount.bic == bic.strip(),
        BankAccount.iban == iban.strip()
    ).with_for_update()
    statement = cast(Select, statement)
    return session.exec(statement).first()


def reserve_funds(session: Session, account: BankAccount, total_transfer_amounts: int):
    account.ongoing_transfer_cents += total_transfer_amounts
    session.add(account)


#--- Transactions


def find_transfer_transaction(session: Session, transfer_uuid: UUID) -> Optional[Transaction]:
    statement = select(Transaction).where(Transaction.transfer_uuid == transfer_uuid)
    statement = cast(Select, statement)
    return session.exec(statement).first()


def create_transfer_transaction(
        session: Session, transfer_job_data: TransferJob
) -> Transaction:
    transfer_transaction = Transaction(
        transfer_uuid=UUID(transfer_job_data.transfer_uuid),
        bulk_request_uuid=UUID(transfer_job_data.bulk_request_uuid),
        counterparty_name=transfer_job_data.counterparty_name,
        counterparty_iban=transfer_job_data.counterparty_iban,
        counterparty_bic=transfer_job_data.counterparty_bic,
        amount_cents=-transfer_job_data.amount_cents,
        amount_currency=transfer_job_data.amount_currency,
        bank_account_id=transfer_job_data.bank_account_id,
        description=transfer_job_data.description
    )
    session.add(transfer_transaction)
    return transfer_transaction


#--- Bulk Requests


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


def select_bulk_request_for_update(session: Session, bulk_request_uuid: UUID):
    statement = select(BulkRequest).where(BulkRequest.request_uuid == bulk_request_uuid).with_for_update()
    statement = cast(Select, statement)
    bulk_request = session.exec(statement).first()
    return bulk_request
