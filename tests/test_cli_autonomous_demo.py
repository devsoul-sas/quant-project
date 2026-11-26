"""CLI coverage for the bounded autonomous demo runner."""

from decimal import Decimal
from io import StringIO

import pytest

from devsoul_quant.application.adaptive_shadow import (
    AdaptiveEvaluationSnapshot,
    AdaptiveModelMetrics,
)
from devsoul_quant.application.autonomous_demo import (
    AutonomousDemoResult,
    AutonomousDemoSnapshot,
    EconomicMetrics,
)
from devsoul_quant.cli import main
from devsoul_quant.domain.execution_mode import ExecutionMode


def _snapshot(
    adaptive: AdaptiveEvaluationSnapshot | None = None,
) -> AutonomousDemoSnapshot:
    economics = EconomicMetrics(
        decisions=2,
        abstentions=0,
        abstention_frequency=Decimal("0"),
        wins=1,
        losses=1,
        stakes=Decimal("2"),
        effective_net_payout=Decimal("0.8"),
        break_even=Decimal("0.5555555555555555555555555556"),
        estimated_probability=Decimal("0.5"),
        estimated_value=Decimal("-0.1"),
        gross_profit=Decimal("0.8"),
        gross_loss=Decimal("1"),
        net_profit=Decimal("-0.2"),
        profit_factor=Decimal("0.8"),
        roi_on_stakes=Decimal("-0.1"),
        by_contract_type=(),
    )
    return AutonomousDemoSnapshot(
        connection_state="DISCONNECTED",
        instrument="R_10",
        strategy="CONTROLLED_RANDOM",
        ticks_processed=30,
        signal="DIGITEVEN",
        virtual_balance=Decimal("-0.20"),
        open_contracts=0,
        settled_contracts=2,
        quotes_consulted=2,
        profit_loss=Decimal("-0.20"),
        win_rate=Decimal("0.5"),
        break_even=Decimal("0.55"),
        drawdown=Decimal("1.00"),
        risk_state="PASS",
        elapsed_seconds=Decimal("60"),
        abstention_reasons=("CONTRACT_LIMIT_REACHED",),
        experimental_budget=Decimal("2"),
        budget_used=Decimal("2"),
        budget_remaining=Decimal("0"),
        economics=economics,
        adaptive=adaptive,
    )


def _adaptive_snapshot() -> AdaptiveEvaluationSnapshot:
    metrics = AdaptiveModelMetrics(
        model="LOGISTIC",
        observations=1200,
        brier_score=Decimal("0.24"),
        log_loss=Decimal("0.67"),
        accuracy=Decimal("0.53"),
        expected_calibration_error=Decimal("0.04"),
        quoted_opportunities=40,
        signals=4,
        signal_coverage=Decimal("0.1"),
        mean_break_even=Decimal("0.52"),
        mean_estimated_value=Decimal("0.01"),
    )
    return AdaptiveEvaluationSnapshot(
        resolved_labels=1320,
        evaluation_labels=1200,
        pending_labels=1,
        models=(metrics,),
    )


def test_autonomous_demo_requires_demo_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_TOKEN", raising=False)
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_APP_ID", raising=False)
    output = StringIO()

    code = main(
        [
            "autonomous-demo",
            "--mode",
            "OBSERVE_ONLY",
            "--symbol",
            "R_10",
            "--strategy",
            "MOMENTUM",
        ],
        stdout=output,
    )

    assert code == 2
    assert output.getvalue() == "error: demo credentials are not configured\n"


