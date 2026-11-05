"""Fail-closed CLI tests for disabled Deriv-derived output."""

from io import StringIO

import pytest

from devsoul_quant.cli import main

DEMO_URL = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=secret-otp"
DISABLED = "error: Deriv-derived output is disabled outside the <24h ephemeral session\n"


@pytest.mark.parametrize("command", ["live-demo", "live-evaluate"])
def test_live_commands_are_disabled_before_authenticated_url_use(command: str) -> None:
    output = StringIO()

    exit_code = main([command, "--url", DEMO_URL, "--symbol", "R_100"], stdout=output)

    assert exit_code == 2
    assert output.getvalue() == DISABLED
    assert "secret-otp" not in output.getvalue()
    assert "wss://" not in output.getvalue()


@pytest.mark.parametrize("command", ["live-demo", "live-evaluate"])
def test_live_commands_are_disabled_before_otp_resolution(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "must-not-be-read")
    output = StringIO()

    exit_code = main([command, "--otp", "--symbol", "R_100"], stdout=output)

    assert exit_code == 2
    assert output.getvalue() == DISABLED
    assert "must-not-be-read" not in output.getvalue()


def test_live_demo_rejects_persistent_ledger_without_exposing_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DEVSOUL_QUANT_DATABASE_URL",
        "postgresql+psycopg://user:password@127.0.0.1:5434/devsoul_quant",
    )
    output = StringIO()

    exit_code = main(
        [
            "live-demo",
            "--url",
            DEMO_URL,
            "--symbol",
            "R_100",
            "--ledger-backend",
            "postgres",
            "--ledger-id",
            "forbidden-live-run",
        ],
        stdout=output,
    )

    assert exit_code == 2
    assert output.getvalue() == DISABLED
    assert "password" not in output.getvalue()


@pytest.mark.parametrize("command", ["live-demo", "live-evaluate"])
def test_live_commands_still_require_symbol_at_parse_boundary(command: str) -> None:
    with pytest.raises(SystemExit):
        main([command, "--url", DEMO_URL])
