"""End-to-end ephemeral Even/Odd research runner tests."""

from collections.abc import Sequence
from contextlib import nullcontext
from decimal import Decimal

import pytest

from devsoul_quant.application.demo_execution import DemoProposal
from devsoul_quant.application.research_runner import EphemeralRunResult, run_even_odd_session
from devsoul_quant.domain.digit_strategy import DigitDecisionPolicy
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.strategy_release import (
    ResearchConclusion,
    StrategyFamily,
    StrategyRelease,
)


class DigitGateway:
    def __init__(self, contract_types: frozenset[str]) -> None:
        self._contract_types = contract_types

    def available_contract_types(self, symbol: str) -> frozenset[str]:
        return self._contract_types

    def propose(self, intent: object) -> DemoProposal:
        return DemoProposal("p-1", Decimal("1.00"), Decimal("1.90"))


def _release(ttl_seconds: int = 82_800) -> StrategyRelease:
    return StrategyRelease(
        family=StrategyFamily.EVEN_ODD,
        specification_hash="a" * 64,
        code_version="0.1.0",
        risk_policy_hash="b" * 64,
        ttl_seconds=ttl_seconds,
    )


def _policy() -> DigitDecisionPolicy:
    return DigitDecisionPolicy(
        min_samples=100,
        z_score=Decimal("2.576"),
        min_edge_probability=Decimal("0.01"),
    )


def _even_ticks(count: int) -> tuple[Tick, ...]:
    return tuple(
        Tick(epoch=index, quote=Decimal(f"100.{index * 2 % 10}"), pip_size=1)
        for index in range(count)
    )


def _balanced_ticks(count: int) -> tuple[Tick, ...]:
    return tuple(
        Tick(epoch=index, quote=Decimal(f"100.{index % 10}"), pip_size=1) for index in range(count)
    )


def _run(
    *,
    ticks: Sequence[Tick],
    gateway: DigitGateway,
    release: StrategyRelease,
    warmup_ticks: int = 100,
    tick_count: int = 120,
) -> EphemeralRunResult:
    return run_even_odd_session(
        release=release,
        symbol="R_10",
        warmup_ticks=warmup_ticks,
        tick_count=tick_count,
        policy=_policy(),
        amount_requested=Decimal("1"),
        resolve_url=lambda: "demo-ticks-url",
        collect_ticks=lambda url, symbol, count: tuple(ticks),
        gateway_factory=lambda url: nullcontext(gateway),
        clock=lambda: 1_000_000_000,
    )


def test_even_odd_runner_emits_paper_eligible_on_conservative_edge() -> None:
    result = _run(
        ticks=_even_ticks(120),
        gateway=DigitGateway(frozenset({"DIGITEVEN", "DIGITODD"})),
        release=_release(),
    )

    assert result.family is StrategyFamily.EVEN_ODD
    assert result.conclusion is ResearchConclusion.PAPER_ELIGIBLE
    assert result.forward_iterations == 20
    assert result.entries > 0


def test_even_odd_runner_emits_no_edge_on_balanced_history() -> None:
    result = _run(
        ticks=_balanced_ticks(120),
        gateway=DigitGateway(frozenset({"DIGITEVEN", "DIGITODD"})),
        release=_release(),
    )

    assert result.conclusion is ResearchConclusion.NO_EDGE
    assert result.forward_iterations == 20
    assert result.entries == 0
    assert result.no_trade == 20


def test_even_odd_runner_emits_insufficient_on_short_history() -> None:
    result = _run(
        ticks=_even_ticks(50),
        gateway=DigitGateway(frozenset({"DIGITEVEN", "DIGITODD"})),
        release=_release(),
        tick_count=50,
    )

    assert result.conclusion is ResearchConclusion.INSUFFICIENT_EVIDENCE
    assert result.forward_iterations == 0


