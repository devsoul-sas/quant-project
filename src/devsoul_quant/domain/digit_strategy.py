"""Causal digit features for ephemeral Deriv paper research."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from itertools import pairwise

from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
    NoTradeIntent,
)
from devsoul_quant.domain.replay import Tick


class InvalidDigitTick(ValueError):
    """Raised when a tick cannot identify its displayed last digit."""


class InvalidDigitPolicy(ValueError):
    """Raised when digit economics or evidence thresholds cannot fail safely."""


@dataclass(frozen=True, slots=True)
class DigitEconomics:
    """Contemporary proposal economics for one digit contract."""

    contract_type: ContractType
    ask_price: Decimal
    payout: Decimal

    def __post_init__(self) -> None:
        if self.contract_type not in (ContractType.DIGITEVEN, ContractType.DIGITODD):
            raise InvalidDigitPolicy("digit economics requires an Even/Odd contract")
        for name, value in (("ask_price", self.ask_price), ("payout", self.payout)):
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise InvalidDigitPolicy(f"{name} must be a positive finite Decimal")

    @classmethod
    def even(cls, *, ask_price: Decimal, payout: Decimal) -> "DigitEconomics":
        return cls(ContractType.DIGITEVEN, ask_price, payout)

    @classmethod
    def odd(cls, *, ask_price: Decimal, payout: Decimal) -> "DigitEconomics":
        return cls(ContractType.DIGITODD, ask_price, payout)


@dataclass(frozen=True, slots=True)
class DigitDecisionPolicy:
    """Frozen evidence threshold for a causal parity decision."""

    min_samples: int
    z_score: Decimal
    min_edge_probability: Decimal

    def __post_init__(self) -> None:
        if type(self.min_samples) is not int or self.min_samples < 1:
            raise InvalidDigitPolicy("min_samples must be a positive integer")
        if (
            not isinstance(self.z_score, Decimal)
            or not self.z_score.is_finite()
            or self.z_score <= 0
        ):
            raise InvalidDigitPolicy("z_score must be a positive finite Decimal")
        edge = self.min_edge_probability
        if not isinstance(edge, Decimal) or not edge.is_finite() or edge < 0:
            raise InvalidDigitPolicy("min_edge_probability must be a non-negative finite Decimal")


def last_digit(tick: Tick) -> int:
    """Return the last displayed digit using the provider-declared precision."""
    if tick.pip_size is None:
        raise InvalidDigitTick("digit analysis requires provider pip_size")
    displayed_quote = format(tick.quote, f".{tick.pip_size}f")
    return int(displayed_quote[-1])


def digit_parity_decision(
    *,
    history: Sequence[Tick],
    even_economics: DigitEconomics,
    odd_economics: DigitEconomics,
    policy: DigitDecisionPolicy,
    amount_requested: Decimal,
    symbol: str,
) -> EnterContractIntent | NoTradeIntent:
    """Enter only when a Wilson lower bound clears observed break-even."""
    if len(history) < policy.min_samples:
        return NoTradeIntent(
            action=ContractAction.NO_TRADE,
            strategy_reason=(
                f"insufficient sample: observed={len(history)} required={policy.min_samples}"
            ),
        )
    if any(current.epoch <= previous.epoch for previous, current in pairwise(history)):
        raise InvalidDigitTick("history must be strictly increasing")

    even_count = sum(last_digit(tick) % 2 == 0 for tick in history)
    sample_count = len(history)
    candidates = (
        (even_economics, even_count),
        (odd_economics, sample_count - even_count),
    )
    scored = tuple(
        (
            _wilson_lower_bound(successes, sample_count, policy.z_score)
            - economics.ask_price / economics.payout,
            economics,
        )
        for economics, successes in candidates
    )
    edge, selected = max(scored, key=lambda candidate: candidate[0])
    if edge <= policy.min_edge_probability:
        return NoTradeIntent(
            action=ContractAction.NO_TRADE,
            strategy_reason="conservative parity edge does not clear observed break-even",
        )
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol=symbol,
        contract_type=selected.contract_type,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=amount_requested,
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="conservative parity edge clears observed break-even",
    )


def _wilson_lower_bound(successes: int, sample_count: int, z_score: Decimal) -> Decimal:
    context = Context(prec=28, rounding=ROUND_HALF_EVEN)
    with localcontext(context):
        count = Decimal(sample_count)
        probability = Decimal(successes) / count
        z_squared = z_score * z_score
        denominator = Decimal(1) + z_squared / count
        centre = probability + z_squared / (Decimal(2) * count)
        variance = (
            probability * (Decimal(1) - probability) + z_squared / (Decimal(4) * count)
        ) / count
        margin = z_score * variance.sqrt()
        return (centre - margin) / denominator
