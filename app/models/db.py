# https://fastapi.tiangolo.com/tutorial/sql-databases/
import datetime
from enum import Enum
from typing import Optional, cast
from uuid import UUID, uuid4

from sqlalchemy import Select
from sqlmodel import create_engine, SQLModel, Field, Column, DateTime, select, Session

DATABASE_PATH = "./qonto_accounts.sqlite"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class BankAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    organization_name: str = Field(nullable=False)
    iban: str = Field(nullable=False)
    bic: str = Field(nullable=False)
    balance_cents: int = Field(default=0, nullable=False)


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transfer_uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    counterparty_name: str = Field(nullable=False)
    counterparty_iban: str = Field(nullable=False)
    counterparty_bic: str = Field(nullable=False)
    amount_cents: int = Field(nullable=False)
    amount_currency: str = Field(nullable=False)
    bank_account_id: int = Field(nullable=False)
    description: str = Field(nullable=False)


class RequestStatus(str, Enum):
    """
    Enum for bulk request and individual transfer requests status values
    """
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BulkRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    request_uuid: UUID = Field(default_factory=uuid4, index=True, unique=True)
    bank_account_id: int = Field(nullable=False)
    status: RequestStatus = Field(default=RequestStatus.PENDING, nullable=False)
    total_amount_cents: int = Field(default=0, nullable=False)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP")
    )
    completed_at: Optional[datetime.datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )


def find_account(session: Session, bic: str, iban: str) -> Optional[BankAccount]:
    statement = select(BankAccount).where(
        BankAccount.bic == bic.strip(),
        BankAccount.iban == iban.strip()
    )
    statement = cast(Select, statement)
    account = session.exec(statement).first()
    return account