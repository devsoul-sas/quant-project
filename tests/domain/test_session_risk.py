"""Tests for the stateful session risk engine."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.session_risk import (
    InvalidSessionRisk,
    SessionRiskDisposition,
    SessionRiskPolicy,
    SessionRiskState,
    apply_settlement,
    assess_entry,
    drawdown,
)


def _policy() -> SessionRiskPolicy:
    return SessionRiskPolicy(
        max_drawdown=Decimal("5"),
        max_consecutive_losses=3,
        cooldown_decisions=2,
    )


def _fresh() -> SessionRiskState:
    return SessionRiskState()


# --- policy and state validation -----------------------------------------------


def test_policy_rejects_non_positive_drawdown() -> None:
    with pytest.raises(InvalidSessionRisk, match="max_drawdown"):
        SessionRiskPolicy(max_drawdown=Decimal("0"), max_consecutive_losses=3, cooldown_decisions=2)


def test_policy_rejects_zero_streak_limit() -> None:
    with pytest.raises(InvalidSessionRisk, match="max_consecutive_losses"):
        SessionRiskPolicy(max_drawdown=Decimal("5"), max_consecutive_losses=0, cooldown_decisions=2)


def test_policy_rejects_negative_cooldown() -> None:
    with pytest.raises(InvalidSessionRisk, match="cooldown_decisions"):
        SessionRiskPolicy(
            max_drawdown=Decimal("5"), max_consecutive_losses=3, cooldown_decisions=-1
        )


def test_state_rejects_peak_below_net() -> None:
    with pytest.raises(InvalidSessionRisk, match="peak_result"):
        SessionRiskState(net_result=Decimal("1"), peak_result=Decimal("0"))


def test_state_rejects_negative_streak() -> None:
    with pytest.raises(InvalidSessionRisk, match="consecutive_losses"):
        SessionRiskState(consecutive_losses=-1)


# --- entry assessment -----------------------------------------------------------


def test_fresh_state_approves_entry() -> None:
    decision, _ = assess_entry(_fresh(), _policy())
    assert decision.disposition is SessionRiskDisposition.APPROVED


def test_stopped_state_rejects_entry() -> None:
    state = SessionRiskState(stopped=True)
    decision, next_state = assess_entry(state, _policy())
    assert decision.disposition is SessionRiskDisposition.REJECTED
    assert next_state is state


def test_cooldown_consumes_slots_and_recovers() -> None:
    state = SessionRiskState(cooldown_remaining=2)
    decision, state = assess_entry(state, _policy())
    assert decision.disposition is SessionRiskDisposition.REJECTED
    assert state.cooldown_remaining == 1
    decision, state = assess_entry(state, _policy())
    assert decision.disposition is SessionRiskDisposition.REJECTED
    assert state.cooldown_remaining == 0
    decision, _ = assess_entry(state, _policy())
    assert decision.disposition is SessionRiskDisposition.APPROVED


def test_drawdown_limit_stops_the_session() -> None:
    state = SessionRiskState(net_result=Decimal("-4"), peak_result=Decimal("2"))
    decision, next_state = assess_entry(state, _policy())
    assert decision.disposition is SessionRiskDisposition.REJECTED
    assert next_state.stopped is True


# --- settlement ----------------------------------------------------------------


def test_loss_extends_streak_without_cooldown() -> None:
    state = apply_settlement(_fresh(), _policy(), Decimal("-1"))
    assert state.consecutive_losses == 1
    assert state.cooldown_remaining == 0
    assert state.net_result == Decimal("-1")


def test_streak_limit_trips_cooldown_and_resets() -> None:
    state = _fresh()
    for _ in range(3):
        state = apply_settlement(state, _policy(), Decimal("-1"))
    assert state.cooldown_remaining == 2
    assert state.consecutive_losses == 0
    assert state.net_result == Decimal("-3")


def test_win_clears_streak_and_cooldown() -> None:
    state = SessionRiskState(consecutive_losses=2, cooldown_remaining=1, net_result=Decimal("-2"))
    state = apply_settlement(state, _policy(), Decimal("3"))
    assert state.consecutive_losses == 0
    assert state.cooldown_remaining == 0
    assert state.net_result == Decimal("1")
    assert state.peak_result == Decimal("1")


def test_settlement_tracks_peak_and_drawdown() -> None:
    state = apply_settlement(_fresh(), _policy(), Decimal("4"))
    assert state.peak_result == Decimal("4")
    state = apply_settlement(state, _policy(), Decimal("-2"))
    assert drawdown(state) == Decimal("2")
    assert state.peak_result == Decimal("4")


def test_settlement_stops_on_drawdown_limit() -> None:
    state = apply_settlement(_fresh(), _policy(), Decimal("4"))
    state = apply_settlement(state, _policy(), Decimal("-6"))
    assert state.net_result == Decimal("-2")
    assert drawdown(state) == Decimal("6")
    assert state.stopped is True


def test_settlement_rejects_non_finite_result() -> None:
    with pytest.raises(InvalidSessionRisk, match="result"):
        apply_settlement(_fresh(), _policy(), Decimal("Infinity"))
