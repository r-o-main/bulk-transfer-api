import json
import logging
import os
from typing import Optional, List, Dict

import pytest

from fastapi.testclient import TestClient
from app.main import app


logger = logging.getLogger()


client = TestClient(app)  # https://fastapi.tiangolo.com/reference/testclient/, https://fastapi.tiangolo.com/tutorial/testing/


def _stub_credit_transfer(
        amount: Optional[str|int] = None,
        description: Optional[str] = None,
        key_to_remove: Optional[str] = None,
        key_to_add: Optional[str] = None,
):
    stubbed_credit_transfer = {
        "amount": amount if amount is not None else "14.5",
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


def _stub_bulk_transfer_payload(
        credit_transfers: Optional[List[Dict]] = None,
        key_to_remove: Optional[str] = None,
        key_to_add: Optional[str] = None,
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
    print(f'payload={stubbed_bulk_transfer_payload}')
    return stubbed_bulk_transfer_payload


def _load_resource(resource_name):
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), f"resources/{resource_name}")) as resource:
        payload = json.load(resource)
        print(f"payload={payload}")
        return payload


@pytest.mark.parametrize("sample_file", ["sample_valid_payload_1.json", "sample_valid_payload_2.json"])
def test_transfers_bulk__when_valid_payload__should_return_201(sample_file):
    sample_data = _load_resource(resource_name=sample_file)
    response = client.post(url="/transfers/bulk", json=sample_data)
    assert response.status_code == 201
    response_dict = response.json()
    assert "bulk_id" in response_dict


@pytest.mark.parametrize("assert_message, payload", [
    (
            'when missing mandatory request key (credit_transfers)',
            _stub_bulk_transfer_payload(key_to_remove="credit_transfers")
    ),
    (
            'when missing mandatory credit transfer key (amount)',
            _stub_bulk_transfer_payload(credit_transfers=[_stub_credit_transfer(key_to_remove="amount")])
    ),
    (
            'when amount is an int',
            _stub_bulk_transfer_payload(credit_transfers=[_stub_credit_transfer(amount=15)])
    ),
    (
            'when additional request key',
            _stub_bulk_transfer_payload(key_to_add="unexpected_key")
    ),
    (
            'when additional credit_transfers key',
            _stub_bulk_transfer_payload(
                credit_transfers=[_stub_credit_transfer(key_to_add="unexpected_key")]
            )
    ),
])
def test_transfers_bulk__when_invalid_payload_model__should_return_422(assert_message, payload):
    response = client.post(url="/transfers/bulk", json=payload)
    assert response.status_code == 422, f"{assert_message}: {response.json()}"


@pytest.mark.parametrize("assert_message, payload", [
    # ('when organization is not known', {
    #     "organization_bic": "UNKNOWN_BIC",
    #     "organization_iban": "VALID_IBAN",
    #     "credit_transfers": [],
    # }),
    # ('when customer bank account is not known', {
    #     "organization_bic": "VALID_BIC",
    #     "organization_iban": "UNKNOWN_IBAN",
    #     "credit_transfers": [],
    # }),
    # ('when customer bank and account are not known', {
    #     "organization_bic": "UNKNOWN_BIC",
    #     "organization_iban": "UNKNOWN_IBAN",
    #     "credit_transfers": [],
    # }),
    # ('when organization BIC is not valid', {
    #     "organization_bic": "INVALID_BIC",
    #     "organization_iban": "VALID_IBAN",
    #     "credit_transfers": [],
    # }),
    # ('when organization IBAN is not valid', {
    #     "organization_bic": "VALID_BIC",
    #     "organization_iban": "INVALID_IBAN",
    #     "credit_transfers": [],
    # }),
    # ('when organization IBAN and BIC are not valid', {
    #     "organization_bic": "INVALID_BIC",
    #     "organization_iban": "INVALID_IBAN",
    #     "credit_transfers": [],
    # }),
    (
            'when at least one amount to transfer < 0',
            _stub_bulk_transfer_payload(
                credit_transfers=[
                    _stub_credit_transfer(amount="61238"),
                    _stub_credit_transfer(amount="-15"),
                ]
            )
    ),
    (
            'when at least one amount to transfer == 0',
            _stub_bulk_transfer_payload(
                credit_transfers=[
                    _stub_credit_transfer(amount="0"),
                    _stub_credit_transfer(amount="199.99"),
                ]
            )
    ),
    (
            'when at least one amount to transfer is null',
            _stub_bulk_transfer_payload(
                credit_transfers=[
                    _stub_credit_transfer(amount="199.99"),
                    {
                        "amount": None,
                        "currency": "EUR",
                        "counterparty_name": "Wile E Coyote",
                        "counterparty_bic": "ZDRPLBQI",
                        "counterparty_iban": "DE9935420810036209081725212",
                        "description": "//TeslaMotors/Invoice/12"
                    }
                ]
            )
    ),
    (
            'when at least one amount to transfer is empty',
            _stub_bulk_transfer_payload(
                credit_transfers=[
                    _stub_credit_transfer(amount=""),
                    _stub_credit_transfer(amount="199.99"),
                ]
            )
    ),
    (
            'when at least one amount to transfer has more than 2 decimal places',
            _stub_bulk_transfer_payload(
                credit_transfers=[
                    _stub_credit_transfer(amount="12.56"),
                    _stub_credit_transfer(amount="199.999"),
                ]
            )
    ),
    (
            'when at least one amount to transfer is invalid',
            _stub_bulk_transfer_payload(
                credit_transfers=[
                    _stub_credit_transfer(amount="12.89"),
                    _stub_credit_transfer(amount="aaaa"),
                ]
            )
    ),
    (
            'when description is less than 10 characters',
            _stub_bulk_transfer_payload(
                credit_transfers=[_stub_credit_transfer(description="too short")]
            )
    ),
    # ('when total amount to transfer is higher than actual account balance', {
    #     "organization_bic": "INVALID_BIC",
    #     "organization_iban": "INVALID_IBAN",
    #     "credit_transfers": [
    #         {
    #             "amount": "61238",
    #             "currency": "EUR",
    #             "counterparty_name": "Wile E Coyote",
    #             "counterparty_bic": "ZDRPLBQI",
    #             "counterparty_iban": "DE9935420810036209081725212",
    #             "description": "//TeslaMotors/Invoice/12"
    #         },
    #     ],
    # }),
    # ('when total amount to transfer is higher than actual account balance', {
    #     "organization_bic": "INVALID_BIC",
    #     "organization_iban": "INVALID_IBAN",
    #     "credit_transfers": [
    #         {
    #             "amount": "61238",
    #             "currency": "EUR",
    #             "counterparty_name": "Wile E Coyote",
    #             "counterparty_bic": "ZDRPLBQI",
    #             "counterparty_iban": "DE9935420810036209081725212",
    #             "description": "//TeslaMotors/Invoice/12"
    #         },
    #         {
    #             "amount": "999",
    #             "currency": "EUR",
    #             "counterparty_name": "Bugs Bunny",
    #             "counterparty_bic": "RNJZNTMC",
    #             "counterparty_iban": "FR0010009380540930414023042",
    #             "description": "2020 09 24/2020 09 25/GoldenCarrot/"
    #         }
    #     ]
    # }),
])
def test_transfers_bulk__should_return_422(assert_message, payload):
    response = client.post(url="/transfers/bulk", json=payload)
    print(f"++++ response={response.json()}")
    assert response.status_code == 422, f"{assert_message}: {response.json()}"

# todo test rounding strategy: "10.05"
