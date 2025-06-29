import json
import os
from typing import Optional, List, Dict


def stub_credit_transfer(
        amount_in_euros: Optional[str | int] = None,
        description: Optional[str] = None,
        key_to_remove: Optional[str] = None,
        key_to_add: Optional[str] = None,
):
    stubbed_credit_transfer = {
        "amount": amount_in_euros if amount_in_euros is not None else "14.5",
        "currency": "EUR",
        "counterparty_name": "Bip Bip",
        "counterparty_bic": "CRLYFRPPTOU",
        "counterparty_iban": "EE383680981021245685",
        "description": description if description else "Wonderland/4410"
    }
    if key_to_remove is not None:
        del stubbed_credit_transfer[key_to_remove]
    if key_to_add is not None:
        stubbed_credit_transfer[key_to_add] = "whatever"
    return stubbed_credit_transfer


def stub_bulk_transfer_payload(
        credit_transfers: Optional[List[Dict]] = None,
        key_to_remove: Optional[str] = None,
        key_to_add: Optional[str] = None,
        verbose: bool = True
):
    stubbed_bulk_transfer_payload = {
        "organization_bic": "OIVUSCLQXXX",
        "organization_iban": "FR10474608000002006107XXXXX",
        "credit_transfers": credit_transfers if credit_transfers is not None else []
    }
    if key_to_remove is not None:
        del stubbed_bulk_transfer_payload[key_to_remove]
    if key_to_add is not None:
        stubbed_bulk_transfer_payload[key_to_add] = "whatever"
    if verbose:
        print(f'payload={stubbed_bulk_transfer_payload}')
    return stubbed_bulk_transfer_payload


def load_sample_payload(resource_name):
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), f"resources/{resource_name}")) as resource:
        payload = json.load(resource)
        print(f"payload={payload}")
        return payload
