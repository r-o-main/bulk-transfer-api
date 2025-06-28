import json
import os

import pytest

from fastapi.testclient import TestClient
from app.main import app

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
        "organization_bic": "VALIDBIC",
        "organization_iban": "VALIDIBAN",
    }),
    ('when missing mandatory credit transfer key (amount)', {
        "organization_bic": "VALIDBIC",
        "organization_iban": "VALIDIBAN",
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
        "organization_bic": "VALIDBIC",
        "organization_iban": "VALIDIBAN",
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
        "organization_bic": "VALIDBIC",
        "organization_iban": "VALIDIBAN",
        "credit_transfers": [],
        "additional_key": "whatever"
    }),
    ('when additional credit_transfers key', {
        "organization_bic": "VALIDBIC",
        "organization_iban": "VALIDIBAN",
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
