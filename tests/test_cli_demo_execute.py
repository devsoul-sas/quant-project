"""CLI tests for one explicitly armed, output-minimized demo contract."""

from io import StringIO

import pytest

from devsoul_quant.application.demo_session import DemoSessionReceipt
from devsoul_quant.cli import main


def test_demo_execute_requires_explicit_demo_confirmation() -> None:
    output = StringIO()

    exit_code = main(["demo-execute", "--symbol", "R_100"], stdout=output)

    assert exit_code == 2
    assert output.getvalue() == "error: pass --confirm-demo-only to arm one demo contract\n"


def test_demo_execute_requires_environment_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_TOKEN", raising=False)
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_APP_ID", raising=False)
    output = StringIO()

    exit_code = main(["demo-execute", "--symbol", "R_100", "--confirm-demo-only"], stdout=output)

    assert exit_code == 2
    assert output.getvalue() == "error: demo credentials are not configured\n"


def test_demo_execute_prints_only_a_generic_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "super-secret-token")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "secret-app-id")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_ACCOUNT", "secret-account")
    captured: dict[str, object] = {}

    def fake_run_demo_session(**kwargs: object) -> DemoSessionReceipt:
        captured.update(kwargs)
        return DemoSessionReceipt()

    monkeypatch.setattr("devsoul_quant.cli.run_demo_session", fake_run_demo_session)
    output = StringIO()

    exit_code = main(
        [
            "demo-execute",
            "--symbol",
            "R_100",
            "--stake",
            "1.00",
            "--minimum-net-payout-ratio",
            "0.75",
            "--maximum-session-loss",
            "1.00",
            "--confirm-demo-only",
        ],
        stdout=output,
    )

    assert exit_code == 0
    assert output.getvalue() == "demo session completed; inspect the provider demo account\n"
    limits = captured["limits"]
    assert limits.kill_switch_enabled is False  # type: ignore[union-attr]
    assert "secret" not in output.getvalue()
    assert "contract" not in output.getvalue().lower()
