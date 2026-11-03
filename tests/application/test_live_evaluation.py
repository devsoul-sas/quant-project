"""Tests for aggregate ephemeral live tick-proxy evaluation."""

from decimal import Decimal

import pytest

from devsoul_quant.adapters.deriv.ephemeral import OPERATIONAL_MARGIN_SECONDS
from devsoul_quant.application.live_evaluation import (
    InvalidLiveEvaluation,
    run_live_evaluation,
)
from devsoul_quant.domain.execution_mode import ExecutionMode
from devsoul_quant.domain.metrics import PromotionEligibility
from devsoul_quant.domain.replay import EconomyProvenance, Tick


def _ticks(count: int = 30) -> tuple[Tick, ...]:
    quotes = ("100", "101", "100", "102", "101", "103")
    return tuple(
        Tick(epoch=index + 1, quote=Decimal(quotes[index % len(quotes)])) for index in range(count)
    )


def test_live_evaluation_aggregates_every_causally_available_trial() -> None:
    report = run_live_evaluation(ticks=_ticks(), symbol="R_100", duration=2, fold_count=3, seed=42)

    assert report.execution_mode is ExecutionMode.EPHEMERAL_PUBLIC_INTEGRATION
    assert report.schema_version == "2"
    assert report.data_source == "DERIV_DEMO_EPHEMERAL"
    assert report.symbol == "R_100"
    assert report.tick_count == 30
    assert report.duration == 2
    assert report.evaluation.decisions == 10
    assert sum(report.fold_sizes) == report.evaluation.decisions
    assert sum(report.fold_tick_sizes) + report.purge_ticks * 2 == report.tick_count
    assert report.purge_ticks == 4
    assert report.bootstrap_block_size == 4
    assert report.trial_alignment == "CAUSAL_ENTRY_AFTER_SIGNAL"
    assert report.overlapping_windows is True


def test_live_evaluation_is_explicitly_non_economic_and_not_promotable() -> None:
    report = run_live_evaluation(ticks=_ticks(), symbol="R_100", duration=2, fold_count=3, seed=42)
    payload = report.to_dict()

    assert report.economy is EconomyProvenance.UNAVAILABLE
    assert report.profitability_claim is False
    assert report.evaluation.economic_metrics_available is False
    assert report.evaluation.promotion_eligibility is PromotionEligibility.NOT_ELIGIBLE
    assert payload["sample_warning"] == "PURGED_FOLD_TICK_PROXY_DIAGNOSTIC_ONLY"
    for forbidden in ("profit", "roi", "payout", "expected_value", "balance"):
        assert forbidden not in payload


def test_live_evaluation_does_not_serialize_ticks_or_quotes() -> None:
    payload = run_live_evaluation(
        ticks=_ticks(), symbol="R_100", duration=2, fold_count=3, seed=42
    ).to_dict()

    assert "ticks" not in payload
    assert "quotes" not in payload
    assert payload["cache_size"] == 30
    assert payload["cache_expired_count"] == 0


def test_live_evaluation_excludes_expired_ticks_before_building_trials() -> None:
    old_ticks = tuple(Tick(epoch=index + 1, quote=Decimal("90") + index) for index in range(6))
    recent_start = OPERATIONAL_MARGIN_SECONDS + 100
    recent_ticks = tuple(
        Tick(epoch=recent_start + index, quote=Decimal("100") + (index % 3)) for index in range(30)
    )

    report = run_live_evaluation(
        ticks=old_ticks + recent_ticks,
        symbol="R_100",
        duration=2,
        fold_count=3,
        seed=42,
    )

    assert report.tick_count == len(recent_ticks)
    assert report.cache_size == len(recent_ticks)
    assert report.cache_expired_count == len(old_ticks)


@pytest.mark.parametrize(
    ("ticks", "duration", "fold_count", "message"),
    [
        (_ticks(4), 2, 1, "at least one causally settled trial"),
        (_ticks(), 2, 0, "fold_count"),
        (_ticks(), 2, 10, "fold_count"),
    ],
)
def test_live_evaluation_rejects_invalid_sample_design(
    ticks: tuple[Tick, ...], duration: int, fold_count: int, message: str
) -> None:
    with pytest.raises(InvalidLiveEvaluation, match=message):
        run_live_evaluation(
            ticks=ticks,
            symbol="R_100",
            duration=duration,
            fold_count=fold_count,
            seed=42,
        )
