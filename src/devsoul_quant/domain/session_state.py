"""Session lifecycle: warm-up, running, cooldown and terminal stop.

The lifecycle phase is derived from three independent signals: warm-up progress
(owned here), the running session risk state (cooldown and drawdown stop) and
an explicit terminal reason (owned here). The machine only owns what the risk
engine does not, so there is no duplicated state between the two.
"""

from dataclasses import dataclass
from enum import StrEnum

from devsoul_quant.domain.session_risk import SessionRiskState


class InvalidSessionState(ValueError):
    """Raised when a session machine cannot represent a safe lifecycle."""


class SessionPhase(StrEnum):
    """The complete lifecycle a paper session may occupy."""

    WARMUP = "WARMUP"
    RUNNING = "RUNNING"
    COOLDOWN = "COOLDOWN"
    STOPPED = "STOPPED"


class StopReason(StrEnum):
    """Terminal reasons a session may report, including the risk drawdown limit."""

    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    KILL_SWITCH = "KILL_SWITCH"
    TTL_EXPIRED = "TTL_EXPIRED"
    MANUAL = "MANUAL"


@dataclass(frozen=True, slots=True)
class SessionMachine:
    """Immutable lifecycle state: warm-up countdown and an optional stop reason."""

    warmup_remaining: int
    stop_reason: StopReason | None = None

    def __post_init__(self) -> None:
        if type(self.warmup_remaining) is not int or self.warmup_remaining < 0:
            raise InvalidSessionState("warmup_remaining must be a non-negative integer")
        if self.stop_reason is not None and not isinstance(self.stop_reason, StopReason):
            raise InvalidSessionState("stop_reason must be a StopReason or None")


def new_machine(warmup_ticks: int) -> SessionMachine:
    """Start a machine in warm-up for ``warmup_ticks`` ticks."""
    if type(warmup_ticks) is not int or warmup_ticks < 0:
        raise InvalidSessionState("warmup_ticks must be a non-negative integer")
    return SessionMachine(warmup_remaining=warmup_ticks)


def advance_warmup(machine: SessionMachine) -> SessionMachine:
    """Consume one observed tick of warm-up, flooring at zero."""
    return SessionMachine(
        warmup_remaining=max(0, machine.warmup_remaining - 1),
        stop_reason=machine.stop_reason,
    )


def stop(machine: SessionMachine, reason: StopReason) -> SessionMachine:
    """Transition the machine to a terminal stop with an explicit reason."""
    if not isinstance(reason, StopReason):
        raise InvalidSessionState("reason must be a StopReason")
    return SessionMachine(warmup_remaining=machine.warmup_remaining, stop_reason=reason)


def phase(machine: SessionMachine, risk_state: SessionRiskState) -> SessionPhase:
    """Derive the lifecycle phase from the machine and the running risk state."""
    if machine.stop_reason is not None or risk_state.stopped:
        return SessionPhase.STOPPED
    if risk_state.cooldown_remaining > 0:
        return SessionPhase.COOLDOWN
    if machine.warmup_remaining > 0:
        return SessionPhase.WARMUP
    return SessionPhase.RUNNING


def can_enter(machine: SessionMachine, risk_state: SessionRiskState) -> bool:
    """Whether an entry may be assessed in the current phase."""
    return phase(machine, risk_state) is SessionPhase.RUNNING


def resolved_stop_reason(
    machine: SessionMachine, risk_state: SessionRiskState
) -> StopReason | None:
    """Return the reason the session is stopped, or None when it is not."""
    if machine.stop_reason is not None:
        return machine.stop_reason
    if risk_state.stopped:
        return StopReason.DRAWDOWN_LIMIT
    return None