def test_even_odd_runner_emits_insufficient_on_unsupported_contracts() -> None:
    result = _run(
        ticks=_even_ticks(120),
        gateway=DigitGateway(frozenset({"CALL", "PUT"})),
        release=_release(),
    )

    assert result.conclusion is ResearchConclusion.INSUFFICIENT_EVIDENCE
    assert result.forward_iterations == 0


def test_even_odd_runner_emits_insufficient_when_ttl_expires() -> None:
    calls = {"now": 0}

    def clock() -> int:
        value = calls["now"]
        calls["now"] += 1
        return value

    result = run_even_odd_session(
        release=_release(ttl_seconds=1),
        symbol="R_10",
        warmup_ticks=100,
        tick_count=120,
        policy=_policy(),
        amount_requested=Decimal("1"),
        resolve_url=lambda: "demo-ticks-url",
        collect_ticks=lambda url, symbol, count: _even_ticks(120),
        gateway_factory=lambda url: nullcontext(DigitGateway(frozenset({"DIGITEVEN", "DIGITODD"}))),
        clock=clock,
    )

    assert result.conclusion is ResearchConclusion.INSUFFICIENT_EVIDENCE
    assert result.forward_iterations == 0


def test_even_odd_runner_rejects_wrong_family_release() -> None:
    with pytest.raises(ValueError, match="EVEN_ODD"):
        run_even_odd_session(
            release=StrategyRelease(
                family=StrategyFamily.MULTIPLIER,
                specification_hash="a" * 64,
                code_version="0.1.0",
                risk_policy_hash="b" * 64,
                ttl_seconds=82_800,
            ),
            symbol="R_10",
            warmup_ticks=100,
            tick_count=120,
            policy=_policy(),
            amount_requested=Decimal("1"),
            resolve_url=lambda: "demo-ticks-url",
            collect_ticks=lambda url, symbol, count: _even_ticks(120),
            gateway_factory=lambda url: nullcontext(
                DigitGateway(frozenset({"DIGITEVEN", "DIGITODD"}))
            ),
            clock=lambda: 0,
        )


def test_even_odd_runner_result_carries_no_derived_state() -> None:
    result = EphemeralRunResult(
        family=StrategyFamily.EVEN_ODD,
        release_id="c" * 64,
        conclusion=ResearchConclusion.NO_EDGE,
        forward_iterations=20,
        entries=0,
        no_trade=20,
    )

    assert not hasattr(result, "profit")
    assert not hasattr(result, "ticks")
    assert not hasattr(result, "features")
    assert len(result.release_id) == 64


def test_even_odd_release_factory_is_deterministic_and_sensitive_to_policy() -> None:
    from devsoul_quant.application.research_runner import even_odd_release

    release = even_odd_release(_policy(), code_version="0.1.0", ttl_seconds=82_800)
    duplicate = even_odd_release(_policy(), code_version="0.1.0", ttl_seconds=82_800)

    assert release.release_id == duplicate.release_id
    assert release.family is StrategyFamily.EVEN_ODD

    other_policy = DigitDecisionPolicy(
        min_samples=200, z_score=Decimal("2.576"), min_edge_probability=Decimal("0.01")
    )
    other = even_odd_release(other_policy, code_version="0.1.0", ttl_seconds=82_800)
    assert other.release_id != release.release_id


@pytest.mark.parametrize("bad", [{"warmup_ticks": 0}, {"tick_count": 0}])
def test_even_odd_runner_rejects_non_positive_counts(bad: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        run_even_odd_session(
            release=_release(),
            symbol="R_10",
            warmup_ticks=bad.get("warmup_ticks", 100),
            tick_count=bad.get("tick_count", 120),
            policy=_policy(),
            amount_requested=Decimal("1"),
            resolve_url=lambda: "demo-ticks-url",
            collect_ticks=lambda url, symbol, count: _even_ticks(120),
            gateway_factory=lambda url: nullcontext(
                DigitGateway(frozenset({"DIGITEVEN", "DIGITODD"}))
            ),
            clock=lambda: 1_000_000_000,
        )
