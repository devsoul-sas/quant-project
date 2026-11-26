"""Autonomous demo runner behavior and safety boundaries."""

from collections.abc import Iterator
from dataclasses import replace
from decimal import Decimal
from itertools import chain, repeat

import pytest

from devsoul_quant.application.autonomous_demo import (
    AutonomousDemoConfig,
    DemoStrategy,
    InvalidAutonomousDemo,
    run_autonomous_demo,
)
from devsoul_quant.application.demo_execution import (
    DemoExecutionLimits,
    DemoProposal,
    DemoSettlement,
)
from devsoul_quant.domain.execution_mode import ExecutionMode
from devsoul_quant.domain.replay import Tick


def _ticks(start: int = 1) -> tuple[Tick, ...]:
    return (
        Tick(start, Decimal("100.00"), pip_size=2),
        Tick(start + 1, Decimal("100.01"), pip_size=2),
        Tick(start + 2, Decimal("100.02"), pip_size=2),
    )


def _limits(maximum_contracts: int = 2) -> DemoExecutionLimits:
    return DemoExecutionLimits(
        fixed_stake=Decimal("1"),
        minimum_net_payout_ratio=Decimal("0.50"),
        maximum_contracts=maximum_contracts,
        maximum_session_loss=Decimal("2"),
        kill_switch_enabled=False,
    )


class FakeGateway:
    account_type = "demo"

    def __init__(
        self,
        profits: Iterator[Decimal],
        *,
        available: frozenset[str] | None = None,
        fail_buy: bool = False,
    ) -> None:
        self.profits = profits
        self.calls: list[str] = []
        self.open_ids: list[str] = []
        self.intents: list[object] = []
        self.available = available or frozenset({"DIGITEVEN", "DIGITODD", "CALL", "PUT"})
        self.fail_buy = fail_buy

    def __enter__(self) -> "FakeGateway":
        self.calls.append("connect")
        return self

    def __exit__(self, *exc_info: object) -> bool:
        self.calls.append("disconnect")
        return False

    def available_contract_types(self, symbol: str) -> frozenset[str]:
        self.calls.append("discover")
        return self.available

    def propose(self, intent: object) -> DemoProposal:
        self.calls.append("propose")
        self.intents.append(intent)
        return DemoProposal(f"proposal-{len(self.intents)}", Decimal("1"), Decimal("1.80"))

    def buy(self, proposal: DemoProposal) -> str:
        self.calls.append("buy")
        if self.fail_buy:
            raise RuntimeError("provider result unknown")
        contract_id = f"contract-{len(self.open_ids) + 1}"
        self.open_ids.append(contract_id)
        return contract_id

    def await_settlement(self, contract_id: str) -> DemoSettlement:
        self.calls.append("settle")
        self.open_ids.remove(contract_id)
        return DemoSettlement(contract_id, next(self.profits))

    def reconcile(self) -> tuple[str, ...]:
        self.calls.append("reconcile")
        return tuple(self.open_ids)


class GatewayFactory:
    def __init__(self, gateway: FakeGateway) -> None:
        self.gateway = gateway
        self.urls: list[str] = []

    def __call__(self, url: str) -> FakeGateway:
        self.urls.append(url)
        return self.gateway


def test_observe_only_never_resolves_credentials_or_opens_a_gateway() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.OBSERVE_ONLY,
        symbol="R_10",
        strategy=DemoStrategy.MOMENTUM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=1,
    )
    gateway = FakeGateway(iter(()))

    result = run_autonomous_demo(
        config=config,
        limits=_limits(),
        collect_ticks=lambda symbol, count: _ticks(),
        resolve_url=lambda: (_ for _ in ()).throw(AssertionError("OTP must not be resolved")),
        gateway_factory=GatewayFactory(gateway),
    )

    assert result.final.ticks_processed == 3
    assert result.final.settled_contracts == 0
    assert result.final.signal == "NO_TRADE"
    assert gateway.calls == []


