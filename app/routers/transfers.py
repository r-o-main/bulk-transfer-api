from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from uuid import UUID
from sqlmodel import Session

from app.amounts.converters import to_cents
from app.models import adapter
from app.models import db
from app.models.db import get_session
from app.services import bulk_request_service
from app.utils.log_formatter import get_logger


MAX_NUMBER_OF_TRANSFERS_PER_BULK_REQUEST = 1000


logger = get_logger(__name__)


router = APIRouter()  # https://fastapi.tiangolo.com/reference/apirouter


@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    response_model=adapter.BulkTransferSuccessResponse,
    responses={
        400: {"model": adapter.BulkTransferErrorResponse, "description": "Bad Request"},
        404: {"model": adapter.BulkTransferErrorResponse, "description": "Organization or Account not found"},
        422: {"model": adapter.BulkTransferErrorResponse, "description": "Bulk transfer denied"},
    }
)
def create_bulk_transfer(request: adapter.BulkTransferRequest, session: Session = Depends(get_session)):
    """
    /docs
    todo docstring
    """
    if not _validate_request_id(request_id=request.request_id):
        return reply_invalid_request_id_error(bulk_id=request.request_id)

    bulk_id = UUID(request.request_id)
    with session.begin():
        already_processed_bulk_request = db.find_bulk_request(session=session, bulk_request_uuid=bulk_id)
        if already_processed_bulk_request:
            return reply_request_already_processed_error(bulk_id=bulk_id)

        if len(request.credit_transfers) > MAX_NUMBER_OF_TRANSFERS_PER_BULK_REQUEST:
            return reply_too_many_transfers_error(bulk_id=bulk_id)

        amounts_in_cents = []
        try:
            amounts_in_cents = [to_cents(amount_in_euros_str=credit_transfer.amount) for credit_transfer in
                                request.credit_transfers]
        except ValueError as e:
            logger.error(f"bulk_id={bulk_id} could not process request: {e}")
            return reply_amounts_invalid_format_error(bulk_id=bulk_id, error_details=str(e))

        all_transfer_amounts_are_valid = all(amount > 0 for amount in amounts_in_cents)
        if not all_transfer_amounts_are_valid:
            logger.error(f"bulk_id={bulk_id} could not process request as not all amounts are > 0: {amounts_in_cents}")
            return reply_amounts_should_be_positive_error(bulk_id=bulk_id)

        account = db.select_account_for_update(
            session=session, bic=request.organization_bic, iban=request.organization_iban
        )
        if not account:
            logger.error(f"bulk_id={bulk_id} could not process request as account unknown")
            return reply_unknown_account_error(bulk_id=bulk_id)

        total_transfer_amounts_cents = sum(amounts_in_cents)
        logger.info(f"bulk_id={bulk_id} total_transfer_amounts_cents={total_transfer_amounts_cents} "
                    f"| account balance={account.balance_cents} | ongoing transfers={account.ongoing_transfer_cents}")
        if total_transfer_amounts_cents + account.ongoing_transfer_cents > account.balance_cents:
            logger.error(f"bulk_id={bulk_id} could not process request as account balance is insufficient "
                         f"for ongoing operations")
            return reply_not_enough_funds_error(bulk_id=bulk_id)

        bulk_request_service.schedule_transfers(
            session=session,
            bulk_request_uuid=str(bulk_id),
            account=account,
            total_transfer_amounts_cents=total_transfer_amounts_cents,
            credit_transfers=request.credit_transfers
        )

    return {"message": "Bulk transfer accepted", "bulk_id": str(bulk_id)}


def _validate_request_id(request_id) -> bool:
    try:
        bulk_id = UUID(request_id)
        return str(bulk_id) == request_id.lower()
    except ValueError:
        return False


def _bulk_error(bulk_id: str, reason: str, error_details: str, status_code: Optional[int] = 422) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=adapter.BulkTransferErrorResponse(
            bulk_id=bulk_id,
            message="Bulk transfer denied",
            error=adapter.ErrorDetails(reason=reason, details=error_details)
        ).model_dump()
    )


def reply_not_enough_funds_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=str(bulk_id),
        reason='insufficient-account-balance',
        error_details=error_details if error_details else "Not enough funds"
    )


def reply_amounts_should_be_positive_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=str(bulk_id),
        reason='negative-or-null-amounts',
        error_details=error_details if error_details else "All amounts should be strictly greater than zero"
    )


def reply_amounts_invalid_format_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=str(bulk_id),
        reason='invalid-amount',
        error_details=error_details if error_details else "All amounts should be numbers and not have more than 2 decimal places"
    )


def reply_unknown_account_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    return _bulk_error(
        bulk_id=str(bulk_id),
        status_code=404,
        reason='unknown-account',
        error_details=error_details if error_details else "Your account should be active"
    )


def reply_too_many_transfers_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    cause = f"Too many transfers requested (max={MAX_NUMBER_OF_TRANSFERS_PER_BULK_REQUEST})"
    logger.error(f"bulk_id={bulk_id} could not process request: {cause}")
    return _bulk_error(
        bulk_id=str(bulk_id),
        status_code=413,
        reason='too-many-transfers',
        error_details=error_details if error_details else cause
    )


def reply_invalid_request_id_error(bulk_id: str, error_details: Optional[str] = None) -> JSONResponse:
    logger.error(f"Invalid bulk request uuid: {bulk_id}")
    return _bulk_error(
        bulk_id=bulk_id,
        reason='invalid-request-id',
        error_details=error_details if error_details else "Invalid bulk request uuid"
    )


def reply_request_already_processed_error(bulk_id: UUID, error_details: Optional[str] = None) -> JSONResponse:
    logger.error(f"bulk_id={bulk_id} Bulk request already processed")
    return _bulk_error(
        bulk_id=str(bulk_id),
        reason='already-processed',
        error_details=error_details if error_details else f"Request {bulk_id} already processed."
    )
