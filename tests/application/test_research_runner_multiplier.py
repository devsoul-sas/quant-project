"""End-to-end ephemeral Multiplier research runner tests."""

from collections.abc import Sequence
from contextlib import nullcontext
from decimal import Decimal

import pytest

from devsoul_quant.application.multiplier_lab import (
    ContractAvailability,
    MarketSymbol,
    MultiplierProposal,
)
from devsoul_quant.application.research_runner import EphemeralRunResult, run_multiplier_session
from devsoul_quant.domain.multiplier import MultiplierIntent, MultiplierPolicy
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.strategy_release import (
    ResearchConclusion,
    StrategyFamily,
    StrategyRelease,
)

DRIFT = MarketSymbol(symbol="SYNTH_DRIFT", name="Drift Switching Index")


class MultiplierGateway:
    def __init__(
        self,
        *,
        symbols: tuple[MarketSymbol, ...],
        contracts: dict[str, tuple[ContractAvailability, ...]],
    ) -> None:
        self._symbols = symbols
        self._contracts = contracts
        self.proposed: list[MultiplierIntent] = []

    def active_symbols(self) -> tuple[MarketSymbol, ...]:
        return self._symbols

    def available_contracts(self, symbol: str) -> tuple[ContractAvailability, ...]:
        return self._contracts.get(symbol, ())

    def propose_multiplier(self, intent: MultiplierIntent) -> MultiplierProposal:
        self.proposed.append(intent)
        return MultiplierProposal("mp-1", Decimal("1.00"), Decimal("100.0"), Decimal("0.01"))


def _drift_contracts() -> tuple[ContractAvailability, ...]:
    return (
        ContractAvailability("MULTUP", "no_expiry", 0, (Decimal("10"), Decimal("20"))),
        ContractAvailability("MULTDOWN", "no_expiry", 0, (Decimal("10"), Decimal("20"))),
    )


def _release(ttl_seconds: int = 82_800) -> StrategyRelease:
    return StrategyRelease(
        family=StrategyFamily.MULTIPLIER,
        specification_hash="a" * 64,
        code_version="0.1.0",
        risk_policy_hash="b" * 64,
        ttl_seconds=ttl_seconds,
    )


def _policy(multiplier: str = "10") -> MultiplierPolicy:
    return MultiplierPolicy(
        lookback_ticks=5,
        minimum_absolute_return=Decimal("0.01"),
        minimum_directional_consistency=Decimal("0.75"),
        multiplier=Decimal(multiplier),
        stake=Decimal("1"),
        stop_loss=Decimal("0.50"),
        take_profit=Decimal("1.00"),
        maximum_holding_ticks=5,
    )


def _trending_ticks(count: int) -> tuple[Tick, ...]:
    return tuple(Tick(epoch=index, quote=Decimal(100 + index)) for index in range(count))


def _choppy_ticks(count: int) -> tuple[Tick, ...]:
    return tuple(Tick(epoch=index, quote=Decimal(100 + (index % 2))) for index in range(count))


def _run(
    *,
    ticks: Sequence[Tick],
    gateway: MultiplierGateway,
    release: StrategyRelease,
    tick_count: int,
    policy: MultiplierPolicy,
) -> EphemeralRunResult:
    return run_multiplier_session(
        release=release,
        fallback_symbol="R_10",
        tick_count=tick_count,
        policy=policy,
        resolve_url=lambda: "demo-ticks-url",
        collect_ticks=lambda url, symbol, count: tuple(ticks),
        gateway_factory=lambda url: nullcontext(gateway),
        clock=lambda: 1_000_000_000,
    )


def test_multiplier_runner_emits_no_edge_when_directional_signal_is_absent() -> None:
    gateway = MultiplierGateway(
        symbols=(DRIFT, MarketSymbol(symbol="R_10", name="Volatility 10 Index")),
        contracts={"SYNTH_DRIFT": _drift_contracts()},
    )

    result = _run(
        ticks=_choppy_ticks(20),
        gateway=gateway,
        release=_release(),
        tick_count=20,
        policy=_policy(),
    )

    assert result.family is StrategyFamily.MULTIPLIER
    assert result.conclusion is ResearchConclusion.NO_EDGE
    assert result.entries == 0
    assert result.forward_iterations > 0


def test_multiplier_runner_emits_insufficient_when_signal_appears_but_exit_is_estimated() -> None:
    gateway = MultiplierGateway(
        symbols=(DRIFT, MarketSymbol(symbol="R_10", name="Volatility 10 Index")),
        contracts={"SYNTH_DRIFT": _drift_contracts()},
    )

    result = _run(
        ticks=_trending_ticks(20),
        gateway=gateway,
        release=_release(),
        tick_count=20,
        policy=_policy(),
    )

    assert result.conclusion is ResearchConclusion.INSUFFICIENT_EVIDENCE
    assert result.entries > 0


def test_multiplier_runner_emits_insufficient_on_unsupported_market() -> None:
    gateway = MultiplierGateway(symbols=(), contracts={})

    result = _run(
        ticks=_trending_ticks(20),
        gateway=gateway,
        release=_release(),
        tick_count=20,
        policy=_policy(),
    )

    assert result.conclusion is ResearchConclusion.INSUFFICIENT_EVIDENCE
    assert result.forward_iterations == 0


