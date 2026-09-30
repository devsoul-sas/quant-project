"""Precise provider-independent monetary values."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class InvalidMoney(ValueError):
    """Raised when a monetary value violates precision invariants."""


class CurrencyMismatch(ValueError):
    """Raised when arithmetic mixes currencies."""


@dataclass(frozen=True, slots=True)
class Money:
    """An immutable finite Decimal amount denominated in one ISO-style currency."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise InvalidMoney("amount must be a finite Decimal")
        if (
            not isinstance(self.currency, str)
            or len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isalpha()
            or not self.currency.isupper()
        ):
            raise InvalidMoney("currency must be a three-letter uppercase ASCII code")

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatch(f"cannot mix {self.currency} and {other.currency}")

    def __add__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)
