"""Ephemeral live demo orchestration tests."""

from decimal import Decimal

import pytest

from devsoul_quant.adapters.deriv.ephemeral import OPERATIONAL_MARGIN_SECONDS
from devsoul_quant.application.live_demo import InvalidLiveDemo, run_live_demo
from devsoul_quant.domain.contracts import ContractAction
from devsoul_quant.domain.execution_mode import ExecutionMode
from devsoul_quant.domain.replay import EconomyProvenance, Outcome, Tick
from devsoul_quant.domain.synthetic import generate_ticks

RISING = (
    Tick(epoch=1, quote=Decimal("100.0000")),
    Tick(epoch=2, quote=Decimal("101.0000")),
    Tick(epoch=3, quote=Decimal("102.0000")),
    Tick(epoch=4, quote=Decimal("103.0000")),
    Tick(epoch=5, quote=Decimal("104.0000")),
)


def test_live_demo_runs_the_pipeline_in_ephemeral_mode() -> None:
    report = run_live_demo(ticks=RISING, symbol="R_100")

    assert report.execution_mode is ExecutionMode.EPHEMERAL_PUBLIC_INTEGRATION
    assert report.data_source == "DERIV_DEMO_EPHEMERAL"
    assert report.symbol == "R_100"
    assert report.economy is EconomyProvenance.UNAVAILABLE
    assert report.profitability_claim is False
    assert report.ledger_valid is True
    assert report.ledger_head_hash


def test_live_demo_carries_the_real_symbol_into_the_intent() -> None:
    report = run_live_demo(ticks=RISING, symbol="R_100")

    assert report.action is ContractAction.ENTER_CONTRACT
    assert report.symbol == "R_100"


def test_live_demo_records_ephemeral_cache_facts() -> None:
    report = run_live_demo(ticks=RISING, symbol="R_100")

    assert report.cache_ttl_seconds == OPERATIONAL_MARGIN_SECONDS
    assert report.cache_size == len(RISING)
    assert report.cache_expired_count == 0


def test_live_demo_records_the_directional_outcome_without_economy() -> None:
    report = run_live_demo(ticks=RISING, symbol="R_100")

    assert report.outcome is Outcome.WIN
    assert report.wins == 1
    assert report.losses == 0
    assert report.no_trades == 0
    assert report.economy is EconomyProvenance.UNAVAILABLE


def test_live_demo_can_emit_no_trade_on_flat_ticks() -> None:
    flat = (
        Tick(epoch=1, quote=Decimal("100.0")),
        Tick(epoch=2, quote=Decimal("100.0")),
    )

    report = run_live_demo(ticks=flat, symbol="R_50")

    assert report.action is ContractAction.NO_TRADE
    assert report.no_trades == 1
    assert report.outcome is None


@pytest.mark.parametrize(
    ("ticks", "symbol"),
    [
        ((Tick(epoch=1, quote=Decimal("1.0")),), "R_100"),
        (
            (Tick(epoch=1, quote=Decimal("1.0")), Tick(epoch=2, quote=Decimal("2.0"))),
            "   ",
        ),
    ],
)
def test_live_demo_rejects_invalid_inputs(ticks: tuple[Tick, ...], symbol: str) -> None:
    with pytest.raises(InvalidLiveDemo):
        run_live_demo(ticks=ticks, symbol=symbol)


def test_live_demo_report_serializes_deterministically() -> None:
    first = run_live_demo(ticks=RISING, symbol="R_100").to_dict()
    second = run_live_demo(ticks=RISING, symbol="R_100").to_dict()

    assert first == second
    assert isinstance(first["ledger_hashes"], list)


def test_live_demo_enters_call_for_a_rising_window() -> None:
    report = run_live_demo(ticks=RISING, symbol="R_100")

    assert report.action is ContractAction.ENTER_CONTRACT
    assert report.outcome is Outcome.WIN


def test_live_demo_report_is_reproducible_from_synthetic_ticks() -> None:
    ticks = generate_ticks(seed=3, count=5)

    report = run_live_demo(ticks=ticks, symbol="R_75")

    assert report.execution_mode is ExecutionMode.EPHEMERAL_PUBLIC_INTEGRATION
    assert report.ledger_valid is True
