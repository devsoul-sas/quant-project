"""Temporal validation preparation tests."""

from datetime import UTC, datetime

from devsoul_quant.application.build_dataset import build_dataset
from devsoul_quant.application.prepare_validation import open_holdout, prepare_validation
from devsoul_quant.domain.data_rights import DataRightsManifest, DataSourceKind, build_manifest
from devsoul_quant.domain.datasets import (
    GENERATOR_VERSION,
    SCHEMA_VERSION,
    DatasetSnapshot,
    DatasetSpec,
)
from devsoul_quant.domain.experiments import StrategyRelease
from devsoul_quant.domain.ledger import InMemoryLedger
from devsoul_quant.domain.validation import TemporalSplitSpec


def _manifest() -> DataRightsManifest:
    return build_manifest(
        source_id="devsoul-synthetic",
        source_kind=DataSourceKind.DEVSOUL_SYNTHETIC,
        license_identifier="DEVSOUL-INTERNAL-1.0",
        license_url=None,
        retrieved_at=1_760_000_000,
        retention_seconds=31_536_000,
        derived_artifacts_allowed=True,
        partner_display_allowed=True,
        redistribution_allowed=False,
        commercial_use_allowed=False,
        geographic_constraints=(),
        written_authorization_ref=None,
    )


def _snapshot() -> DatasetSnapshot:
    manifest = _manifest()
    return build_dataset(
        spec=DatasetSpec(
            generator_version=GENERATOR_VERSION,
            seed=42,
            start_epoch=1_700_000_000,
            interval=1,
            row_count=40,
            schema_version=SCHEMA_VERSION,
            rights_manifest_hash=manifest.manifest_hash,
        ),
        manifest=manifest,
    )


def test_prepare_validation_builds_a_split_over_the_snapshot() -> None:
    snapshot = _snapshot()
    spec = TemporalSplitSpec(
        lookback_ticks=3,
        purge_ticks=3,
        embargo_ticks=2,
        test_ticks=4,
        fold_count=3,
        holdout_ticks=5,
    )

    split = prepare_validation(spec=spec, snapshot=snapshot, run_id="run-1")

    assert len(split.folds) == 3
    assert split.holdout.tick_count == 5


def test_open_holdout_emits_a_ledger_event() -> None:
    snapshot = _snapshot()
    spec = TemporalSplitSpec(
        lookback_ticks=3,
        purge_ticks=3,
        embargo_ticks=2,
        test_ticks=4,
        fold_count=3,
        holdout_ticks=5,
    )
    split = prepare_validation(spec=spec, snapshot=snapshot, run_id="run-7")
    release = StrategyRelease.draft(
        release_id="release-1",
        strategy_hash="a" * 64,
        feature_set_hash="b" * 64,
        risk_policy_hash="c" * 64,
    ).freeze(datetime(2026, 10, 29, tzinfo=UTC))
    ledger = InMemoryLedger()

    revealed = open_holdout(
        holdout=split.holdout,
        ticks=tuple(snapshot.ticks[-spec.holdout_ticks :]),
        release=release,
        ledger=ledger,
        run_id="run-7",
        occurred_at=1_760_000_000,
    )

    assert len(revealed) == 5
    assert len(ledger.events) == 1
    event = ledger.events[0]
    assert event.event_type == "HOLDOUT_OPENED"
    assert event.payload["release_id"] == "release-1"
    assert event.payload["run_id"] == "run-7"
    assert ledger.verify() is True
