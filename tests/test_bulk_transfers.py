import json
import logging
import os

import pytest

from fastapi.testclient import TestClient
from app.main import app


logger = logging.getLogger()


client = TestClient(app)  # https://fastapi.tiangolo.com/reference/testclient/, https://fastapi.tiangolo.com/tutorial/testing/


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
    ('when missing mandatory request key (credit_transfers)', {
        "organization_bic": "VALID_BIC",
        "organization_iban": "VALID_IBAN",
    }),
    ('when missing mandatory credit transfer key (amount)', {
        "organization_bic": "VALID_BIC",
        "organization_iban": "VALID_IBAN",
        "credit_transfers": [
            {
                "currency": "EUR",
                "counterparty_name": "Bip Bip",
                "counterparty_bic": "CRLYFRPPTOU",
                "counterparty_iban": "EE383680981021245685",
                "description": "Wonderland/4410"
            }
        ]
    }),
    ('when amount is an int', {
        "organization_bic": "VALID_BIC",
        "organization_iban": "VALID_IBAN",
        "credit_transfers": [
            {
                "amount": 15,
                "currency": "EUR",
                "counterparty_name": "Bip Bip",
                "counterparty_bic": "CRLYFRPPTOU",
                "counterparty_iban": "EE383680981021245685",
                "description": "Wonderland/4410"
            }
        ]
    }),
    ('when additional request key', {
        "organization_bic": "VALID_BIC",
        "organization_iban": "VALID_IBAN",
        "credit_transfers": [],
        "additional_key": "whatever"
    }),
    ('when additional credit_transfers key', {
        "organization_bic": "VALID_BIC",
        "organization_iban": "VALID_IBAN",
        "credit_transfers": [
            {
                "amount": "15.2",
                "currency": "EUR",
                "counterparty_name": "Bip Bip",
                "counterparty_bic": "CRLYFRPPTOU",
                "counterparty_iban": "EE383680981021245685",
                "description": "Wonderland/4410",
                "additional_key": "whatever"
            }
        ],
    }),
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
    ('when amount to transfer < 0', {
        "organization_bic": "INVALID_BIC",
        "organization_iban": "INVALID_IBAN",
        "credit_transfers": [
            {
                "amount": "61238",
                "currency": "EUR",
                "counterparty_name": "Wile E Coyote",
                "counterparty_bic": "ZDRPLBQI",
                "counterparty_iban": "DE9935420810036209081725212",
                "description": "//TeslaMotors/Invoice/12"
            },
            {
                "amount": "-15",
                "currency": "EUR",
                "counterparty_name": "Bip Bip",
                "counterparty_bic": "CRLYFRPPTOU",
                "counterparty_iban": "EE383680981021245685",
                "description": "Wonderland/4410",
            }
        ],
    }),
    ('when amount to transfer == 0', {
        "organization_bic": "INVALID_BIC",
        "organization_iban": "INVALID_IBAN",
        "credit_transfers": [
            {
                "amount": "61238",
                "currency": "EUR",
                "counterparty_name": "Wile E Coyote",
                "counterparty_bic": "ZDRPLBQI",
                "counterparty_iban": "DE9935420810036209081725212",
                "description": "//TeslaMotors/Invoice/12"
            },
            {
                "amount": "0",
                "currency": "EUR",
                "counterparty_name": "Bip Bip",
                "counterparty_bic": "CRLYFRPPTOU",
                "counterparty_iban": "EE383680981021245685",
                "description": "Wonderland/4410",
            }
        ],
    }),
    ('when amount to transfer is null', {
        "organization_bic": "INVALID_BIC",
        "organization_iban": "INVALID_IBAN",
        "credit_transfers": [
            {
                "amount": None,
                "currency": "EUR",
                "counterparty_name": "Wile E Coyote",
                "counterparty_bic": "ZDRPLBQI",
                "counterparty_iban": "DE9935420810036209081725212",
                "description": "//TeslaMotors/Invoice/12"
            },
        ],
    }),
    ('when amount to transfer is empty', {
        "organization_bic": "INVALID_BIC",
        "organization_iban": "INVALID_IBAN",
        "credit_transfers": [
            {
                "amount": "",
                "currency": "EUR",
                "counterparty_name": "Wile E Coyote",
                "counterparty_bic": "ZDRPLBQI",
                "counterparty_iban": "DE9935420810036209081725212",
                "description": "//TeslaMotors/Invoice/12"
            },
        ],
    }),
    ('when amount to transfer has more than 2 decimal places', {
        "organization_bic": "VALID_BIC",
        "organization_iban": "VALID_IBAN",
        "credit_transfers": [
            {
                "amount": "13.2356",
                "currency": "EUR",
                "counterparty_name": "Wile E Coyote",
                "counterparty_bic": "ZDRPLBQI",
                "counterparty_iban": "DE9935420810036209081725212",
                "description": "//TeslaMotors/Invoice/12"
            },
        ],
    }),
    ('when amount to transfer is invalid', {
        "organization_bic": "VALID_BIC",
        "organization_iban": "VALID_IBAN",
        "credit_transfers": [
            {
                "amount": "aaaaa",
                "currency": "EUR",
                "counterparty_name": "Wile E Coyote",
                "counterparty_bic": "ZDRPLBQI",
                "counterparty_iban": "DE9935420810036209081725212",
                "description": "//TeslaMotors/Invoice/12"
            },
        ],
    }),
    ('when description is too short', {
        "organization_bic": "VALID_BIC",
        "organization_iban": "VALID_IBAN",
        "credit_transfers": [
            {
                "amount": "15",
                "currency": "EUR",
                "counterparty_name": "Wile E Coyote",
                "counterparty_bic": "ZDRPLBQI",
                "counterparty_iban": "DE9935420810036209081725212",
                "description": "toto"
            },
        ],
    }),
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
