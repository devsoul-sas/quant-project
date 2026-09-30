from decimal import Decimal

import pytest

from devsoul_quant.domain.money import CurrencyMismatch, InvalidMoney, Money


def test_money_preserves_decimal_precision_and_currency() -> None:
    money = Money(amount=Decimal("1.2300"), currency="USD")

    assert money.amount == Decimal("1.2300")
    assert money.amount.as_tuple().exponent == -4
    assert money.currency == "USD"


@pytest.mark.parametrize("amount", [0.1, Decimal("NaN"), Decimal("Infinity")])
def test_money_rejects_non_decimal_or_non_finite_amounts(amount: object) -> None:
    with pytest.raises(InvalidMoney):
        Money(amount=amount, currency="USD")  # type: ignore[arg-type]


@pytest.mark.parametrize("currency", ["usd", "US", "USDX", "   "])
def test_money_rejects_invalid_currency_codes(currency: str) -> None:
    with pytest.raises(InvalidMoney):
        Money(amount=Decimal("1.00"), currency=currency)


def test_money_addition_and_pnl_require_the_same_currency() -> None:
    stake = Money(amount=Decimal("1.00"), currency="USD")
    payout = Money(amount=Decimal("1.75"), currency="USD")

    assert payout - stake == Money(amount=Decimal("0.75"), currency="USD")
    assert stake + Money(amount=Decimal("0.25"), currency="USD") == Money(
        amount=Decimal("1.25"), currency="USD"
    )

    with pytest.raises(CurrencyMismatch):
        _ = stake + Money(amount=Decimal("1.00"), currency="EUR")
