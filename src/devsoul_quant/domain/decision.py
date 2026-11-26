"""Rich, auditable entry decisions over measured statistical evidence.

The decision engine separates the scientific decision — direction, estimated
probability, uncertainty, expected value, risk margin and reason — from
execution intents. It can always decline to trade; ``NO_TRADE`` is the
fail-closed default, and no path fabricates a real-money authorization.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise

from devsoul_quant.domain.contracts import ContractType
from devsoul_quant.domain.digit_strategy import (
    DigitDecisionPolicy,
    DigitEconomics,
    last_digit,
    wilson_lower_bound,
    wilson_upper_bound,
)
from devsoul_quant.domain.range_regime import (
    InvalidRangeRegime,
    RangePolicy,
    analyze_range,
)
from devsoul_quant.domain.replay import Tick


class InvalidDecision(ValueError):
    """Raised when decision inputs cannot produce a safe, honest decision."""


class DecisionAction(StrEnum):
    """Directional entry actions a decision may select."""

    NO_TRADE = "NO_TRADE"
    EVEN = "EVEN"
    ODD = "ODD"
    MULTUP = "MULTUP"
    MULTDOWN = "MULTDOWN"


_ENTRY_ACTIONS = (
    DecisionAction.EVEN,
    DecisionAction.ODD,
    DecisionAction.MULTUP,
    DecisionAction.MULTDOWN,
)


def _finite_probability(value: Decimal | None, field: str) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal) or not value.is_finite():
        raise InvalidDecision(f"{field} must be a finite Decimal or None")
    if not (Decimal(0) <= value <= Decimal(1)):
        raise InvalidDecision(f"{field} must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class Decision:
    """The complete scientific record of one entry decision.

    Numeric fields are optional: they are populated when evidence supports a
    quantified estimate and left ``None`` when a quantity is honestly deferred
    (for example the reversion probability of a Multiplier, which requires the
    walk-forward layer). A ``NO_TRADE`` decision may be bare (insufficient
    evidence) or fully quantified (evidence present but no edge).
    """

    action: DecisionAction
    probability: Decimal | None
    probability_lower: Decimal | None
    probability_upper: Decimal | None
    uncertainty: Decimal | None
    expected_value_per_stake: Decimal | None
    risk_edge: Decimal | None
    reason: str
    forecast_action: DecisionAction | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action, DecisionAction):
            raise InvalidDecision("action must be a DecisionAction")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise InvalidDecision("reason must be non-blank")
        if self.forecast_action is not None and self.forecast_action not in _ENTRY_ACTIONS:
            raise InvalidDecision("forecast_action must be an entry DecisionAction or None")
        for name, value in (
            ("probability", self.probability),
            ("probability_lower", self.probability_lower),
            ("probability_upper", self.probability_upper),
        ):
            _finite_probability(value, name)
        for name, value in (
            ("uncertainty", self.uncertainty),
            ("expected_value_per_stake", self.expected_value_per_stake),
            ("risk_edge", self.risk_edge),
        ):
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite()):
                raise InvalidDecision(f"{name} must be a finite Decimal or None")
        if self.uncertainty is not None and self.uncertainty < 0:
            raise InvalidDecision("uncertainty must be non-negative")
        if (
            self.probability_lower is not None
            and self.probability_upper is not None
            and self.probability_lower > self.probability_upper
        ):
            raise InvalidDecision("probability_lower must not exceed probability_upper")


def _no_trade(reason: str) -> Decision:
    return Decision(
        action=DecisionAction.NO_TRADE,
        probability=None,
        probability_lower=None,
        probability_upper=None,
        uncertainty=None,
        expected_value_per_stake=None,
        risk_edge=None,
        reason=reason,
    )


def _require_strictly_increasing(history: Sequence[Tick]) -> None:
    if any(current.epoch <= previous.epoch for previous, current in pairwise(history)):
        raise InvalidDecision("history must be strictly increasing")


def even_odd_decision(
    *,
    history: Sequence[Tick],
    even_economics: DigitEconomics,
    odd_economics: DigitEconomics,
    policy: DigitDecisionPolicy,
) -> Decision:
    """Decide Even/Odd from a Wilson lower bound against observed break-even.

    The estimate is the empirical parity frequency; uncertainty is the Wilson
    interval width and the risk margin is the lower bound minus break-even.
    """
    if len(history) < policy.min_samples:
        return _no_trade(
            f"insufficient sample: observed={len(history)} required={policy.min_samples}"
        )
    _require_strictly_increasing(history)

    sample_count = len(history)
    even_count = sum(last_digit(tick) % 2 == 0 for tick in history)
    candidates = (
        (even_economics, even_count),
        (odd_economics, sample_count - even_count),
    )

    scored: list[tuple[Decimal, DigitEconomics, Decimal, Decimal, Decimal, Decimal]] = []
    for economics, successes in candidates:
        probability = Decimal(successes) / Decimal(sample_count)
        lower = wilson_lower_bound(successes, sample_count, policy.z_score)
        upper = wilson_upper_bound(successes, sample_count, policy.z_score)
        break_even = economics.ask_price / economics.payout
        edge = lower - break_even
        expected_value = probability * (economics.payout / economics.ask_price) - Decimal(1)
        scored.append((edge, economics, probability, lower, upper, expected_value))

    edge, economics, probability, lower, upper, expected_value = max(
        scored, key=lambda candidate: candidate[0]
    )
    uncertainty = upper - lower
    forecast_action = (
        DecisionAction.EVEN
        if economics.contract_type is ContractType.DIGITEVEN
        else DecisionAction.ODD
    )
    if edge <= policy.min_edge_probability:
        return Decision(
            action=DecisionAction.NO_TRADE,
            probability=probability,
            probability_lower=lower,
            probability_upper=upper,
            uncertainty=uncertainty,
            expected_value_per_stake=expected_value,
            risk_edge=edge,
            reason="parity edge does not clear observed break-even",
            forecast_action=forecast_action,
        )
    return Decision(
        action=forecast_action,
        probability=probability,
        probability_lower=lower,
        probability_upper=upper,
        uncertainty=uncertainty,
        expected_value_per_stake=expected_value,
        risk_edge=edge,
        reason="parity edge clears observed break-even",
        forecast_action=forecast_action,
    )


@dataclass(frozen=True, slots=True)
class ReversionPolicy:
    """Frozen thresholds for a mean-reversion entry decision."""

    z_score_threshold: Decimal
    min_deceleration: Decimal
    min_return_frequency: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.z_score_threshold, Decimal)
            or not self.z_score_threshold.is_finite()
            or self.z_score_threshold <= 0
        ):
            raise InvalidDecision("z_score_threshold must be a positive finite Decimal")
        for name, value in (
            ("min_deceleration", self.min_deceleration),
            ("min_return_frequency", self.min_return_frequency),
        ):
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise InvalidDecision(f"{name} must be a non-negative finite Decimal")


def multiplier_decision(
    *,
    history: Sequence[Tick],
    range_policy: RangePolicy,
    reversion_policy: ReversionPolicy,
) -> Decision:
    """Decide a mean-reversion Multiplier direction from the range regime.

    The reversion probability and expected value are honestly deferred to the
    walk-forward layer, so this decision is a bounded technical signal plus a
    risk gate: it requires an extreme Z-score, a decelerating move, and prior
    evidence of reversion (return frequency), but never claims a quantified
    edge on its own.
    """
    if len(history) < range_policy.window + 1:
        return _no_trade(
            f"insufficient range warm-up: observed={len(history)} "
            f"required={range_policy.window + 1}"
        )
    _require_strictly_increasing(history)

    try:
        profile = analyze_range(tuple(tick.quote for tick in history), range_policy)
    except InvalidRangeRegime:
        return _no_trade("degenerate range window cannot support a reversion signal")

    if abs(profile.z_score) <= reversion_policy.z_score_threshold:
        return _no_trade("z-score is within the neutral band")
    if profile.deceleration <= reversion_policy.min_deceleration:
        return _no_trade("no deceleration evidence for a reversal")
    if profile.return_frequency < reversion_policy.min_return_frequency:
        return _no_trade("insufficient historical reversion frequency")

    action = DecisionAction.MULTUP if profile.z_score < 0 else DecisionAction.MULTDOWN
    direction = "up" if action is DecisionAction.MULTUP else "down"
    return Decision(
        action=action,
        probability=None,
        probability_lower=None,
        probability_upper=None,
        uncertainty=None,
        expected_value_per_stake=None,
        risk_edge=None,
        reason=f"extreme z-score with deceleration favors reversion {direction}",
        forecast_action=action,
    )
