import uuid

import mockito
import pytest

from fastapi.testclient import TestClient
from mockito import when, KWARGS, mock, ANY

from app.main import app
from app.models import db
from app.routers.transfers import MAX_NUMBER_OF_TRANSFERS_PER_BULK_REQUEST

from tests.faker import stub_credit_transfer, stub_bulk_transfer_payload, load_sample_payload


client = TestClient(app)  # https://fastapi.tiangolo.com/reference/testclient/, https://fastapi.tiangolo.com/tutorial/testing/


# @pytest.fixture(scope="module", autouse=True)
# def setup(request):
#     when(db).find_account_for_update(**KWARGS).thenReturn(
#         db.BankAccount(id=1, iban="123", bic="456", organization_name="Test Org",
#                        balance_cents=90000000, ongoing_transfer_cents=0)
#     )
#     when(db).find_bulk_request(**KWARGS)

@pytest.fixture
def when_account_valid(request):
    when(db).find_account_for_update(**KWARGS).thenReturn(
        db.BankAccount(id=1, iban="123", bic="456", organization_name="Test Org",
                       balance_cents=90000000, ongoing_transfer_cents=0)
    )

@pytest.fixture
def when_bulk_request_not_already_processed(request):
    when(db).find_bulk_request(**KWARGS).thenReturn(None)


@pytest.fixture(autouse=True)
def unstub_between_tests():
    yield
    mockito.unstub()


@pytest.fixture
def when_ongoing_transfer_cents(request):
    when(db).find_account_for_update(**KWARGS).thenReturn(
        db.BankAccount(id=1, iban="123", bic="456", organization_name="Test Org",
                       balance_cents=599900, ongoing_transfer_cents=399900)
    )

@pytest.fixture
def when_unknown_bank_account(request):
    when(db).find_account_for_update(**KWARGS).thenReturn(None)


@pytest.fixture
def when_process_request_successfully(request):
    # when(db).find_bulk_request(**KWARGS).thenReturn(None)
    when(db).reserve_funds(**KWARGS)
    when(db).create_bulk_request(**KWARGS).thenReturn(mock({'request_uuid': uuid.uuid4()}))
    when(db).create_transfer_transaction(**KWARGS).thenReturn(mock({
        "id": 1,
        "transfer_uuid": uuid.uuid4(),
        "status": db.RequestStatus.PENDING
    })
    )
    when(db).finalize_bulk_transfer(**KWARGS)


# @pytest.fixture(scope="module", autouse=True)
# def fake_session():
#     return mock()


# @pytest.fixture
# def fake_credit_transfers():
#     return [stub_credit_transfer()]


@pytest.mark.parametrize("sample_file", ["sample_valid_payload_1.json", "sample_valid_payload_2.json"])
def test_transfers_bulk__when_valid_payload__should_return_201(
        when_account_valid, when_bulk_request_not_already_processed, when_process_request_successfully,
        sample_file
):
    # when(db).find_account(**KWARGS).thenReturn(
    #     db.BankAccount(id=1, iban="123", bic="456", organization_name="Test Org")
    # )
    # when(db).reserve_funds(**KWARGS)
    # when(db).create_bulk_request(**KWARGS)
    # when(db).create_transfer_transaction(**KWARGS).thenReturn(mock({
    #     "id": 1,
    #     "transfer_uuid": uuid.uuid4(),
    #     "status": db.RequestStatus.PENDING
    # })
    # )
    # when(db).finalize_bulk_transfer(**KWARGS)

    sample_payload = load_sample_payload(resource_name=sample_file)
    response = client.post(url="/transfers/bulk", json=sample_payload)

    assert response.status_code == 201
    response_dict = response.json()
    assert "bulk_id" in response_dict

    # todo verify


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
            stub_bulk_transfer_payload(credit_transfers=[stub_credit_transfer(amount_in_euros=15)])
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
    (
            'when credit_transfers is not a list',
            stub_bulk_transfer_payload(credit_transfers=stub_credit_transfer())
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
                    stub_credit_transfer(amount_in_euros="61238"),
                    stub_credit_transfer(amount_in_euros="-15"),
                ]
            )
    ),
    (
            'when at least one amount to transfer == 0',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount_in_euros="0"),
                    stub_credit_transfer(amount_in_euros="199.99"),
                ]
            )
    ),
    (
            'when at least one amount to transfer is null',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount_in_euros="199.99"),
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
                    stub_credit_transfer(amount_in_euros=""),
                    stub_credit_transfer(amount_in_euros="199.99"),
                ]
            )
    ),
    (
            'when at least one amount to transfer has more than 2 decimal places',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount_in_euros="12.56"),
                    stub_credit_transfer(amount_in_euros="199.999"),
                ]
            )
    ),
    (
            'when at least one amount to transfer is invalid',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount_in_euros="12.89"),
                    stub_credit_transfer(amount_in_euros="aaaa"),
                ]
            )
    ),
    (
            'when description is less than 10 characters',
            stub_bulk_transfer_payload(
                credit_transfers=[stub_credit_transfer(description="too short")]
            )
    ),
    (
            'when total amount to transfer is higher than actual account balance (single transfer)',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount_in_euros="900000.01"),
                ]
            )
    ),
    (
            'when total amount to transfer is higher than actual account balance',
            stub_bulk_transfer_payload(
                credit_transfers=[
                    stub_credit_transfer(amount_in_euros="899005.25"),
                    stub_credit_transfer(amount_in_euros="999.1"),
                ]
            )
    ),
])
def test_transfers_bulk__should_return_422(
        when_account_valid, when_bulk_request_not_already_processed,
        assert_message, payload
):
    response = client.post(url="/transfers/bulk", json=payload)
    print(f"response={response.json()}")
    assert response.status_code == 422, f"{assert_message}: {response.json()}"


