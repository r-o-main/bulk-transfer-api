import pytest

from app.amounts.converters import to_cents


@pytest.mark.parametrize("amount_euros, expected_amount_cents", [
    ("10", 1000),
    ("10.0", 1000),
    ("10.00", 1000),
    ("10.05", 1005),
])
def test_to_cents__when_valid_amount_with_at_most_2_decimal_places__should_convert_to_cents_without_money_loss(
        amount_euros: str, expected_amount_cents: int
):
    assert to_cents(amount_in_euros_str=amount_euros) == expected_amount_cents

@pytest.mark.parametrize("assert_message, amount_euros", [
    ("when invalid format", "eaaa"),
    ("when more than 2 decimal places", "10.123"),
])
def test_to_cents__when_invalid_amount__should_raise_value_error(
        assert_message: str, amount_euros: str
):
    with pytest.raises(ValueError):
        to_cents(amount_in_euros_str=amount_euros)
