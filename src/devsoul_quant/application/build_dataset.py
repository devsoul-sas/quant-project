"""Materialize deterministic synthetic dataset snapshots."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from devsoul_quant.domain.data_rights import (
    DataRightsManifest,
    PersistentUseDecision,
    decide_persistent_use,
)
from devsoul_quant.domain.datasets import (
    DatasetSnapshot,
    DatasetSpec,
    build_snapshot,
    serialize_dataset,
)
from devsoul_quant.domain.synthetic import generate_ticks


class UnapprovedDatasetSource(ValueError):
    """Raised when persistence is attempted on an unapproved source."""


def build_dataset(
    *,
    spec: DatasetSpec,
    manifest: DataRightsManifest,
    start_quote: Decimal = Decimal("100.0000"),
) -> DatasetSnapshot:
    """Generate and bind a snapshot only after the manifest is approved."""
    decision = decide_persistent_use(manifest, require_derived_artifacts=True)
    if decision.decision is not PersistentUseDecision.ALLOW:
        raise UnapprovedDatasetSource(
            "dataset source is not approved for persistence: " + ", ".join(decision.reasons)
        )
    ticks = generate_ticks(
        seed=spec.seed,
        count=spec.row_count,
        start_epoch=spec.start_epoch,
        interval=spec.interval,
        start_quote=start_quote,
    )
    return build_snapshot(spec=spec, manifest=manifest, ticks=ticks)


def write_snapshot(snapshot: DatasetSnapshot, directory: Path) -> Path:
    """Write the canonical data file and manifest, failing closed on unapproved sources."""
    decision = decide_persistent_use(snapshot.manifest, require_derived_artifacts=True)
    if decision.decision is not PersistentUseDecision.ALLOW:
        raise UnapprovedDatasetSource(
            "dataset source is not approved for persistence: " + ", ".join(decision.reasons)
        )
    directory.mkdir(parents=True, exist_ok=True)
    data_path = directory / "data.jsonl"
    data_path.write_text(serialize_dataset(snapshot), encoding="utf-8")
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(
        json.dumps(snapshot.manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return data_path
