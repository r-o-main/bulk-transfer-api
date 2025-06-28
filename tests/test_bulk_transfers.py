import pytest

from fastapi.testclient import TestClient
from mockito import when, KWARGS

from app.main import app
from app.models import db

from tests.faker import stub_credit_transfer, stub_bulk_transfer_payload, load_sample_payload


client = TestClient(app)  # https://fastapi.tiangolo.com/reference/testclient/, https://fastapi.tiangolo.com/tutorial/testing/


@pytest.fixture(scope="module", autouse=True)
def setup_bank_account(request):
    when(db).find_account(**KWARGS).thenReturn(
        db.BankAccount(id=1, iban="123", bic="456", organization_name="Test Org")
    )

@pytest.fixture
def unknown_bank_account(request):
    when(db).find_account(**KWARGS).thenReturn(None)


@pytest.mark.parametrize("sample_file", ["sample_valid_payload_1.json", "sample_valid_payload_2.json"])
def test_transfers_bulk__when_valid_payload__should_return_201(sample_file):
    # when(db).find_account(**KWARGS).thenReturn(
    #     db.BankAccount(id=1, iban="123", bic="456", organization_name="Test Org")
    # )
    sample_payload = load_sample_payload(resource_name=sample_file)
    response = client.post(url="/transfers/bulk", json=sample_payload)

    assert response.status_code == 201
    response_dict = response.json()
    assert "bulk_id" in response_dict


@pytest.mark.parametrize("assert_message, payload", [
    (
            'when missing mandatory request key (credit_transfers)',
            stub_bulk_transfer_payload(key_to_remove="credit_transfers")
    ),
    (
            'when missing mandatory credit transfer key (amount)',
            stub_bulk_transfer_payload(credit_transfers=[stub_credit_transfer(key_to_remove="amount")])
    ),
    (
            'when amount is an int',
            stub_bulk_transfer_payload(credit_transfers=[stub_credit_transfer(amount=15)])
    ),
    (
            'when additional request key',
            stub_bulk_transfer_payload(key_to_add="unexpected_key")
    ),
    (
            'when additional credit_transfers key',
            stub_bulk_transfer_payload(
                credit_transfers=[stub_credit_transfer(key_to_add="unexpected_key")]
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
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount="61238"),
                    stub_credit_transfer(amount="-15"),
                ]
            )
    ),
    (
            'when at least one amount to transfer == 0',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount="0"),
                    stub_credit_transfer(amount="199.99"),
                ]
            )
    ),
    (
            'when at least one amount to transfer is null',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount="199.99"),
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
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount=""),
                    stub_credit_transfer(amount="199.99"),
                ]
            )
    ),
    (
            'when at least one amount to transfer has more than 2 decimal places',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount="12.56"),
                    stub_credit_transfer(amount="199.999"),
                ]
            )
    ),
    (
            'when at least one amount to transfer is invalid',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount="12.89"),
                    stub_credit_transfer(amount="aaaa"),
                ]
            )
    ),
    (
            'when description is less than 10 characters',
            stub_bulk_transfer_payload(
                credit_transfers=[stub_credit_transfer(description="too short")]
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


def test_transfers_bulk__when_unknown_organization__should_return_404(unknown_bank_account):
    response = client.post(url="/transfers/bulk", json=stub_bulk_transfer_payload())
    print(f"++++ response={response.json()}")
    assert response.status_code == 404


# todo test rounding strategy: "10.05"
