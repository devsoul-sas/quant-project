"""Immutable synthetic dataset snapshots with full lineage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from devsoul_quant.domain.data_rights import DataRightsManifest, DataSourceKind
from devsoul_quant.domain.replay import Tick

GENERATOR_VERSION = "synthetic-random-walk-v1"
SCHEMA_VERSION = "1"

_HASH_CHARS = frozenset("0123456789abcdef")


class InvalidDataset(ValueError):
    """Raised when a dataset spec or snapshot violates invariants."""


def _require_non_blank(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidDataset(f"{field} must be a non-blank string")


def _require_hash(value: object, field: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HASH_CHARS for character in value)
    ):
        raise InvalidDataset(f"{field} must be a lowercase SHA-256 hash")


def _tick_json(tick: Tick) -> str:
    return json.dumps(
        {"epoch": tick.epoch, "quote": format(tick.quote, "f")},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    """Frozen recipe for one reproducible synthetic dataset."""

    generator_version: str
    seed: int
    start_epoch: int
    interval: int
    row_count: int
    schema_version: str
    rights_manifest_hash: str

    def __post_init__(self) -> None:
        _require_non_blank(self.generator_version, "generator_version")
        if type(self.seed) is not int:
            raise InvalidDataset("seed must be an integer")
        if type(self.start_epoch) is not int or self.start_epoch < 0:
            raise InvalidDataset("start_epoch must be a non-negative integer")
        if type(self.interval) is not int or self.interval < 1:
            raise InvalidDataset("interval must be a positive integer")
        if type(self.row_count) is not int or self.row_count < 2:
            raise InvalidDataset("row_count must be an integer of at least two")
        _require_non_blank(self.schema_version, "schema_version")
        _require_hash(self.rights_manifest_hash, "rights_manifest_hash")

    def spec_hash(self) -> str:
        """Return the canonical SHA-256 identity of this spec."""
        canonical = json.dumps(
            {
                "generator_version": self.generator_version,
                "interval": self.interval,
                "rights_manifest_hash": self.rights_manifest_hash,
                "row_count": self.row_count,
                "schema_version": self.schema_version,
                "seed": self.seed,
                "start_epoch": self.start_epoch,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class DatasetSnapshot:
    """Immutable dataset with a bound manifest and a data SHA-256."""

    spec: DatasetSpec
    manifest: DataRightsManifest
    ticks: tuple[Tick, ...]
    data_hash: str


def serialize_dataset(snapshot: DatasetSnapshot) -> str:
    """Return the canonical JSON Lines representation (never floats)."""
    return "\n".join(_tick_json(tick) for tick in snapshot.ticks) + "\n"


def hash_ticks(ticks: tuple[Tick, ...]) -> str:
    """Return the canonical SHA-256 of a tick sequence (epoch + fixed quote)."""
    canonical = "\n".join(_tick_json(tick) for tick in ticks) + "\n"
    return sha256(canonical.encode()).hexdigest()


def build_snapshot(
    *,
    spec: DatasetSpec,
    manifest: DataRightsManifest,
    ticks: tuple[Tick, ...],
) -> DatasetSnapshot:
    """Validate lineage, provenance, and ordering, then bind the data hash."""
    if manifest.source_kind is not DataSourceKind.DEVSOUL_SYNTHETIC:
        raise InvalidDataset("only DevSoul synthetic datasets may be snapshotted")
    if spec.rights_manifest_hash != manifest.manifest_hash:
        raise InvalidDataset("dataset rights manifest hash does not match the spec")
    if len(ticks) != spec.row_count:
        raise InvalidDataset("tick count does not match the dataset spec")
    for index, tick in enumerate(ticks):
        if tick.epoch != spec.start_epoch + index * spec.interval:
            raise InvalidDataset("tick epochs must be aligned to start_epoch and interval")
        if not tick.quote.is_finite() or tick.quote <= 0:
            raise InvalidDataset("tick quotes must be positive finite decimals")
    return DatasetSnapshot(
        spec=spec,
        manifest=manifest,
        ticks=ticks,
        data_hash=hash_ticks(ticks),
    )