def test_shadow_trading_quotes_but_never_buys() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.SHADOW_TRADING,
        symbol="R_10",
        strategy=DemoStrategy.MOMENTUM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=1,
    )
    gateway = FakeGateway(iter(()))

    result = run_autonomous_demo(
        config=config,
        limits=_limits(),
        collect_ticks=lambda symbol, count: _ticks(),
        resolve_url=lambda: "wss://demo.invalid/otp",
        gateway_factory=GatewayFactory(gateway),
    )

    assert result.final.quotes_consulted == 1
    assert result.final.settled_contracts == 0
    assert result.final.break_even == Decimal("0.5555555555555555555555555556")
    assert "buy" not in gateway.calls


def test_adaptive_shadow_scores_ticks_quotes_both_directions_and_never_buys() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.SHADOW_TRADING,
        symbol="R_10",
        strategy=DemoStrategy.ADAPTIVE_ENSEMBLE,
        session_seconds=60,
        ticks_per_cycle=130,
        contract_duration=1,
        maximum_cycles=1,
        seed=38,
    )
    ticks = tuple(
        Tick(index, Decimal("100") + Decimal(index) / Decimal("100"), pip_size=2)
        for index in range(1, 131)
    )
    gateway = FakeGateway(iter(()))

    result = run_autonomous_demo(
        config=config,
        limits=_limits(),
        collect_ticks=lambda symbol, count: ticks,
        resolve_url=lambda: "wss://demo.invalid/otp",
        gateway_factory=GatewayFactory(gateway),
    )

    assert result.final.adaptive is not None
    assert result.final.adaptive.resolved_labels == 124
    assert result.final.adaptive.evaluation_labels == 4
    assert result.final.adaptive.decision == "INSUFFICIENT_EVIDENCE"
    assert result.final.adaptive.decision_reasons == ("EVALUATION_SAMPLE_BELOW_1200",)
    assert result.final.quotes_consulted == 2
    assert gateway.calls.count("propose") == 2
    assert "buy" not in gateway.calls
    assert result.final.settled_contracts == 0


def test_demo_integration_executes_at_most_two_sequential_contracts_and_reconciles() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.DEMO_INTEGRATION,
        symbol="R_10",
        strategy=DemoStrategy.CONTROLLED_RANDOM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=3,
        seed=7,
        armed=True,
    )
    gateway = FakeGateway(iter((Decimal("0.80"), Decimal("-1.00"))))
    factory = GatewayFactory(gateway)
    otp_counter = iter(range(10))
    batch_starts = iter((1, 4, 7))

    result = run_autonomous_demo(
        config=config,
        limits=_limits(maximum_contracts=2),
        collect_ticks=lambda symbol, count: _ticks(next(batch_starts)),
        resolve_url=lambda: f"wss://demo.invalid/{next(otp_counter)}",
        gateway_factory=factory,
    )

    assert result.classification == "INTEGRATION_TEST"
    assert result.final.settled_contracts == 2
    assert result.final.open_contracts == 0
    assert result.final.profit_loss == Decimal("-0.20")
    assert result.final.win_rate == Decimal("0.5")
    assert result.final.drawdown == Decimal("1.00")
    assert result.final.risk_state == "PASS"
    assert gateway.calls.count("buy") == 2
    assert gateway.calls.count("settle") == 2
    assert gateway.calls[-2:] == ["reconcile", "disconnect"]


def test_demo_mode_remains_no_trade_when_not_explicitly_armed() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.DEMO_EXPLORATORY,
        symbol="R_10",
        strategy=DemoStrategy.MOMENTUM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=1,
        armed=False,
    )
    gateway = FakeGateway(iter(()))

    result = run_autonomous_demo(
        config=config,
        limits=_limits(),
        collect_ticks=lambda symbol, count: _ticks(),
        resolve_url=lambda: "wss://demo.invalid/otp",
        gateway_factory=GatewayFactory(gateway),
    )

    assert result.final.signal == "NO_TRADE"
    assert "DEMO_EXECUTION_NOT_ARMED" in result.final.abstention_reasons
    assert gateway.calls == []


@pytest.mark.parametrize(
    "changes",
    (
        {"mode": ExecutionMode.SYNTHETIC_BACKTEST},
        {"symbol": " "},
        {"strategy": "MOMENTUM"},
        {"session_seconds": 0},
        {"ticks_per_cycle": 0},
        {"contract_duration": 0},
        {"maximum_cycles": 0},
        {"session_seconds": 86_400},
        {"ticks_per_cycle": 10_001},
        {"seed": True},
        {"armed": 1},
    ),
)
def test_autonomous_config_rejects_unsafe_or_ambiguous_values(changes: dict[str, object]) -> None:
    base = AutonomousDemoConfig(
        mode=ExecutionMode.OBSERVE_ONLY,
        symbol="R_10",
        strategy=DemoStrategy.MOMENTUM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=1,
    )

    with pytest.raises(InvalidAutonomousDemo):
        replace(base, **changes)  # type: ignore[arg-type]


