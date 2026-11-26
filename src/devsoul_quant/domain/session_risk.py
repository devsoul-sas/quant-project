"""Stateful session risk engine: drawdown, cooldown and loss-streak gates.

This sits above the per-contract ``RiskPolicy`` gate and enforces session-level
limits across a sequence of paper settlements. It is a pure reducer: every
operation returns a new immutable state, so behaviour is deterministic and
testable without shared mutable state.

A paper session is strictly bounded under 24 hours, so the drawdown limit is
the effective daily drawdown by construction.
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum


class InvalidSessionRisk(ValueError):
    """Raised when a session risk policy or state cannot fail safely."""


class SessionRiskDisposition(StrEnum):
    """Outcome of assessing an entry against the running session risk state."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class SessionRiskPolicy:
    """Frozen session-level limits enforced across paper settlements."""

    max_drawdown: Decimal
    max_consecutive_losses: int
    cooldown_decisions: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.max_drawdown, Decimal)
            or not self.max_drawdown.is_finite()
            or self.max_drawdown <= 0
        ):
            raise InvalidSessionRisk("max_drawdown must be a positive finite Decimal")
        if type(self.max_consecutive_losses) is not int or self.max_consecutive_losses < 1:
            raise InvalidSessionRisk("max_consecutive_losses must be a positive integer")
        if type(self.cooldown_decisions) is not int or self.cooldown_decisions < 0:
            raise InvalidSessionRisk("cooldown_decisions must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class SessionRiskState:
    """Immutable running session risk counters, in stake units."""

    net_result: Decimal = Decimal("0")
    peak_result: Decimal = Decimal("0")
    consecutive_losses: int = 0
    cooldown_remaining: int = 0
    stopped: bool = False

    def __post_init__(self) -> None:
        for name in ("net_result", "peak_result"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise InvalidSessionRisk(f"{name} must be a finite Decimal")
        if self.net_result > self.peak_result:
            raise InvalidSessionRisk("peak_result must be at least net_result")
        for name in ("consecutive_losses", "cooldown_remaining"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise InvalidSessionRisk(f"{name} must be a non-negative integer")
        if type(self.stopped) is not bool:
            raise InvalidSessionRisk("stopped must be a boolean")


@dataclass(frozen=True, slots=True)
class SessionRiskDecision:
    """Verdict of an entry assessment with the reason it was approved or rejected."""

    disposition: SessionRiskDisposition
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, SessionRiskDisposition):
            raise InvalidSessionRisk("disposition must be a SessionRiskDisposition")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise InvalidSessionRisk("reason must be non-blank")


def drawdown(state: SessionRiskState) -> Decimal:
    """Return the current drawdown from the peak result, in stake units."""
    return state.peak_result - state.net_result


def assess_entry(
    state: SessionRiskState, policy: SessionRiskPolicy
) -> tuple[SessionRiskDecision, SessionRiskState]:
    """Assess an entry against the running state, consuming one cooldown slot.

    Returns the verdict plus the resulting state: an active cooldown is
    decremented, and a tripped drawdown limit transitions the state to stopped.
    """
    if state.stopped:
        return SessionRiskDecision(
            SessionRiskDisposition.REJECTED, "session risk stop is active"
        ), state
    if state.cooldown_remaining > 0:
        next_state = replace(state, cooldown_remaining=state.cooldown_remaining - 1)
        return SessionRiskDecision(SessionRiskDisposition.REJECTED, "cooldown active"), next_state
    if drawdown(state) >= policy.max_drawdown:
        return (
            SessionRiskDecision(SessionRiskDisposition.REJECTED, "drawdown limit reached"),
            replace(state, stopped=True),
        )
    return SessionRiskDecision(SessionRiskDisposition.APPROVED, "within session risk limits"), state


def apply_settlement(
    state: SessionRiskState, policy: SessionRiskPolicy, result: Decimal
) -> SessionRiskState:
    """Fold one settled result (stake units, negative = loss) into the state.

    Losses extend the streak; reaching ``max_consecutive_losses`` trips a
    cooldown and resets the streak. A win clears both streak and cooldown.
    The drawdown limit transitions the state to stopped.
    """
    if not isinstance(result, Decimal) or not result.is_finite():
        raise InvalidSessionRisk("result must be a finite Decimal")
    net_result = state.net_result + result
    peak_result = max(state.peak_result, net_result)

    if result < 0:
        streak = state.consecutive_losses + 1
        if streak >= policy.max_consecutive_losses:
            cooldown = policy.cooldown_decisions
            streak = 0
        else:
            cooldown = state.cooldown_remaining
    else:
        streak = 0
        cooldown = 0

    stopped = state.stopped or (peak_result - net_result) >= policy.max_drawdown
    return SessionRiskState(
        net_result=net_result,
        peak_result=peak_result,
        consecutive_losses=streak,
        cooldown_remaining=cooldown,
        stopped=stopped,
    )
