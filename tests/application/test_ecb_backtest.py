"""Daily ECB quote-replay backtest application tests."""

from datetime import UTC, datetime, timedelta

import pytest

from devsoul_quant.adapters.ecb.manifest import build_ecb_manifest
from devsoul_quant.application.ecb_backtest import (
    UnapprovedEcbSource,
    run_ecb_daily_backtest,
)
from devsoul_quant.domain.data_rights import DataSourceKind, build_manifest
from devsoul_quant.domain.metrics import EvidenceMode, PromotionEligibility
from devsoul_quant.domain.validation import TemporalSplitSpec


def _make_csv(row_count: int) -> str:
    """Build a newest-first, eurofxref-hist style CSV with deterministic rates."""
    lines = ["Date,USD,"]
    end = datetime(2026, 11, 4, tzinfo=UTC)
    for offset in range(row_count):
        day = end - timedelta(days=offset)
        lines.append(f"{day:%Y-%m-%d},1.{offset:04d},")
    return "\n".join(lines) + "\n"


def _split() -> TemporalSplitSpec:
    return TemporalSplitSpec(
        lookback_ticks=3,
        purge_ticks=3,
        embargo_ticks=2,
        test_ticks=8,
        fold_count=3,
        holdout_ticks=4,
    )


def test_ecb_daily_backtest_produces_quote_replay_report() -> None:
    manifest = build_ecb_manifest(retrieved_at=1_760_000_000)

    result = run_ecb_daily_backtest(
        csv_text=_make_csv(60),
        currency="USD",
        manifest=manifest,
        split=_split(),
        duration=3,
        seed=7,
    )

    assert result.data_source == "ecb"
    assert result.symbol == "EURUSD"
    assert result.tick_count == 60
    assert result.holdout_tick_count == 4
    assert len(result.holdout_hash) == 64

    evaluation = result.evaluation
    assert evaluation.evidence_mode is EvidenceMode.QUOTE_REPLAY_BACKTEST
    assert evaluation.promotion_eligibility is PromotionEligibility.NOT_ELIGIBLE
    assert evaluation.economic_metrics_available is False
    assert evaluation.decisions > 0
    assert evaluation.enter_count + evaluation.wait_count == evaluation.decisions


def test_ecb_daily_backtest_is_deterministic() -> None:
    manifest = build_ecb_manifest(retrieved_at=1_760_000_000)

    first = run_ecb_daily_backtest(
        csv_text=_make_csv(60),
        currency="USD",
        manifest=manifest,
        split=_split(),
        duration=3,
        seed=7,
    )
    second = run_ecb_daily_backtest(
        csv_text=_make_csv(60),
        currency="USD",
        manifest=manifest,
        split=_split(),
        duration=3,
        seed=7,
    )

    assert first == second


def test_ecb_daily_backtest_fails_closed_on_unapproved_manifest() -> None:
    denied = build_manifest(
        source_id="ecb",
        source_kind=DataSourceKind.OPEN_LICENSE,
        license_identifier=None,
        license_url=None,
        retrieved_at=1_760_000_000,
        retention_seconds=0,
    )

    with pytest.raises(UnapprovedEcbSource, match="not approved"):
        run_ecb_daily_backtest(
            csv_text=_make_csv(60),
            currency="USD",
            manifest=denied,
            split=_split(),
        )
