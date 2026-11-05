"""Frozen Federal Reserve H.10 EURGBP confirmation tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from devsoul_quant.adapters.federal_reserve.manifest import build_fed_h10_manifest
from devsoul_quant.application.fed_h10_confirmation import (
    CONFIRMATORY_DURATION,
    CONFIRMATORY_LOOKBACK,
    CONFIRMATORY_SPREAD,
    CONFIRMATORY_SPREADS,
    UnapprovedFedH10Source,
    run_fed_h10_eurgbp_confirmation,
    run_fed_h10_eurgbp_sensitivity,
)
from devsoul_quant.domain.data_rights import DataSourceKind, build_manifest
from devsoul_quant.domain.metrics import EvidenceMode, PromotionEligibility


def _series(label: str, count: int, *, base: Decimal, slope: Decimal) -> str:
    start = datetime(2000, 1, 3, tzinfo=UTC)
    rows = []
    for offset in range(count):
        date = start + timedelta(days=offset)
        rate = base + slope * Decimal(offset) + Decimal(offset % 7) / Decimal("10000")
        rows.append(f"<tr><td>{date:%-d-%b-%y}</td><td>{rate}</td></tr>")
    return (
        "<!doctype html><html><body>"
        f"<h5>Historical Rates for the {label}</h5><table>"
        + "".join(rows)
        + "</table></body></html>"
    )


def _inputs() -> tuple[str, str]:
    return (
        _series("EU Euro", 1700, base=Decimal("1.02"), slope=Decimal("0.00001")),
        _series(
            "Great British Pound",
            1700,
            base=Decimal("1.50"),
            slope=Decimal("0.00002"),
        ),
    )


def test_confirmation_uses_frozen_hypothesis_and_keeps_holdout_sealed() -> None:
    euros, pounds = _inputs()
    manifest = build_fed_h10_manifest(retrieved_at=1_760_000_000)

    result = run_fed_h10_eurgbp_confirmation(
        usd_per_eur_html=euros,
        usd_per_gbp_html=pounds,
        manifest=manifest,
    )

    assert result.data_source == "federal-reserve-h10"
    assert result.symbol == "EURGBP"
    assert result.lookback == CONFIRMATORY_LOOKBACK == 10
    assert result.duration == CONFIRMATORY_DURATION == 5
    assert result.spread_fraction == CONFIRMATORY_SPREAD == Decimal("0.0001")
    assert result.tick_count == 1700
    assert result.holdout_tick_count == 252
    assert len(result.holdout_hash) == 64
    assert result.holdout_opened is False
    assert result.evaluation.evidence_mode is EvidenceMode.QUOTE_REPLAY_BACKTEST
    assert result.evaluation.promotion_eligibility is PromotionEligibility.NOT_ELIGIBLE
    assert result.evaluation.economic_metrics_available is False
    expected_confirms = (
        result.evaluation.bootstrap_interval is not None
        and result.evaluation.bootstrap_interval.lower > Decimal("0.50")
    )
    assert result.confirms_directional_signal is expected_confirms


def test_confirmation_is_deterministic() -> None:
    euros, pounds = _inputs()
    manifest = build_fed_h10_manifest(retrieved_at=1_760_000_000)

    first = run_fed_h10_eurgbp_confirmation(
        usd_per_eur_html=euros,
        usd_per_gbp_html=pounds,
        manifest=manifest,
    )
    second = run_fed_h10_eurgbp_confirmation(
        usd_per_eur_html=euros,
        usd_per_gbp_html=pounds,
        manifest=manifest,
    )

    assert first == second


def test_confirmation_fails_closed_before_parsing_unapproved_source() -> None:
    denied = build_manifest(
        source_id="fed-h10",
        source_kind=DataSourceKind.OPEN_LICENSE,
        license_identifier=None,
        license_url=None,
        retrieved_at=1_760_000_000,
        retention_seconds=0,
    )

    with pytest.raises(UnapprovedFedH10Source, match="not approved"):
        run_fed_h10_eurgbp_confirmation(
            usd_per_eur_html="not html",
            usd_per_gbp_html="not html",
            manifest=denied,
        )


def test_sensitivity_is_monotonic_and_uses_frozen_ladder() -> None:
    euros, pounds = _inputs()
    manifest = build_fed_h10_manifest(retrieved_at=1_760_000_000)

    points = run_fed_h10_eurgbp_sensitivity(
        usd_per_eur_html=euros,
        usd_per_gbp_html=pounds,
        manifest=manifest,
    )

    assert [point.spread_fraction for point in points] == list(CONFIRMATORY_SPREADS)
    hit_rates = [point.hit_rate for point in points]
    assert all(rate is not None for rate in hit_rates)
    non_none = [rate for rate in hit_rates if rate is not None]
    assert non_none == sorted(non_none, reverse=True)
    for point in points:
        assert point.confirms is (
            point.bootstrap_lower is not None and point.bootstrap_lower > Decimal("0.50")
        )
