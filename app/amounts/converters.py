import decimal


def to_cents(amount_in_euros_str: str) -> int:
    try:
        amount_in_euros = decimal.Decimal(amount_in_euros_str)
    except Exception:
        raise ValueError(f"Invalid amount: {amount_in_euros_str}")
    rounded_amount_in_euros = amount_in_euros.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)
    if amount_in_euros != rounded_amount_in_euros:
        raise ValueError(f"More than 2 decimal places is not allowed: {amount_in_euros_str}")
    amount_in_cents = rounded_amount_in_euros * 100
    return int(amount_in_cents)
