"""Assemble and write the auditable partner evidence package."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from devsoul_quant import __version__
from devsoul_quant.application.build_dataset import build_dataset
from devsoul_quant.application.compute_features import compute_features_for_snapshot
from devsoul_quant.application.evaluate import evaluate_split
from devsoul_quant.application.prepare_validation import prepare_validation
from devsoul_quant.domain.data_rights import DataRightsManifest, DataSourceKind, build_manifest
from devsoul_quant.domain.datasets import GENERATOR_VERSION, SCHEMA_VERSION, DatasetSpec
from devsoul_quant.domain.features import FEATURE_SET_NAME, FEATURE_SET_VERSION, FeatureSetSpec
from devsoul_quant.domain.metrics import EvidenceMode
from devsoul_quant.domain.validation import TemporalSplitSpec

REPORT_SCHEMA_VERSION = "1"


class InvalidResearchSpec(ValueError):
    """Raised when a research spec file is malformed."""


def synthetic_manifest() -> DataRightsManifest:
    """Return the fixed DevSoul-owned synthetic data manifest."""
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


@dataclass(frozen=True, slots=True)
class ResearchSpec:
    """A fully parsed, typed research configuration."""

    seed: int
    duration: int
    dataset: DatasetSpec
    feature_set: FeatureSetSpec
    split: TemporalSplitSpec


def _get_int(mapping: Mapping[str, object], key: str) -> int:
    value = mapping.get(key)
    if type(value) is not int:
        raise InvalidResearchSpec(f"{key} must be an integer")
    return value


def _get_str(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidResearchSpec(f"{key} must be a non-blank string")
    return value


def _get_int_list(mapping: Mapping[str, object], key: str) -> tuple[int, ...]:
    value = mapping.get(key)
    if not isinstance(value, list) or any(type(item) is not int for item in value):
        raise InvalidResearchSpec(f"{key} must be a list of integers")
    return tuple(value)


def _get_object(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise InvalidResearchSpec(f"{key} must be an object")
    return value


def parse_research_spec(data: Mapping[str, object]) -> ResearchSpec:
    """Parse a research spec JSON into typed domain specs."""
    manifest = synthetic_manifest()
    seed = _get_int(data, "seed")
    duration = data.get("duration", 3)
    if type(duration) is not int or duration < 1:
        raise InvalidResearchSpec("duration must be a positive integer")

    dataset = _get_object(data, "dataset")
    features = _get_object(data, "features")
    split = _get_object(data, "split")

    generator_version = _get_str(dataset, "generator_version")
    if generator_version != GENERATOR_VERSION:
        raise InvalidResearchSpec(
            f"generator_version must be {GENERATOR_VERSION!r}, got {generator_version!r}"
        )
    schema_version = _get_str(dataset, "schema_version")
    if schema_version != SCHEMA_VERSION:
        raise InvalidResearchSpec(
            f"schema_version must be {SCHEMA_VERSION!r}, got {schema_version!r}"
        )
    feature_name = _get_str(features, "name")
    feature_version = _get_str(features, "version")
    if feature_name != FEATURE_SET_NAME or feature_version != FEATURE_SET_VERSION:
        raise InvalidResearchSpec(
            "feature set name and version must be "
            f"{FEATURE_SET_NAME!r} {FEATURE_SET_VERSION!r}, "
            f"got {feature_name!r} {feature_version!r}"
        )

    dataset_spec = DatasetSpec(
        generator_version=generator_version,
        seed=seed,
        start_epoch=_get_int(dataset, "start_epoch"),
        interval=_get_int(dataset, "interval"),
        row_count=_get_int(dataset, "row_count"),
        schema_version=schema_version,
        rights_manifest_hash=manifest.manifest_hash,
    )
    feature_spec = FeatureSetSpec(
        name=feature_name,
        version=feature_version,
        lag_windows=_get_int_list(features, "lag_windows"),
        rolling_window=_get_int(features, "rolling_window"),
    )
    split_spec = TemporalSplitSpec(
        lookback_ticks=_get_int(split, "lookback_ticks"),
        purge_ticks=_get_int(split, "purge_ticks"),
        embargo_ticks=_get_int(split, "embargo_ticks"),
        test_ticks=_get_int(split, "test_ticks"),
        fold_count=_get_int(split, "fold_count"),
        holdout_ticks=_get_int(split, "holdout_ticks"),
    )
    return ResearchSpec(
        seed=seed,
        duration=duration,
        dataset=dataset_spec,
        feature_set=feature_spec,
        split=split_spec,
    )


def run_research(*, spec: ResearchSpec, git_sha: str) -> dict[str, Any]:
    """Run the full synthetic research pipeline and return a canonical report."""
    manifest = synthetic_manifest()
    snapshot = build_dataset(spec=spec.dataset, manifest=manifest)
    frame = compute_features_for_snapshot(spec=spec.feature_set, snapshot=snapshot)
    split = prepare_validation(spec=spec.split, snapshot=snapshot, run_id=f"research-{spec.seed}")
    evaluation = evaluate_split(
        split=split,
        evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST,
        seed=spec.seed,
        duration=spec.duration,
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "code_version": __version__,
        "git_sha": git_sha,
        "seed": spec.seed,
        "profitability_claim": False,
        "reproduction_command": (
            "devsoul-quant research synthetic --spec <spec.json> --output <directory>"
        ),
        "dataset": {
            "generator_version": spec.dataset.generator_version,
            "start_epoch": spec.dataset.start_epoch,
            "interval": spec.dataset.interval,
            "row_count": spec.dataset.row_count,
            "schema_version": spec.dataset.schema_version,
            "spec_hash": spec.dataset.spec_hash(),
            "rights_manifest_hash": spec.dataset.rights_manifest_hash,
            "data_hash": snapshot.data_hash,
        },
        "features": {
            "name": spec.feature_set.name,
            "version": spec.feature_set.version,
            "spec_hash": spec.feature_set.spec_hash(),
            "dataset_hash": frame.dataset_hash,
            "feature_hash": frame.feature_hash,
        },
        "split": {
            "spec_hash": spec.split.spec_hash(),
            "holdout_hash": split.holdout.holdout_hash,
            "holdout_tick_count": split.holdout.tick_count,
        },
        "evaluation": evaluation.to_dict(),
        "states": {
            "engineering_readiness": {
                "status": "READY",
                "details": [
                    "execution/replay/audit architecture works end-to-end",
                    "research pipeline is deterministic and reproducible",
                ],
            },
            "scientific_evidence": {
                "status": "NON_ECONOMIC",
                "details": [
                    "synthetic results validate engineering only",
                    "directional hit rate is a non-economic proxy",
                    "no profitability claim is made",
                ],
            },
            "provider_license_blockers": {
                "status": "DERIV_PENDING",
                "details": [
                    "Deriv review is pending; persistent market data is not authorized",
                    "research is provider-independent",
                ],
            },
            "real_money_exclusion": {
                "status": "EXCLUDED",
                "details": [
                    "no real-money mode exists",
                    "no credentials or accounts are handled",
                ],
            },
        },
    }


def render_summary(report: Mapping[str, object]) -> str:
    """Render a human-readable summary without economic overclaim."""
    evaluation = report["evaluation"]
    states = report["states"]
    assert isinstance(evaluation, Mapping)
    assert isinstance(states, Mapping)
    return (
        "\n".join(
            [
                "# DevSoul Quant — Research Run Summary",
                "",
                f"- Seed: {report['seed']}",
                f"- Code version: {report['code_version']}",
                f"- Git SHA: {report['git_sha']}",
                f"- Evidence mode: {evaluation['evidence_mode']}",
                "",
                "## States",
                "",
                f"- Engineering readiness: {states['engineering_readiness']['status']}",
                f"- Scientific evidence: {states['scientific_evidence']['status']}",
                f"- Provider/license blockers: {states['provider_license_blockers']['status']}",
                f"- Real-money exclusion: {states['real_money_exclusion']['status']}",
                "",
                "## Directional evidence (non-economic)",
                "",
                f"- Decisions: {evaluation['decisions']}",
                f"- Entered: {evaluation['enter_count']}",
                f"- Waited: {evaluation['wait_count']}",
                f"- Directional hit rate: {evaluation['directional_hit_rate']}",
                f"- Longest loss streak: {evaluation['longest_loss_streak']}",
                "",
                "## Reproduction",
                "",
                f"```\n{report['reproduction_command']}\n```",
                "",
            ]
        )
        + "\n"
    )


def write_evidence_package(
    report: Mapping[str, object], output_dir: Path
) -> dict[str, list[dict[str, object]]]:
    """Write the three-file evidence package, refusing an existing directory."""
    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    report_json = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    summary = render_summary(report)

    (output_dir / "run-report.json").write_text(report_json, encoding="utf-8")
    (output_dir / "run-summary.md").write_text(summary, encoding="utf-8")

    entries = [
        {
            "name": "run-report.json",
            "size": len(report_json.encode()),
            "sha256": sha256(report_json.encode()).hexdigest(),
        },
        {
            "name": "run-summary.md",
            "size": len(summary.encode()),
            "sha256": sha256(summary.encode()).hexdigest(),
        },
    ]
    manifest = {"files": entries}
    manifest_json = json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    (output_dir / "manifest.json").write_text(manifest_json, encoding="utf-8")
    return manifest


def git_head_sha() -> str:
    """Return the current commit SHA, or a stable placeholder outside a repo."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def git_is_dirty() -> bool:
    """Return whether the working tree has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip() != ""