def test_even_odd_shadow_characterizes_quotes_but_abstains_without_evidence() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.SHADOW_TRADING,
        symbol="R_10",
        strategy=DemoStrategy.EVEN_ODD,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=1,
    )
    gateway = FakeGateway(iter(()))

    result = run_autonomous_demo(
        config=config,
        limits=_limits(),
        collect_ticks=lambda symbol, count: _ticks(),
        resolve_url=lambda: "wss://demo.invalid/otp",
        gateway_factory=GatewayFactory(gateway),
    )

    assert result.final.signal == "NO_TRADE"
    assert result.final.quotes_consulted == 2
    assert gateway.calls.count("propose") == 2
    assert "buy" not in gateway.calls


def test_even_odd_abstains_when_contract_family_is_unavailable() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.SHADOW_TRADING,
        symbol="R_10",
        strategy=DemoStrategy.EVEN_ODD,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=1,
    )
    gateway = FakeGateway(iter(()), available=frozenset({"CALL", "PUT"}))

    result = run_autonomous_demo(
        config=config,
        limits=_limits(),
        collect_ticks=lambda symbol, count: _ticks(),
        resolve_url=lambda: "wss://demo.invalid/otp",
        gateway_factory=GatewayFactory(gateway),
    )

    assert "Even/Odd contracts are unavailable" in result.final.abstention_reasons
    assert gateway.calls.count("propose") == 0


def test_observation_stops_on_duration_empty_source_or_duplicate_ticks() -> None:
    base = AutonomousDemoConfig(
        mode=ExecutionMode.OBSERVE_ONLY,
        symbol="R_10",
        strategy=DemoStrategy.MOMENTUM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=2,
    )
    gateway_factory = GatewayFactory(FakeGateway(iter(())))

    duration_clock = iter(chain((0.0, 60.0), repeat(60.0)))
    duration = run_autonomous_demo(
        config=base,
        limits=_limits(),
        collect_ticks=lambda symbol, count: _ticks(),
        resolve_url=lambda: "unused",
        gateway_factory=gateway_factory,
        monotonic=lambda: next(duration_clock),
    )
    empty = run_autonomous_demo(
        config=base,
        limits=_limits(),
        collect_ticks=lambda symbol, count: (),
        resolve_url=lambda: "unused",
        gateway_factory=gateway_factory,
    )
    duplicate = run_autonomous_demo(
        config=base,
        limits=_limits(),
        collect_ticks=lambda symbol, count: _ticks(),
        resolve_url=lambda: "unused",
        gateway_factory=gateway_factory,
    )

    assert "SESSION_DURATION_REACHED" in duration.final.abstention_reasons
    assert "TICK_SOURCE_EXHAUSTED" in empty.final.abstention_reasons
    assert "NO_STRICTLY_NEW_TICKS" in duplicate.final.abstention_reasons


def test_demo_stops_at_loss_limit_and_reconciles() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.DEMO_EXPLORATORY,
        symbol="R_10",
        strategy=DemoStrategy.CONTROLLED_RANDOM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=2,
        armed=True,
    )
    gateway = FakeGateway(iter((Decimal("-1"),)))
    limits = DemoExecutionLimits(
        fixed_stake=Decimal("1"),
        minimum_net_payout_ratio=Decimal("0.50"),
        maximum_contracts=2,
        maximum_session_loss=Decimal("1"),
        kill_switch_enabled=False,
    )

    result = run_autonomous_demo(
        config=config,
        limits=limits,
        collect_ticks=lambda symbol, count: _ticks(),
        resolve_url=lambda: "wss://demo.invalid/otp",
        gateway_factory=GatewayFactory(gateway),
    )

    assert result.classification == "DEMO_EXPLORATORY"
    assert result.final.settled_contracts == 1
    assert "LOSS_LIMIT_REACHED" in result.final.abstention_reasons