def test_transfers_bulk__when_ongoing_transfers_and_balance_not_enough__should_return_422(
        when_account_valid, when_bulk_request_not_already_processed, when_ongoing_transfer_cents
):
    response = client.post(url="/transfers/bulk", json=stub_bulk_transfer_payload(
        credit_transfers=[stub_credit_transfer(amount_in_euros="3999")]
    ))
    print(f"response={response.json()}")
    assert response.status_code == 422, f"{response.json()}"


@pytest.mark.parametrize("assert_message, invalid_request_id", [
    ('when not a uuid', 'not-a-uuid'),
    ('when too short', '8348f0e-cf70-4a32-8dce-d6c6467ca590'),
])
def test_transfers_bulk__when_invalid_request_uuid__should_return_422(
        when_account_valid, when_bulk_request_not_already_processed,
        assert_message, invalid_request_id
):
    payload = stub_bulk_transfer_payload()
    payload["request_id"] = invalid_request_id
    response = client.post(url="/transfers/bulk", json=payload)
    print(f"response={response.json()}")
    assert response.status_code == 422, f"{assert_message}: {response.json()}"


def test_transfers_bulk__when_already_processed__should_return_422(
        when_account_valid, when_bulk_request_not_already_processed, when_process_request_successfully
):
    bulk_request_id = str(uuid.uuid4())
    payload = stub_bulk_transfer_payload()
    payload["request_id"] = bulk_request_id
    # when(db).find_bulk_request(**KWARGS).thenReturn(None)
    # when(db).reserve_funds(**KWARGS)
    # when(db).create_bulk_request(**KWARGS)
    # when(db).create_transfer_transaction(**KWARGS).thenReturn(mock({
    #     "id": 1,
    #     "transfer_uuid": uuid.uuid4(),
    #     "status": db.RequestStatus.PENDING
    # })
    # )
    # when(db).finalize_bulk_transfer(**KWARGS)
    response = client.post(url="/transfers/bulk", json=payload)
    assert response.status_code == 201

    when(db).find_bulk_request(**KWARGS).thenReturn(mock())
    response = client.post(url="/transfers/bulk", json=payload)
    print(f"response={response.json()}")
    assert response.status_code == 422


def test_transfers_bulk__when_too_many_transfers__should_return_413(
        when_account_valid, when_bulk_request_not_already_processed
):
    response = client.post(url="/transfers/bulk", json=stub_bulk_transfer_payload(
        credit_transfers=[stub_credit_transfer()] * (MAX_NUMBER_OF_TRANSFERS_PER_BULK_REQUEST + 1), verbose=False
    ))
    print(f"response={response.json()}")
    assert response.status_code == 413


def test_transfers_bulk__when_unknown_organization__should_return_404(
        when_unknown_bank_account, when_bulk_request_not_already_processed
):
# def test_transfers_bulk__when_unknown_organization__should_return_404():
    # when(db).find_account_for_update(**KWARGS).thenReturn(None)
    # when(db).find_bulk_request(**KWARGS).thenReturn(None)
    response = client.post(url="/transfers/bulk", json=stub_bulk_transfer_payload())
    print(f"response={response.json()}")
    assert response.status_code == 404
