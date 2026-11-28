"""Regression coverage for autonomous shell exit-code propagation."""

import subprocess
from pathlib import Path

_WRAPPER = Path(__file__).parents[1] / "scripts" / "run-autonomous.sh"


def test_autonomous_wrapper_propagates_child_failure() -> None:
    result = subprocess.run(
        [str(_WRAPPER), "python3", "-c", "raise SystemExit(17)"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 17
    assert "AUTONOMOUS_EXIT=17" in result.stderr


def test_autonomous_wrapper_propagates_success() -> None:
    result = subprocess.run(
        [str(_WRAPPER), "python3", "-c", "raise SystemExit(0)"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "AUTONOMOUS_EXIT=0" in result.stderr
