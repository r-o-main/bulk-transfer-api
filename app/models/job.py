from pydantic import BaseModel

from app.models.adapter import CreditTransfer


class TransferJob(BaseModel):
    transfer_uuid: str
    bulk_request_uuid: str
    bank_account_id: int
    counterparty_name: str
    counterparty_iban: str
    counterparty_bic: str
    amount_cents: int
    amount_currency: str
    description: str


def build_transfer_job(
        bulk_request_uuid: str, transfer_uuid: str, bank_account_id: int, credit_transfer: CreditTransfer
) -> TransferJob:
    return TransferJob(
        transfer_uuid=transfer_uuid,
        bulk_request_uuid=bulk_request_uuid,
        bank_account_id=bank_account_id,
        counterparty_name=credit_transfer.counterparty_name,
        counterparty_iban=credit_transfer.counterparty_iban,
        counterparty_bic=credit_transfer.counterparty_bic,
        amount_cents=credit_transfer.amount_to_cents(),
        amount_currency=credit_transfer.currency,
        description=credit_transfer.description
    )


class BulkJob(BaseModel):
    bulk_request_uuid: str
    bank_account_id: int
    single_transferred_amount_cents: int
    success: bool
