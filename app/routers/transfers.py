import uuid
import logging

from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from uuid import UUID

from sqlmodel import Session

from app.amounts.converters import to_cents
from app.models import adapter
from app.models import db

MAX_NUMBER_OF_TRANSFERS_PER_BULK_REQUEST = 1000

logger = logging.getLogger(__name__)


router = APIRouter()  # https://fastapi.tiangolo.com/reference/apirouter


def get_session():
    with Session(db.engine) as session:
        yield session


def _bulk_error(bulk_id: UUID, reason: str, error_details: str, status_code: Optional[int] = 422) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=adapter.BulkTransferErrorResponse(
            bulk_id=str(bulk_id),
            message="Bulk transfer denied",
            error=adapter.ErrorDetails(reason=reason, details=error_details)
        ).model_dump()
    )

def reply_not_enough_funds_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=bulk_id,
        reason='insufficient-account-balance',  # todo ENUM
        error_details=error_details if error_details else "Not enough funds"
    )

def reply_amounts_should_be_positive_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=bulk_id,
        reason='negative-or-null-amounts',  # todo ENUM
        error_details=error_details if error_details else "All amounts should be strictly greater than zero"
    )


def reply_amounts_invalid_format_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=bulk_id,
        reason='invalid-amount',  # todo ENUM
        error_details=error_details if error_details else "All amounts should be numbers and not have more than 2 decimal places"
    )


def reply_unknown_account_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=bulk_id,
        status_code=404,
        reason='unknown-account',  # todo ENUM
        error_details=error_details if error_details else "Your account should be active"
    )


def reply_too_many_transfers_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=bulk_id,
        status_code=413,
        reason='too-many-transfers',  # todo ENUM
        error_details=error_details if error_details else f"Too many transfers requested (max={MAX_NUMBER_OF_TRANSFERS_PER_BULK_REQUEST})"
    )


@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    response_model=adapter.BulkTransferSuccessResponse,
    responses={  # https://fastapi.tiangolo.com/advanced/additional-responses/
        400: {"model": adapter.BulkTransferErrorResponse, "description": "Bad Request"},
        404: {"model": adapter.BulkTransferErrorResponse, "description": "Organization or Account not found"},
        # 422: {"description": "Payload does not match spec"},
        422: {"model": adapter.BulkTransferErrorResponse, "description": "Bulk transfer denied"},  # todo list of reasons (provide details in response) + handle mismatch patload vs Pydantic model
    }
)
def create_bulk_transfer(request: adapter.BulkTransferRequest, session: Session = Depends(get_session)):  # todo check async
    """
    /docs
    todo docstring
    """
    # todo
    bulk_id = uuid.uuid4()  # todo handle idempotency
    # checks: first additional validation (such as amounts are positive and can be converted to int), amounts are enough, etc.

    if len(request.credit_transfers) > MAX_NUMBER_OF_TRANSFERS_PER_BULK_REQUEST:
        logger.error(f"bulk_id={bulk_id} could not process request as too many transfers requested "
                     f"({len(request.credit_transfers)} > limit={MAX_NUMBER_OF_TRANSFERS_PER_BULK_REQUEST})")  # todo add logging context
        return reply_too_many_transfers_error(bulk_id=bulk_id)

    amounts_in_cents = []
    try:
        amounts_in_cents = [to_cents(amount_in_euros_str=credit_transfer.amount) for credit_transfer in
                            request.credit_transfers]
    except ValueError as e:
        logger.error(f"bulk_id={bulk_id} could not process request: {e}")  # todo add logging context
        return reply_amounts_invalid_format_error(bulk_id=bulk_id, error_details=str(e))

    all_transfer_amounts_are_valid = all(amount > 0 for amount in amounts_in_cents)
    if not all_transfer_amounts_are_valid:
        logger.error(f"bulk_id={bulk_id} could not process request as not all amounts are > 0: {amounts_in_cents}")  # todo add logging context
        return reply_amounts_should_be_positive_error(bulk_id=bulk_id)
        # raise HTTPException(status_code=422, detail="Bulk transfer denied")

    # with session.begin():
    # statement = select(db.BankAccount).where(
    #     db.BankAccount.bic == request.organization_bic.strip(),
    #     db.BankAccount.iban == request.organization_iban.strip()
    # )
    # statement = cast(Select, statement)
    # account = session.exec(statement).first()# v1: sync transfers
    with session.begin():
        account = db.find_account_for_update(session=session, bic=request.organization_bic, iban=request.organization_iban)
        if not account:
            logger.error(f"bulk_id={bulk_id} could not process request as account unknown")  # todo add logging context
            return reply_unknown_account_error(bulk_id=bulk_id)

        total_transfer_amounts = sum(amounts_in_cents)
        logger.error(f"++++ DEBUG bulk_id={bulk_id} total_transfer_amounts={total_transfer_amounts} | account balance={account.balance_cents} | ongoing transfers={account.ongoing_transfer_cents}")
        if total_transfer_amounts + account.ongoing_transfer_cents > account.balance_cents:
            logger.error(f"bulk_id={bulk_id} could not process request as account balance is insufficient for ongoing operations")  # todo add logging context
            return reply_not_enough_funds_error(bulk_id=bulk_id)


        # todo check UUIDs and skip
        # todo log bulk_request

        # Reserve funds
        # account.ongoing_transfer_cents += total_transfer_amounts
        # session.add(account)
        db.reserve_funds(session=session, account=account, total_transfer_amounts=total_transfer_amounts)
        for credit_transfer in request.credit_transfers:
            transaction = db.create_transfer_transaction(
                session=session, bank_account_id=account.id, credit_transfer=credit_transfer
            )
            logger.info(f"bulk_id={bulk_id} transfer_uuid={transaction.transfer_uuid} transaction recorded amount={transaction.amount_cents}")
        db.finalize_bulk_transfer(session=session, account=account, total_transfer_amounts=total_transfer_amounts)


    # return {"message": "Bulk transfer accepted", "bulk_id": str(request.bulk_id)}
    return {"message": "Bulk transfer accepted", "bulk_id": str(bulk_id)}
    # return JSONResponse(
    #     status_code=201,
    #     content=BulkTransferSuccessResponse(bulk_id=str(bulk_id), message="Bulk transfer accepted").model_dump()
    # )
