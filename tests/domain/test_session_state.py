"""Tests for the session lifecycle state machine."""

import pytest

from devsoul_quant.domain.session_risk import SessionRiskState
from devsoul_quant.domain.session_state import (
    InvalidSessionState,
    SessionMachine,
    SessionPhase,
    StopReason,
    advance_warmup,
    can_enter,
    new_machine,
    phase,
    resolved_stop_reason,
    stop,
)


def _risk() -> SessionRiskState:
    return SessionRiskState()


def test_new_machine_starts_in_warmup() -> None:
    machine = new_machine(warmup_ticks=5)
    assert phase(machine, _risk()) is SessionPhase.WARMUP


def test_new_machine_rejects_negative_warmup() -> None:
    with pytest.raises(InvalidSessionState, match="warmup_ticks"):
        new_machine(warmup_ticks=-1)


def test_warmup_counts_down_to_running() -> None:
    machine = new_machine(warmup_ticks=2)
    machine = advance_warmup(machine)
    assert phase(machine, _risk()) is SessionPhase.WARMUP
    machine = advance_warmup(machine)
    assert phase(machine, _risk()) is SessionPhase.RUNNING


def test_warmup_floors_at_zero() -> None:
    machine = advance_warmup(new_machine(warmup_ticks=0))
    assert machine.warmup_remaining == 0


def test_cooldown_phase_derives_from_risk_state() -> None:
    machine = new_machine(warmup_ticks=0)
    risk = SessionRiskState(cooldown_remaining=1)
    assert phase(machine, risk) is SessionPhase.COOLDOWN
    assert can_enter(machine, risk) is False


def test_stopped_phase_derives_from_machine_reason() -> None:
    machine = stop(new_machine(warmup_ticks=0), StopReason.KILL_SWITCH)
    assert phase(machine, _risk()) is SessionPhase.STOPPED
    assert resolved_stop_reason(machine, _risk()) is StopReason.KILL_SWITCH


def test_stopped_phase_derives_from_drawdown() -> None:
    machine = new_machine(warmup_ticks=0)
    risk = SessionRiskState(stopped=True)
    assert phase(machine, risk) is SessionPhase.STOPPED
    assert resolved_stop_reason(machine, risk) is StopReason.DRAWDOWN_LIMIT


def test_stop_requires_a_reason() -> None:
    with pytest.raises(InvalidSessionState, match="reason"):
        stop(new_machine(warmup_ticks=0), "NOT_A_REASON")  # type: ignore[arg-type]


def test_machine_rejects_negative_warmup_field() -> None:
    with pytest.raises(InvalidSessionState, match="warmup_remaining"):
        SessionMachine(warmup_remaining=-1)


def test_can_enter_only_in_running() -> None:
    machine = new_machine(warmup_ticks=0)
    assert can_enter(machine, _risk()) is True


def test_resolved_stop_reason_none_when_running() -> None:
    assert resolved_stop_reason(new_machine(warmup_ticks=0), _risk()) is None
