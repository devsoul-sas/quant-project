"""Execution-friction model: directional outcomes net of transaction cost."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from devsoul_quant.domain.contracts import ContractType
from devsoul_quant.domain.replay import Outcome


class InvalidCostModel(ValueError):
    """Raised when an execution-cost model violates invariants."""


@dataclass(frozen=True, slots=True)
class ExecutionCostModel:
    """Relative round-trip friction charged on every entered trade.

    A mid-point fixing has no executable bid/ask, so a directional move must
    clear a spread before its outcome is economically meaningful. The cost is a
    non-negative relative fraction of the entry quote (e.g. 0.0001 ~ 1 pip).
    """

    spread_fraction: Decimal

    def __post_init__(self) -> None:
        _require_spread(self.spread_fraction)


def _require_spread(spread_fraction: Decimal) -> None:
    if (
        not isinstance(spread_fraction, Decimal)
        or not spread_fraction.is_finite()
        or spread_fraction < 0
    ):
        raise InvalidCostModel("spread_fraction must be a non-negative finite Decimal")


def direction_clears_spread(
    *,
    entry: Decimal,
    exit: Decimal,
    contract_type: ContractType,
    spread_fraction: Decimal,
) -> bool:
    """Whether a directional move exceeds the execution friction."""
    _require_spread(spread_fraction)
    if contract_type is ContractType.CALL:
        return exit > entry * (Decimal(1) + spread_fraction)
    if contract_type is ContractType.PUT:
        return exit < entry * (Decimal(1) - spread_fraction)
    raise InvalidCostModel("contract_type must be CALL or PUT")


def net_outcome(
    *,
    entry: Decimal,
    exit: Decimal,
    contract_type: ContractType,
    spread_fraction: Decimal,
) -> Outcome:
    """Reclassify a directional outcome net of the modeled spread."""
    if direction_clears_spread(
        entry=entry,
        exit=exit,
        contract_type=contract_type,
        spread_fraction=spread_fraction,
    ):
        return Outcome.WIN
    return Outcome.LOSS