def test_multiplier_runner_emits_insufficient_when_multiplier_is_not_allowed() -> None:
    gateway = MultiplierGateway(
        symbols=(DRIFT,),
        contracts={
            "SYNTH_DRIFT": (
                ContractAvailability("MULTUP", "no_expiry", 0, (Decimal("40"),)),
                ContractAvailability("MULTDOWN", "no_expiry", 0, (Decimal("40"),)),
            )
        },
    )

    result = _run(
        ticks=_trending_ticks(20),
        gateway=gateway,
        release=_release(),
        tick_count=20,
        policy=_policy(multiplier="10"),
    )

    assert result.conclusion is ResearchConclusion.INSUFFICIENT_EVIDENCE
    assert result.forward_iterations == 0


def test_multiplier_runner_selects_the_minimum_runtime_multiplier() -> None:
    gateway = MultiplierGateway(
        symbols=(DRIFT,),
        contracts={
            "SYNTH_DRIFT": (
                ContractAvailability("MULTUP", "no_expiry", 0, (Decimal("400"), Decimal("1000"))),
                ContractAvailability("MULTDOWN", "no_expiry", 0, (Decimal("400"), Decimal("1000"))),
            )
        },
    )

    result = _run(
        ticks=_trending_ticks(20),
        gateway=gateway,
        release=_release(),
        tick_count=20,
        policy=_policy(multiplier="1000"),
    )

    assert result.conclusion is ResearchConclusion.INSUFFICIENT_EVIDENCE
    assert result.entries > 0
    assert gateway.proposed
    assert all(intent.multiplier == Decimal("400") for intent in gateway.proposed)


def test_multiplier_runner_opens_separate_gateway_connections() -> None:
    calls = {"count": 0}
    gateway = MultiplierGateway(
        symbols=(DRIFT,),
        contracts={"SYNTH_DRIFT": _drift_contracts()},
    )

    def gateway_factory(url: str):
        calls["count"] += 1
        return nullcontext(gateway)

    result = run_multiplier_session(
        release=_release(),
        fallback_symbol="R_10",
        tick_count=20,
        policy=_policy(),
        resolve_url=lambda: "demo-ticks-url",
        collect_ticks=lambda url, symbol, count: _trending_ticks(20),
        gateway_factory=gateway_factory,
        clock=lambda: 1_000_000_000,
    )

    assert calls["count"] == 2
    assert result.entries > 0


def test_multiplier_runner_emits_insufficient_on_short_history() -> None:
    gateway = MultiplierGateway(
        symbols=(DRIFT,),
        contracts={"SYNTH_DRIFT": _drift_contracts()},
    )

    result = _run(
        ticks=_trending_ticks(3),
        gateway=gateway,
        release=_release(),
        tick_count=3,
        policy=_policy(),
    )

    assert result.conclusion is ResearchConclusion.INSUFFICIENT_EVIDENCE
    assert result.forward_iterations == 0


def test_multiplier_runner_rejects_wrong_family_release() -> None:
    with pytest.raises(ValueError, match="MULTIPLIER"):
        run_multiplier_session(
            release=StrategyRelease(
                family=StrategyFamily.EVEN_ODD,
                specification_hash="a" * 64,
                code_version="0.1.0",
                risk_policy_hash="b" * 64,
                ttl_seconds=82_800,
            ),
            fallback_symbol="R_10",
            tick_count=20,
            policy=_policy(),
            resolve_url=lambda: "demo-ticks-url",
            collect_ticks=lambda url, symbol, count: _trending_ticks(20),
            gateway_factory=lambda url: nullcontext(
                MultiplierGateway(symbols=(DRIFT,), contracts={"SYNTH_DRIFT": _drift_contracts()})
            ),
            clock=lambda: 1_000_000_000,
        )


def test_multiplier_runner_rejects_non_positive_tick_count() -> None:
    with pytest.raises(ValueError):
        run_multiplier_session(
            release=_release(),
            fallback_symbol="R_10",
            tick_count=0,
            policy=_policy(),
            resolve_url=lambda: "demo-ticks-url",
            collect_ticks=lambda url, symbol, count: _trending_ticks(20),
            gateway_factory=lambda url: nullcontext(
                MultiplierGateway(symbols=(DRIFT,), contracts={"SYNTH_DRIFT": _drift_contracts()})
            ),
            clock=lambda: 1_000_000_000,
        )


def test_multiplier_runner_emits_insufficient_when_ttl_expires() -> None:
    calls = {"now": 0}

    def clock() -> int:
        value = calls["now"]
        calls["now"] += 1
        return value

    result = run_multiplier_session(
        release=_release(ttl_seconds=1),
        fallback_symbol="R_10",
        tick_count=20,
        policy=_policy(),
        resolve_url=lambda: "demo-ticks-url",
        collect_ticks=lambda url, symbol, count: _trending_ticks(20),
        gateway_factory=lambda url: nullcontext(
            MultiplierGateway(symbols=(DRIFT,), contracts={"SYNTH_DRIFT": _drift_contracts()})
        ),
        clock=clock,
    )

    assert result.conclusion is ResearchConclusion.INSUFFICIENT_EVIDENCE
    assert result.forward_iterations == 0


def test_multiplier_release_factory_is_deterministic_and_sensitive_to_policy() -> None:
    from devsoul_quant.application.research_runner import multiplier_release

    release = multiplier_release(_policy(), code_version="0.1.0", ttl_seconds=82_800)
    duplicate = multiplier_release(_policy(), code_version="0.1.0", ttl_seconds=82_800)

    assert release.release_id == duplicate.release_id
    assert release.family is StrategyFamily.MULTIPLIER

    other = multiplier_release(_policy(multiplier="20"), code_version="0.1.0", ttl_seconds=82_800)
    assert other.release_id != release.release_id
