"""Immutable synthetic dataset snapshot tests."""

import json
from decimal import Decimal
from hashlib import sha256

import pytest

from devsoul_quant.domain.data_rights import DataRightsManifest, DataSourceKind, build_manifest
from devsoul_quant.domain.datasets import (
    GENERATOR_VERSION,
    SCHEMA_VERSION,
    DatasetSnapshot,
    DatasetSpec,
    InvalidDataset,
    build_snapshot,
    serialize_dataset,
)
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.synthetic import generate_ticks


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


def _spec(manifest: DataRightsManifest, **overrides: object) -> DatasetSpec:
    fields: dict[str, object] = {
        "generator_version": GENERATOR_VERSION,
        "seed": 42,
        "start_epoch": 1_700_000_000,
        "interval": 1,
        "row_count": 8,
        "schema_version": SCHEMA_VERSION,
        "rights_manifest_hash": manifest.manifest_hash,
    }
    fields.update(overrides)
    return DatasetSpec(**fields)  # type: ignore[arg-type]


def _ticks(spec: DatasetSpec) -> tuple[Tick, ...]:
    return generate_ticks(
        seed=spec.seed,
        count=spec.row_count,
        start_epoch=spec.start_epoch,
        interval=spec.interval,
    )


def _snapshot(**spec_overrides: object) -> DatasetSnapshot:
    manifest = _manifest()
    spec = _spec(manifest, **spec_overrides)
    return build_snapshot(spec=spec, manifest=manifest, ticks=_ticks(spec))


def test_spec_hash_is_deterministic_and_canonical() -> None:
    manifest = _manifest()

    first = _spec(manifest).spec_hash()
    second = _spec(manifest).spec_hash()
    changed = _spec(manifest, seed=43).spec_hash()

    assert first == second
    assert len(first) == 64
    assert changed != first


@pytest.mark.parametrize(
    "overrides",
    [
        {"generator_version": "   "},
        {"seed": True},
        {"start_epoch": -1},
        {"interval": 0},
        {"row_count": 1},
        {"schema_version": ""},
        {"rights_manifest_hash": "not-a-hash"},
    ],
)
def test_spec_rejects_invalid_fields(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidDataset):
        _spec(_manifest(), **overrides)


def test_snapshot_rejects_mismatched_manifest_hash() -> None:
    manifest = _manifest()
    spec = _spec(manifest, rights_manifest_hash="a" * 64)

    with pytest.raises(InvalidDataset, match="manifest"):
        build_snapshot(spec=spec, manifest=manifest, ticks=_ticks(spec))


def test_snapshot_rejects_non_synthetic_provenance() -> None:
    manifest = build_manifest(
        source_id="external-x",
        source_kind=DataSourceKind.LICENSED_EXTERNAL,
        license_identifier="EXT-1.0",
        license_url="https://example.com/license",
        retrieved_at=1_760_000_000,
        retention_seconds=3600,
    )
    spec = _spec(manifest)

    with pytest.raises(InvalidDataset, match="synthetic"):
        build_snapshot(spec=spec, manifest=manifest, ticks=_ticks(spec))


def test_snapshot_rejects_duplicate_or_misaligned_timestamps() -> None:
    manifest = _manifest()
    spec = _spec(manifest)
    ticks = _ticks(spec)
    broken = (ticks[0], ticks[0], *ticks[2:])

    with pytest.raises(InvalidDataset, match="aligned"):
        build_snapshot(spec=spec, manifest=manifest, ticks=broken)


def test_snapshot_rejects_row_count_mismatch() -> None:
    manifest = _manifest()
    spec = _spec(manifest)

    with pytest.raises(InvalidDataset, match="count"):
        build_snapshot(spec=spec, manifest=manifest, ticks=_ticks(spec)[: spec.row_count - 1])


def test_snapshot_rejects_non_positive_quote() -> None:
    manifest = _manifest()
    spec = _spec(manifest)
    ticks = _ticks(spec)
    bad = (*ticks[:-1], Tick(epoch=ticks[-1].epoch, quote=Decimal("-1.0000")))

    with pytest.raises(InvalidDataset, match="positive"):
        build_snapshot(spec=spec, manifest=manifest, ticks=bad)


def test_serialize_dataset_is_deterministic_jsonl() -> None:
    snapshot = _snapshot()

    first = serialize_dataset(snapshot)
    second = serialize_dataset(snapshot)

    assert first == second
    assert first.endswith("\n")
    for line in first.strip().splitlines():
        payload = json.loads(line)
        assert isinstance(payload["epoch"], int)
        assert isinstance(payload["quote"], str)


def test_data_hash_covers_serialized_bytes() -> None:
    snapshot = _snapshot()

    assert snapshot.data_hash == sha256(serialize_dataset(snapshot).encode()).hexdigest()


def test_snapshot_is_immutable() -> None:
    snapshot = _snapshot()

    with pytest.raises(AttributeError):
        snapshot.data_hash = "x"  # type: ignore[misc]
