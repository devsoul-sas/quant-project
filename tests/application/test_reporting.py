"""Auditable partner evidence package tests."""

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from devsoul_quant.application.reporting import (
    InvalidResearchSpec,
    git_head_sha,
    git_is_dirty,
    parse_research_spec,
    render_summary,
    run_research,
    write_evidence_package,
)
from devsoul_quant.domain.datasets import GENERATOR_VERSION, SCHEMA_VERSION
from devsoul_quant.domain.features import FEATURE_SET_NAME, FEATURE_SET_VERSION

_SPEC: dict[str, object] = {
    "seed": 42,
    "duration": 3,
    "dataset": {
        "generator_version": "synthetic-random-walk-v1",
        "start_epoch": 1700000000,
        "interval": 1,
        "row_count": 40,
        "schema_version": "1",
    },
    "features": {
        "name": "momentum-baseline",
        "version": "1",
        "lag_windows": [1, 3],
        "rolling_window": 3,
    },
    "split": {
        "lookback_ticks": 3,
        "purge_ticks": 3,
        "embargo_ticks": 2,
        "test_ticks": 10,
        "fold_count": 2,
        "holdout_ticks": 5,
    },
}

_FORBIDDEN = ("profitable", "expected profit", "ROI", "rentab", "ganancia", "return on investment")


def _report() -> dict[str, Any]:
    return run_research(spec=parse_research_spec(_SPEC), git_sha="f" * 40)


def test_report_is_deterministic() -> None:
    first = json.dumps(_report(), sort_keys=True)
    second = json.dumps(_report(), sort_keys=True)

    assert first == second


def test_report_contains_four_states() -> None:
    report = _report()

    assert report["profitability_claim"] is False
    assert set(report["states"].keys()) == {
        "engineering_readiness",
        "scientific_evidence",
        "provider_license_blockers",
        "real_money_exclusion",
    }
    assert report["states"]["engineering_readiness"]["status"] == "READY"
    assert report["states"]["scientific_evidence"]["status"] == "NON_ECONOMIC"
    assert report["states"]["real_money_exclusion"]["status"] == "EXCLUDED"


def test_report_contains_reproduction_command_and_git_sha() -> None:
    report = _report()

    assert report["git_sha"] == "f" * 40
    assert "devsoul-quant research synthetic" in report["reproduction_command"]


def test_report_contains_no_absolute_local_paths() -> None:
    report_json = json.dumps(_report(), sort_keys=True)

    assert str(Path.cwd()) not in report_json
    assert "/home/" not in report_json
    assert ".." not in report_json


def test_report_contains_no_secrets() -> None:
    report_json = json.dumps(_report(), sort_keys=True)

    for pattern in ("password", "api_key", "postgresql://", "PRIVATE KEY", "Bearer "):
        assert pattern not in report_json


def test_summary_has_no_forbidden_profitability_language() -> None:
    summary = render_summary(_report())

    for phrase in _FORBIDDEN:
        assert phrase not in summary


def test_report_has_no_forbidden_profitability_language() -> None:
    report_json = json.dumps(_report(), sort_keys=True)

    for phrase in _FORBIDDEN:
        assert phrase not in report_json


def test_write_refuses_existing_output_directory(tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()

    with pytest.raises(FileExistsError):
        write_evidence_package(_report(), output)


def test_manifest_lists_files_with_correct_hashes(tmp_path: Path) -> None:
    output = tmp_path / "out"

    write_evidence_package(_report(), output)

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    names = {entry["name"] for entry in manifest["files"]}
    assert names == {"run-report.json", "run-summary.md"}
    for entry in manifest["files"]:
        content = (output / entry["name"]).read_bytes()
        assert entry["size"] == len(content)
        assert entry["sha256"] == sha256(content).hexdigest()


def test_package_is_byte_identical_across_directories(tmp_path: Path) -> None:
    report = _report()

    write_evidence_package(report, tmp_path / "a")
    write_evidence_package(report, tmp_path / "b")

    for name in ("run-report.json", "run-summary.md", "manifest.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_git_helpers_work_in_this_repo() -> None:
    sha = git_head_sha()
    assert sha and all(character in "0123456789abcdef" for character in sha)
    assert isinstance(git_is_dirty(), bool)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda s: s.update({"seed": "not-an-int"}),
        lambda s: s.update({"duration": 0}),
        lambda s: s["dataset"].pop("row_count"),
        lambda s: s["features"].update({"lag_windows": "1,3"}),
        lambda s: s.pop("split"),
    ],
)
def test_parse_research_spec_rejects_malformed(mutator: object) -> None:
    import copy

    data = copy.deepcopy(_SPEC)
    mutator(data)  # type: ignore[operator]

    with pytest.raises(InvalidResearchSpec):
        parse_research_spec(data)


def test_parse_research_spec_rejects_unknown_generator_version() -> None:
    import copy

    data = copy.deepcopy(_SPEC)
    data["dataset"]["generator_version"] = "made-up-v999"

    with pytest.raises(InvalidResearchSpec, match="generator_version"):
        parse_research_spec(data)


def test_parse_research_spec_rejects_unknown_feature_set_version() -> None:
    import copy

    data = copy.deepcopy(_SPEC)
    data["features"]["version"] = "made-up-v999"

    with pytest.raises(InvalidResearchSpec, match="version"):
        parse_research_spec(data)


def test_parse_research_spec_accepts_implemented_versions() -> None:
    spec = parse_research_spec(_SPEC)

    assert spec.dataset.generator_version == GENERATOR_VERSION
    assert spec.dataset.schema_version == SCHEMA_VERSION
    assert spec.feature_set.name == FEATURE_SET_NAME
    assert spec.feature_set.version == FEATURE_SET_VERSION
