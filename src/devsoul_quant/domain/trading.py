"""Immutable provider-independent trade lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from devsoul_quant.domain.contracts import EnterContractIntent
from devsoul_quant.domain.replay import Outcome


class InvalidTradeTransition(ValueError):
    """Raised when a trade lifecycle transition is not legal."""


class TradeState(StrEnum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


def _require_non_blank(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string")


@dataclass(frozen=True, slots=True)
class Trade:
    """One immutable snapshot in a contract trade lifecycle."""

    trade_id: str
    intent: EnterContractIntent
    state: TradeState
    position_id: str | None = None
    outcome: Outcome | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.trade_id, "trade_id")

    @classmethod
    def pending(cls, *, trade_id: str, intent: EnterContractIntent) -> Trade:
        return cls(trade_id=trade_id, intent=intent, state=TradeState.PENDING)

    def open(self, *, position_id: str) -> Trade:
        if self.state is not TradeState.PENDING:
            raise InvalidTradeTransition(f"cannot open a trade in {self.state.value} state")
        _require_non_blank(position_id, "position_id")
        return replace(self, state=TradeState.OPEN, position_id=position_id)

    def close(self, outcome: Outcome) -> Trade:
        if self.state is not TradeState.OPEN:
            raise InvalidTradeTransition(f"cannot close a trade in {self.state.value} state")
        return replace(self, state=TradeState.CLOSED, outcome=outcome)


@dataclass(frozen=True, slots=True)
class Adjustment:
    """An append-only correction that references, rather than mutates, history."""

    adjustment_id: str
    original_event_id: str
    reason: str

    def __post_init__(self) -> None:
        _require_non_blank(self.adjustment_id, "adjustment_id")
        _require_non_blank(self.original_event_id, "original_event_id")
        _require_non_blank(self.reason, "reason")
