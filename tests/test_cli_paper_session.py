"""CLI tests for the ephemeral paper-only Deriv demo session."""

import json
from io import StringIO

import pytest

from devsoul_quant.cli import main


def _fake_result(strategy: str) -> object:
    from devsoul_quant.application.research_runner import EphemeralRunResult
    from devsoul_quant.domain.strategy_release import ResearchConclusion, StrategyFamily

    family = StrategyFamily.EVEN_ODD if strategy == "even-odd" else StrategyFamily.MULTIPLIER
    return EphemeralRunResult(
        family=family,
        release_id="d" * 64,
        conclusion=ResearchConclusion.NO_EDGE,
        forward_iterations=20,
        entries=0,
        no_trade=20,
    )


def test_paper_session_requires_explicit_confirmation() -> None:
    output = StringIO()

    exit_code = main(["paper-session", "--strategy", "even-odd", "--symbol", "R_10"], stdout=output)

    assert exit_code == 2
    assert (
        output.getvalue() == "error: pass --confirm-paper-only to run one ephemeral paper session\n"
    )


def test_paper_session_requires_environment_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_TOKEN", raising=False)
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_APP_ID", raising=False)
    output = StringIO()

    exit_code = main(
        ["paper-session", "--strategy", "even-odd", "--symbol", "R_10", "--confirm-paper-only"],
        stdout=output,
    )

    assert exit_code == 2
    assert output.getvalue() == "error: demo credentials are not configured\n"


def test_paper_session_even_odd_requires_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "t")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "a")
    output = StringIO()

    exit_code = main(
        ["paper-session", "--strategy", "even-odd", "--confirm-paper-only"], stdout=output
    )

    assert exit_code == 2
    assert "symbol" in output.getvalue()


def test_paper_session_even_odd_prints_only_a_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "super-secret-token")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "secret-app-id")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_ACCOUNT", "secret-account")
    captured: dict[str, object] = {}

    def fake_run_even_odd_session(**kwargs: object) -> object:
        captured.update(kwargs)
        return _fake_result("even-odd")

    monkeypatch.setattr("devsoul_quant.cli.run_even_odd_session", fake_run_even_odd_session)
    output = StringIO()

    exit_code = main(
        [
            "paper-session",
            "--strategy",
            "even-odd",
            "--symbol",
            "R_10",
            "--confirm-paper-only",
        ],
        stdout=output,
    )

    assert exit_code == 0
    payload = json.loads(output.getvalue())
    assert payload["conclusion"] == "NO_EDGE"
    assert payload["strategy"] == "EVEN_ODD"
    assert payload["forward_iterations"] == 20
    assert "super-secret-token" not in output.getvalue()
    assert "secret-app-id" not in output.getvalue()
    assert "secret-account" not in output.getvalue()
    assert "wss://" not in output.getvalue()
    assert "otp" not in output.getvalue().lower()
    assert "profit" not in output.getvalue().lower()
    assert "tick" not in output.getvalue().lower()


def test_paper_session_multiplier_dispatches_to_multiplier_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "t")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "a")
    captured: dict[str, object] = {}

    def fake_run_multiplier_session(**kwargs: object) -> object:
        captured.update(kwargs)
        return _fake_result("multiplier")

    monkeypatch.setattr("devsoul_quant.cli.run_multiplier_session", fake_run_multiplier_session)
    output = StringIO()

    exit_code = main(
        [
            "paper-session",
            "--strategy",
            "multiplier",
            "--fallback-symbol",
            "R_10",
            "--confirm-paper-only",
        ],
        stdout=output,
    )

    assert exit_code == 0
    payload = json.loads(output.getvalue())
    assert payload["strategy"] == "MULTIPLIER"
    assert payload["conclusion"] == "NO_EDGE"
    assert captured["fallback_symbol"] == "R_10"


def test_paper_session_output_does_not_leak_provider_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "t")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "a")

    def fake_run_even_odd_session(**kwargs: object) -> object:
        return _fake_result("even-odd")

    monkeypatch.setattr("devsoul_quant.cli.run_even_odd_session", fake_run_even_odd_session)
    output = StringIO()

    main(
        ["paper-session", "--strategy", "even-odd", "--symbol", "R_10", "--confirm-paper-only"],
        stdout=output,
    )

    assert "price" not in output.getvalue().lower()
    assert "payout" not in output.getvalue().lower()
    assert "quote" not in output.getvalue().lower()
    assert "contract" not in output.getvalue().lower()
