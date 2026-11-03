"""CLI research synthetic command tests."""

import json
from io import StringIO
from pathlib import Path

import pytest

from devsoul_quant.cli import main

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


def _write_spec(tmp_path: Path) -> Path:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_SPEC), encoding="utf-8")
    return spec_path


def test_research_synthetic_cli_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("devsoul_quant.cli.git_is_dirty", lambda: False)
    monkeypatch.setattr("devsoul_quant.cli.git_head_sha", lambda: "a" * 40)
    spec_path = _write_spec(tmp_path)
    output = StringIO()

    exit_code = main(
        ["research", "synthetic", "--spec", str(spec_path), "--output", str(tmp_path / "out")],
        stdout=output,
    )

    assert exit_code == 0
    assert (tmp_path / "out" / "run-report.json").exists()
    assert (tmp_path / "out" / "run-summary.md").exists()
    assert (tmp_path / "out" / "manifest.json").exists()


def test_research_synthetic_cli_fails_on_missing_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("devsoul_quant.cli.git_is_dirty", lambda: False)
    monkeypatch.setattr("devsoul_quant.cli.git_head_sha", lambda: "a" * 40)
    output = StringIO()

    exit_code = main(
        [
            "research",
            "synthetic",
            "--spec",
            str(tmp_path / "nope.json"),
            "--output",
            str(tmp_path / "out"),
        ],
        stdout=output,
    )

    assert exit_code == 2
    assert "error:" in output.getvalue()


def test_research_synthetic_cli_fails_on_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("devsoul_quant.cli.git_is_dirty", lambda: False)
    monkeypatch.setattr("devsoul_quant.cli.git_head_sha", lambda: "a" * 40)
    spec_path = _write_spec(tmp_path)
    (tmp_path / "out").mkdir()
    output = StringIO()

    exit_code = main(
        ["research", "synthetic", "--spec", str(spec_path), "--output", str(tmp_path / "out")],
        stdout=output,
    )

    assert exit_code == 2
    assert "already exists" in output.getvalue()


def test_research_synthetic_cli_fails_closed_on_dirty_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("devsoul_quant.cli.git_is_dirty", lambda: True)
    monkeypatch.setattr("devsoul_quant.cli.git_head_sha", lambda: "a" * 40)
    spec_path = _write_spec(tmp_path)
    output = StringIO()

    exit_code = main(
        ["research", "synthetic", "--spec", str(spec_path), "--output", str(tmp_path / "out")],
        stdout=output,
    )

    assert exit_code == 2
    assert "dirty" in output.getvalue()


def test_research_synthetic_rejects_allow_dirty_flag_as_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("devsoul_quant.cli.git_is_dirty", lambda: False)
    monkeypatch.setattr("devsoul_quant.cli.git_head_sha", lambda: "a" * 40)
    spec_path = _write_spec(tmp_path)
    output = StringIO()

    with pytest.raises(SystemExit):
        main(
            [
                "research",
                "synthetic",
                "--spec",
                str(spec_path),
                "--output",
                str(tmp_path / "out"),
                "--allow-dirty",
            ],
            stdout=output,
        )


def test_research_synthetic_cli_reports_git_state_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail() -> str:
        raise OSError("no git available")

    monkeypatch.setattr("devsoul_quant.cli.git_head_sha", fail)
    monkeypatch.setattr("devsoul_quant.cli.git_is_dirty", lambda: False)
    spec_path = _write_spec(tmp_path)
    output = StringIO()

    exit_code = main(
        ["research", "synthetic", "--spec", str(spec_path), "--output", str(tmp_path / "out")],
        stdout=output,
    )

    assert exit_code == 2
    assert "git state" in output.getvalue()
