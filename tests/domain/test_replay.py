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
from devsoul_quant.domain.replay import (
    EconomyProvenance,
    InsufficientTicks,
    InvalidTick,
    InvalidTickSequence,
    Outcome,
    Tick,
    UnsupportedBarrier,
    replay_rise_fall,
)


def test_economy_provenance_is_explicit() -> None:
    assert {provenance.value for provenance in EconomyProvenance} == {
        "OBSERVED",
        "ESTIMATED",
        "UNAVAILABLE",
    }


@pytest.mark.parametrize("quote", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_tick_rejects_non_finite_quotes(quote: Decimal) -> None:
    with pytest.raises(InvalidTick, match="finite"):
        Tick(epoch=100, quote=quote)


def test_tick_rejects_a_boolean_epoch() -> None:
    with pytest.raises(InvalidTick, match="integer"):
        Tick(epoch=True, quote=Decimal("100"))


def test_tick_rejects_a_non_decimal_quote() -> None:
    with pytest.raises(InvalidTick, match="Decimal"):
        Tick(epoch=100, quote=100.0)  # type: ignore[arg-type]


def test_call_wins_when_exit_quote_is_above_entry_quote() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_RISE_FALL",
        contract_type=ContractType.CALL,
        duration=2,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="synthetic tracer",
    )
    ticks = (
        Tick(epoch=100, quote=Decimal("100.0")),
        Tick(epoch=101, quote=Decimal("99.5")),
        Tick(epoch=102, quote=Decimal("100.1")),
    )

    result = replay_rise_fall(intent, ticks)

    assert result.outcome is Outcome.WIN
    assert result.economy is EconomyProvenance.UNAVAILABLE
    assert result.entry_tick == ticks[0]
    assert result.exit_tick == ticks[2]


def test_put_wins_when_exit_quote_is_below_entry_quote() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_RISE_FALL",
        contract_type=ContractType.PUT,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="synthetic tracer",
    )
    ticks = (
        Tick(epoch=100, quote=Decimal("100.0")),
        Tick(epoch=101, quote=Decimal("99.9")),
    )

    result = replay_rise_fall(intent, ticks)

    assert result.outcome is Outcome.WIN


def test_replay_rejects_an_incomplete_tick_window() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_RISE_FALL",
        contract_type=ContractType.CALL,
        duration=2,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="synthetic tracer",
    )
    ticks = (Tick(epoch=100, quote=Decimal("100.0")),)

    with pytest.raises(InsufficientTicks, match="does not reach contract expiry"):
        replay_rise_fall(intent, ticks)


def test_replay_rejects_non_monotonic_epochs() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_RISE_FALL",
        contract_type=ContractType.CALL,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="synthetic tracer",
    )
    ticks = (
        Tick(epoch=100, quote=Decimal("100.0")),
        Tick(epoch=100, quote=Decimal("100.1")),
    )

    with pytest.raises(InvalidTickSequence, match="strictly increasing"):
        replay_rise_fall(intent, ticks)


def test_rise_fall_replay_rejects_a_barrier_it_cannot_settle() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_RISE_FALL",
        contract_type=ContractType.CALL,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1"),
        currency="USD",
        barrier=Decimal("100"),
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="synthetic tracer",
    )
    ticks = (
        Tick(epoch=100, quote=Decimal("50")),
        Tick(epoch=101, quote=Decimal("51")),
    )

    with pytest.raises(UnsupportedBarrier, match="barrier"):
        replay_rise_fall(intent, ticks)


def test_rise_fall_replay_rejects_a_digit_contract() -> None:
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
        strategy_reason="wrong replay",
    )

    with pytest.raises(ValueError, match="CALL or PUT"):
        replay_rise_fall(
            intent,
            (
                Tick(epoch=1, quote=Decimal("100.1"), pip_size=1),
                Tick(epoch=2, quote=Decimal("100.2"), pip_size=1),
            ),
        )