def test_unknown_buy_result_stops_without_retry_and_reports_open_contract() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.DEMO_INTEGRATION,
        symbol="R_10",
        strategy=DemoStrategy.CONTROLLED_RANDOM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=1,
        armed=True,
    )
    gateway = FakeGateway(iter(()), fail_buy=True)
    gateway.open_ids.append("unknown-contract")

    result = run_autonomous_demo(
        config=config,
        limits=_limits(),
        collect_ticks=lambda symbol, count: _ticks(),
        resolve_url=lambda: "wss://demo.invalid/otp",
        gateway_factory=GatewayFactory(gateway),
    )

    assert gateway.calls.count("buy") == 1
    assert result.final.open_contracts == 1
    assert "AMBIGUOUS_DEMO_EXECUTION" in result.final.abstention_reasons
    assert "OPEN_CONTRACTS_REMAIN" in result.final.abstention_reasons


def test_experimental_budget_stops_execution_independently_of_demo_balance() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.DEMO_EXPLORATORY,
        symbol="R_10",
        strategy=DemoStrategy.CONTROLLED_RANDOM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=3,
        experimental_budget=Decimal("2"),
        armed=True,
    )
    gateway = FakeGateway(iter((Decimal("0.80"), Decimal("0.80"), Decimal("0.80"))))
    limits = DemoExecutionLimits(
        fixed_stake=Decimal("1"),
        minimum_net_payout_ratio=Decimal("0.50"),
        maximum_contracts=100,
        maximum_session_loss=Decimal("10"),
        kill_switch_enabled=False,
    )
    batch_starts = iter((1, 4, 7))

    result = run_autonomous_demo(
        config=config,
        limits=limits,
        collect_ticks=lambda symbol, count: _ticks(next(batch_starts)),
        resolve_url=lambda: "wss://demo.invalid/otp",
        gateway_factory=GatewayFactory(gateway),
    )

    assert result.final.settled_contracts == 2
    assert result.final.experimental_budget == Decimal("2")
    assert result.final.budget_used == Decimal("2")
    assert result.final.budget_remaining == Decimal("0")
    assert "EXPERIMENTAL_BUDGET_EXHAUSTED" in result.final.abstention_reasons
    assert gateway.calls.count("buy") == 2


def test_economic_metrics_use_observed_proposals_and_settlements() -> None:
    config = AutonomousDemoConfig(
        mode=ExecutionMode.DEMO_EXPLORATORY,
        symbol="R_10",
        strategy=DemoStrategy.CONTROLLED_RANDOM,
        session_seconds=60,
        ticks_per_cycle=3,
        contract_duration=1,
        maximum_cycles=2,
        experimental_budget=Decimal("100"),
        seed=7,
        armed=True,
    )
    gateway = FakeGateway(iter((Decimal("0.80"), Decimal("-1.00"))))
    batch_starts = iter((1, 4))

    result = run_autonomous_demo(
        config=config,
        limits=DemoExecutionLimits(
            fixed_stake=Decimal("1"),
            minimum_net_payout_ratio=Decimal("0.50"),
            maximum_contracts=100,
            maximum_session_loss=Decimal("10"),
            kill_switch_enabled=False,
        ),
        collect_ticks=lambda symbol, count: _ticks(next(batch_starts)),
        resolve_url=lambda: "wss://demo.invalid/otp",
        gateway_factory=GatewayFactory(gateway),
    )

    metrics = result.final.economics
    assert metrics.decisions == 2
    assert metrics.abstentions == 0
    assert metrics.abstention_frequency == Decimal("0")
    assert metrics.wins == 1
    assert metrics.losses == 1
    assert metrics.stakes == Decimal("2")
    assert metrics.effective_net_payout == Decimal("0.80")
    assert metrics.estimated_probability == Decimal("0.5")
    assert metrics.estimated_value == Decimal("-0.100")
    assert metrics.gross_profit == Decimal("0.80")
    assert metrics.gross_loss == Decimal("1.00")
    assert metrics.profit_factor == Decimal("0.8")
    assert metrics.net_profit == Decimal("-0.20")
    assert metrics.roi_on_stakes == Decimal("-0.10")
    assert {item.contract_type for item in metrics.by_contract_type} == {"DIGITODD", "CALL"}
