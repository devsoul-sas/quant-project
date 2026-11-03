"""Deterministic dataset build and write tests."""

import json
from pathlib import Path

import pytest

from devsoul_quant.application.build_dataset import (
    UnapprovedDatasetSource,
    build_dataset,
    write_snapshot,
)
from devsoul_quant.domain.data_rights import (
    DataRightsManifest,
    DataSourceKind,
    PersistentUseDecision,
    build_manifest,
    decide_persistent_use,
)
from devsoul_quant.domain.datasets import (
    GENERATOR_VERSION,
    SCHEMA_VERSION,
    DatasetSpec,
    build_snapshot,
    serialize_dataset,
)
from devsoul_quant.domain.synthetic import generate_ticks


def _synthetic_manifest() -> DataRightsManifest:
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


def _unapproved_external_manifest() -> DataRightsManifest:
    return build_manifest(
        source_id="deriv",
        source_kind=DataSourceKind.LICENSED_EXTERNAL,
        license_identifier="DERIV-API-USERS-TERMS-R26",
        license_url="https://deriv.com/terms-and-conditions/api-users",
        retrieved_at=1_760_000_000,
        retention_seconds=3600,
    )


def _unapproved_synthetic_manifest() -> DataRightsManifest:
    return build_manifest(
        source_id="devsoul-synthetic",
        source_kind=DataSourceKind.DEVSOUL_SYNTHETIC,
        license_identifier=None,
        license_url=None,
        retrieved_at=1_760_000_000,
        retention_seconds=31_536_000,
    )


def _spec(manifest: DataRightsManifest) -> DatasetSpec:
    return DatasetSpec(
        generator_version=GENERATOR_VERSION,
        seed=42,
        start_epoch=1_700_000_000,
        interval=1,
        row_count=8,
        schema_version=SCHEMA_VERSION,
        rights_manifest_hash=manifest.manifest_hash,
    )


def test_build_dataset_is_deterministic() -> None:
    manifest = _synthetic_manifest()

    first = build_dataset(spec=_spec(manifest), manifest=manifest)
    second = build_dataset(spec=_spec(manifest), manifest=manifest)

    assert first == second
    assert first.data_hash == second.data_hash


def test_build_dataset_rejects_unapproved_external_manifest() -> None:
    manifest = _unapproved_external_manifest()

    assert decide_persistent_use(manifest).decision is PersistentUseDecision.DENY
    with pytest.raises(UnapprovedDatasetSource):
        build_dataset(spec=_spec(manifest), manifest=manifest)


def test_build_dataset_binds_manifest_hash() -> None:
    manifest = _synthetic_manifest()

    snapshot = build_dataset(spec=_spec(manifest), manifest=manifest)

    assert snapshot.spec.rights_manifest_hash == manifest.manifest_hash
    assert snapshot.manifest.manifest_hash == manifest.manifest_hash


def test_write_snapshot_is_byte_identical_across_directories(tmp_path: Path) -> None:
    manifest = _synthetic_manifest()
    snapshot = build_dataset(spec=_spec(manifest), manifest=manifest)

    first = write_snapshot(snapshot, tmp_path / "a")
    second = write_snapshot(snapshot, tmp_path / "b")

    assert first.read_bytes() == second.read_bytes()


def test_write_snapshot_writes_manifest_and_data(tmp_path: Path) -> None:
    manifest = _synthetic_manifest()
    snapshot = build_dataset(spec=_spec(manifest), manifest=manifest)

    data_path = write_snapshot(snapshot, tmp_path / "out")

    assert data_path.read_text(encoding="utf-8") == serialize_dataset(snapshot)
    manifest_payload = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_payload["manifest_hash"] == manifest.manifest_hash


def test_write_snapshot_refuses_unapproved_source(tmp_path: Path) -> None:
    manifest = _unapproved_synthetic_manifest()
    spec = _spec(manifest)
    ticks = generate_ticks(
        seed=spec.seed,
        count=spec.row_count,
        start_epoch=spec.start_epoch,
        interval=spec.interval,
    )
    snapshot = build_snapshot(spec=spec, manifest=manifest, ticks=ticks)

    with pytest.raises(UnapprovedDatasetSource):
        write_snapshot(snapshot, tmp_path / "out")
