"""Systematic daily edge search over observed ECB data tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from devsoul_quant.adapters.ecb.manifest import build_ecb_manifest
from devsoul_quant.application.ecb_backtest import UnapprovedEcbSource
from devsoul_quant.application.edge_search import (
    EdgeCandidate,
    InvalidEdgeSearch,
    search_daily_edges,
)
from devsoul_quant.domain.data_rights import DataSourceKind, build_manifest
from devsoul_quant.domain.validation import TemporalSplitSpec


def _make_csv(row_count: int) -> str:
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


def test_search_daily_edges_enumerates_all_combinations() -> None:
    manifest = build_ecb_manifest(retrieved_at=1_760_000_000)

    candidates = search_daily_edges(
        csv_text=_make_csv(60),
        currency="USD",
        manifest=manifest,
        split_spec=_split(),
        seed=7,
        strategies=("momentum", "mean-reversion"),
        lookbacks=(1, 2),
        durations=(3,),
        spread_fractions=(Decimal("0"), Decimal("0.0001")),
    )

    assert len(candidates) == 8
    assert all(candidate.decisions > 0 for candidate in candidates)
    assert all(len(candidate.holdout_hash) == 64 for candidate in candidates)
    assert {candidate.strategy for candidate in candidates} == {"momentum", "mean-reversion"}


def test_search_daily_edges_rejects_empty_config() -> None:
    manifest = build_ecb_manifest(retrieved_at=1_760_000_000)

    with pytest.raises(InvalidEdgeSearch, match="at least one"):
        search_daily_edges(
            csv_text=_make_csv(60),
            currency="USD",
            manifest=manifest,
            split_spec=_split(),
            seed=7,
            strategies=(),
            lookbacks=(1,),
            durations=(3,),
            spread_fractions=(Decimal("0"),),
        )


def test_search_daily_edges_rejects_invalid_lookback() -> None:
    manifest = build_ecb_manifest(retrieved_at=1_760_000_000)

    with pytest.raises(InvalidEdgeSearch, match="lookbacks"):
        search_daily_edges(
            csv_text=_make_csv(60),
            currency="USD",
            manifest=manifest,
            split_spec=_split(),
            seed=7,
            strategies=("momentum",),
            lookbacks=(0,),
            durations=(3,),
            spread_fractions=(Decimal("0"),),
        )


def test_edge_candidate_has_edge_requires_bootstrap_above_coin_flip() -> None:
    strong = EdgeCandidate(
        strategy="momentum",
        lookback=1,
        duration=3,
        spread_fraction=Decimal("0"),
        decisions=10,
        hit_rate=Decimal("0.60"),
        bootstrap_lower=Decimal("0.52"),
        bootstrap_upper=Decimal("0.68"),
        holdout_hash="a" * 64,
        run_id="r",
    )
    weak = EdgeCandidate(
        strategy="momentum",
        lookback=1,
        duration=3,
        spread_fraction=Decimal("0"),
        decisions=10,
        hit_rate=Decimal("0.47"),
        bootstrap_lower=Decimal("0.44"),
        bootstrap_upper=Decimal("0.50"),
        holdout_hash="b" * 64,
        run_id="r",
    )

    assert strong.has_edge is True
    assert weak.has_edge is False


def test_edge_candidate_has_edge_false_when_bootstrap_missing() -> None:
    candidate = EdgeCandidate(
        strategy="momentum",
        lookback=1,
        duration=3,
        spread_fraction=Decimal("0"),
        decisions=0,
        hit_rate=None,
        bootstrap_lower=None,
        bootstrap_upper=None,
        holdout_hash="c" * 64,
        run_id="r",
    )

    assert candidate.has_edge is False


def test_search_daily_edges_rejects_unknown_strategy() -> None:
    manifest = build_ecb_manifest(retrieved_at=1_760_000_000)

    with pytest.raises(InvalidEdgeSearch, match="unknown strategy"):
        search_daily_edges(
            csv_text=_make_csv(60),
            currency="USD",
            manifest=manifest,
            split_spec=_split(),
            seed=7,
            strategies=("nonsense",),
            lookbacks=(1,),
            durations=(3,),
            spread_fractions=(Decimal("0"),),
        )


def test_search_daily_edges_fails_closed_on_unapproved_manifest() -> None:
    denied = build_manifest(
        source_id="ecb",
        source_kind=DataSourceKind.OPEN_LICENSE,
        license_identifier=None,
        license_url=None,
        retrieved_at=1_760_000_000,
        retention_seconds=0,
    )

    with pytest.raises(UnapprovedEcbSource, match="not approved"):
        search_daily_edges(
            csv_text=_make_csv(60),
            currency="USD",
            manifest=denied,
            split_spec=_split(),
            seed=7,
            strategies=("momentum",),
            lookbacks=(1,),
            durations=(3,),
            spread_fractions=(Decimal("0"),),
        )
