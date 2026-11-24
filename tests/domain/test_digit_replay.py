"""Deterministic Even/Odd settlement tests."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
)
from devsoul_quant.domain.digit_replay import replay_digit
from devsoul_quant.domain.replay import (
    InsufficientTicks,
    InvalidTickSequence,
    Outcome,
    Tick,
    UnsupportedBarrier,
)


def test_even_contract_wins_when_expiry_display_digit_is_even() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="R_10",
        contract_type=ContractType.DIGITEVEN,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="paper parity baseline",
    )
    ticks = (
        Tick(epoch=100, quote=Decimal("123.1"), pip_size=1),
        Tick(epoch=101, quote=Decimal("123.2"), pip_size=1),
    )

    result = replay_digit(intent, ticks)

    assert result.outcome is Outcome.WIN
    assert result.exit_tick == ticks[1]


def test_odd_contract_loses_when_expiry_display_digit_is_even() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="R_10",
        contract_type=ContractType.DIGITODD,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="paper parity baseline",
    )

    result = replay_digit(
        intent,
        (
            Tick(epoch=100, quote=Decimal("123.1"), pip_size=1),
            Tick(epoch=101, quote=Decimal("123.2"), pip_size=1),
        ),
    )

    assert result.outcome is Outcome.LOSS


def test_digit_replay_rejects_incomplete_window() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="R_10",
        contract_type=ContractType.DIGITEVEN,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="paper parity baseline",
    )

    with pytest.raises(InsufficientTicks):
        replay_digit(intent, (Tick(epoch=100, quote=Decimal("123.1"), pip_size=1),))


def test_digit_replay_rejects_unordered_ticks() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="R_10",
        contract_type=ContractType.DIGITEVEN,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="paper parity baseline",
    )

    with pytest.raises(InvalidTickSequence):
        replay_digit(
            intent,
            (
                Tick(epoch=100, quote=Decimal("123.1"), pip_size=1),
                Tick(epoch=100, quote=Decimal("123.2"), pip_size=1),
            ),
        )


def test_digit_replay_rejects_barrier_and_directional_contracts() -> None:
    base = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="R_10",
        contract_type=ContractType.DIGITEVEN,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="paper parity baseline",
    )
    ticks = (
        Tick(epoch=100, quote=Decimal("123.1"), pip_size=1),
        Tick(epoch=101, quote=Decimal("123.2"), pip_size=1),
    )

    with pytest.raises(UnsupportedBarrier):
        replay_digit(base.model_copy(update={"barrier": Decimal("1")}), ticks)
    with pytest.raises(ValueError, match="Even/Odd"):
        replay_digit(base.model_copy(update={"contract_type": ContractType.CALL}), ticks)