def test_autonomous_demo_emits_operational_snapshot_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "super-secret-token")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "secret-app")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_ACCOUNT", "secret-account")
    captured: dict[str, object] = {}
    status = _snapshot()

    def fake_run_autonomous_demo(**kwargs: object) -> AutonomousDemoResult:
        captured.update(kwargs)
        kwargs["emit"](status)  # type: ignore[operator]
        return AutonomousDemoResult("INTEGRATION_TEST", status)

    monkeypatch.setattr("devsoul_quant.cli.run_autonomous_demo", fake_run_autonomous_demo)
    output = StringIO()

    code = main(
        [
            "autonomous-demo",
            "--mode",
            "DEMO_INTEGRATION",
            "--symbol",
            "R_10",
            "--strategy",
            "CONTROLLED_RANDOM",
            "--session-seconds",
            "60",
            "--ticks-per-cycle",
            "30",
            "--maximum-cycles",
            "2",
            "--maximum-contracts",
            "2",
            "--arm-demo",
        ],
        stdout=output,
    )

    assert code == 0
    config = captured["config"]
    assert config.mode is ExecutionMode.DEMO_INTEGRATION  # type: ignore[union-attr]
    assert config.armed is True  # type: ignore[union-attr]
    rendered = output.getvalue()
    for field in (
        "connection_state",
        "instrument",
        "strategy",
        "ticks_processed",
        "signal",
        "virtual_balance",
        "open_contracts",
        "settled_contracts",
        "profit_loss",
        "win_rate",
        "break_even",
        "drawdown",
        "risk_state",
        "elapsed_seconds",
        "abstention_reasons",
    ):
        assert f'"{field}"' in rendered
    assert '"classification": "INTEGRATION_TEST"' in rendered
    assert "secret" not in rendered


def test_autonomous_demo_accepts_frozen_s37_virtual_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "demo-token")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "demo-app")
    captured: dict[str, object] = {}

    def fake_run_autonomous_demo(**kwargs: object) -> AutonomousDemoResult:
        captured.update(kwargs)
        return AutonomousDemoResult("DEMO_EXPLORATORY", _snapshot())

    monkeypatch.setattr("devsoul_quant.cli.run_autonomous_demo", fake_run_autonomous_demo)

    code = main(
        [
            "autonomous-demo",
            "--mode",
            "DEMO_EXPLORATORY",
            "--symbol",
            "R_10",
            "--strategy",
            "CONTROLLED_RANDOM",
            "--stake",
            "1",
            "--experimental-budget",
            "100",
            "--maximum-contracts",
            "100",
            "--maximum-session-loss",
            "10",
            "--arm-demo",
        ],
        stdout=StringIO(),
    )

    assert code == 0
    config = captured["config"]
    assert config.experimental_budget == Decimal("100")  # type: ignore[union-attr]


def test_autonomous_demo_preserves_latest_safe_snapshot_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "demo-token")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "demo-app")

    def failing_run_autonomous_demo(**kwargs: object) -> AutonomousDemoResult:
        emit = kwargs["emit"]
        emit(_snapshot())  # type: ignore[operator]
        raise RuntimeError("authenticated-url-must-not-be-rendered")

    monkeypatch.setattr("devsoul_quant.cli.run_autonomous_demo", failing_run_autonomous_demo)
    stdout = StringIO()

    code = main(
        [
            "autonomous-demo",
            "--mode",
            "DEMO_EXPLORATORY",
            "--symbol",
            "R_10",
            "--strategy",
            "CONTROLLED_RANDOM",
        ],
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert code == 2
    assert '"type": "error"' in rendered
    assert '"net_profit": "-0.2"' in rendered
    assert "authenticated-url-must-not-be-rendered" not in rendered


def test_autonomous_demo_emits_adaptive_aggregate_metrics_without_model_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "demo-token")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "demo-app")
    status = _snapshot(_adaptive_snapshot())
    monkeypatch.setattr(
        "devsoul_quant.cli.run_autonomous_demo",
        lambda **kwargs: AutonomousDemoResult("SHADOW_ONLY", status),
    )
    output = StringIO()

    code = main(
        [
            "autonomous-demo",
            "--mode",
            "SHADOW_TRADING",
            "--symbol",
            "R_10",
            "--strategy",
            "ADAPTIVE_ENSEMBLE",
        ],
        stdout=output,
    )

    rendered = output.getvalue()
    assert code == 0
    assert '"evaluation_labels": 1200' in rendered
    assert '"brier_score": "0.24"' in rendered
    assert '"mean_estimated_value": "0.01"' in rendered
    assert "weights" not in rendered
    assert "means" not in rendered
