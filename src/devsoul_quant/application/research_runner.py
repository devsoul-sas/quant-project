"""Ephemeral end-to-end paper research runner for the Deriv laboratory.

Orchestrates discovery, tick collection, contemporary economics, causal decision
and paper settlement inside a single strictly bounded in-memory session. Only a
conclusion and aggregate counts escape; provider-derived ticks, features, P&L and
individual decisions are discarded when the session closes.

Network access is injected through ``resolve_url``, ``collect_ticks`` and
``gateway_factory`` so the orchestration is testable without a live connection.
"""

import hashlib
import json
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Protocol

from devsoul_quant.adapters.deriv.research_session import (
    EphemeralResearchSession,
    ExpiredResearchSession,
)
from devsoul_quant.application.digit_paper import (
    DigitProposalGateway,
    UnsupportedDigitContracts,
    observe_digit_economics,
    simulate_digit_decision,
)
from devsoul_quant.application.multiplier_lab import (
    MultiplierDiscoveryGateway,
    MultiplierProposalGateway,
    UnsupportedMultiplierContracts,
    observe_multiplier_proposal,
    select_multiplier_market,
)
from devsoul_quant.domain.contracts import NoTradeIntent
from devsoul_quant.domain.digit_strategy import DigitDecisionPolicy
from devsoul_quant.domain.multiplier import (
    MultiplierPolicy,
    decide_multiplier,
    replay_multiplier_estimate,
)
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.strategy_release import (
    ResearchConclusion,
    StrategyFamily,
    StrategyRelease,
)


@dataclass(frozen=True, slots=True)
class EphemeralRunResult:
    """Session verdict plus aggregate counts; no provider-derived state."""

    family: StrategyFamily
    release_id: str
    conclusion: ResearchConclusion
    forward_iterations: int
    entries: int
    no_trade: int


class MultiplierResearchGateway(MultiplierDiscoveryGateway, MultiplierProposalGateway, Protocol):
    """Combined discovery and read-only proposal port for Multiplier sessions."""


DigitGatewayFactory = Callable[[str], AbstractContextManager[DigitProposalGateway]]
MultiplierGatewayFactory = Callable[[str], AbstractContextManager[MultiplierResearchGateway]]


def _result(
    release: StrategyRelease,
    conclusion: ResearchConclusion,
    forward: int,
    entries: int,
    no_trade: int,
) -> EphemeralRunResult:
    return EphemeralRunResult(
        family=release.family,
        release_id=release.release_id,
        conclusion=conclusion,
        forward_iterations=forward,
        entries=entries,
        no_trade=no_trade,
    )


def run_even_odd_session(
    *,
    release: StrategyRelease,
    symbol: str,
    warmup_ticks: int,
    tick_count: int,
    policy: DigitDecisionPolicy,
    amount_requested: Decimal,
    resolve_url: Callable[[], str],
    collect_ticks: Callable[[str, str, int], Sequence[Tick]],
    gateway_factory: DigitGatewayFactory,
    clock: Callable[[], int],
) -> EphemeralRunResult:
    """Run one causal Even/Odd paper session and zeroize everything on exit."""
    if release.family is not StrategyFamily.EVEN_ODD:
        raise ValueError("release family must be EVEN_ODD")
    if type(warmup_ticks) is not int or warmup_ticks < 1:
        raise ValueError("warmup_ticks must be a positive integer")
    if type(tick_count) is not int or tick_count < 1:
        raise ValueError("tick_count must be a positive integer")

    session: EphemeralResearchSession[Tick] = EphemeralResearchSession(
        clock=clock, ttl_seconds=release.ttl_seconds
    )
    entries = 0
    no_trade = 0
    forward = 0
    try:
        ticks = tuple(collect_ticks(resolve_url(), symbol, tick_count))
        for tick in ticks:
            session.add_tick(tick)
        if len(ticks) < warmup_ticks + 1:
            return _result(release, ResearchConclusion.INSUFFICIENT_EVIDENCE, 0, 0, 0)

        with gateway_factory(resolve_url()) as gateway:
            try:
                even_economics, odd_economics = observe_digit_economics(
                    gateway=gateway, symbol=symbol, amount_requested=amount_requested
                )
            except UnsupportedDigitContracts:
                return _result(release, ResearchConclusion.INSUFFICIENT_EVIDENCE, 0, 0, 0)

            for index in range(warmup_ticks, len(ticks)):
                paper = simulate_digit_decision(
                    history=ticks[:index],
                    settlement_tick=ticks[index],
                    even_economics=even_economics,
                    odd_economics=odd_economics,
                    policy=policy,
                    amount_requested=amount_requested,
                    symbol=symbol,
                )
                forward += 1
                if isinstance(paper.decision, NoTradeIntent):
                    no_trade += 1
                else:
                    entries += 1

        conclusion = (
            ResearchConclusion.PAPER_ELIGIBLE if entries > 0 else ResearchConclusion.NO_EDGE
        )
        return _result(release, conclusion, forward, entries, no_trade)
    except ExpiredResearchSession:
        return _result(
            release, ResearchConclusion.INSUFFICIENT_EVIDENCE, forward, entries, no_trade
        )
    finally:
        session.close()


def run_multiplier_session(
    *,
    release: StrategyRelease,
    fallback_symbol: str,
    tick_count: int,
    policy: MultiplierPolicy,
    resolve_url: Callable[[], str],
    collect_ticks: Callable[[str, str, int], Sequence[Tick]],
    gateway_factory: MultiplierGatewayFactory,
    clock: Callable[[], int],
) -> EphemeralRunResult:
    """Run one causal Multiplier paper session and zeroize everything on exit."""
    if release.family is not StrategyFamily.MULTIPLIER:
        raise ValueError("release family must be MULTIPLIER")
    if type(tick_count) is not int or tick_count < 1:
        raise ValueError("tick_count must be a positive integer")

    session: EphemeralResearchSession[Tick] = EphemeralResearchSession(
        clock=clock, ttl_seconds=release.ttl_seconds
    )
    entries = 0
    no_trade = 0
    forward = 0
    try:
        with gateway_factory(resolve_url()) as discovery_gateway:
            try:
                market = select_multiplier_market(
                    discovery_gateway, fallback_symbol=fallback_symbol
                )
            except UnsupportedMultiplierContracts:
                return _result(release, ResearchConclusion.INSUFFICIENT_EVIDENCE, 0, 0, 0)
        effective_multiplier = min(market.allowed_multipliers)
        if effective_multiplier > policy.multiplier:
            return _result(release, ResearchConclusion.INSUFFICIENT_EVIDENCE, 0, 0, 0)
        effective_policy = replace(policy, multiplier=effective_multiplier)

        ticks = tuple(collect_ticks(resolve_url(), market.symbol, tick_count))
        for tick in ticks:
            session.add_tick(tick)
        if len(ticks) < effective_policy.lookback_ticks + 1:
            return _result(release, ResearchConclusion.INSUFFICIENT_EVIDENCE, 0, 0, 0)

        # The demo OTP connection is short-lived, so discovery and the proposal
        # loop each open their own bounded connection rather than sharing one that
        # would be stale after the (multi-connection) tick collection.
        with gateway_factory(resolve_url()) as proposal_gateway:
            for index in range(effective_policy.lookback_ticks, len(ticks)):
                decision = decide_multiplier(
                    history=ticks[:index], symbol=market.symbol, policy=effective_policy
                )
                forward += 1
                if isinstance(decision, NoTradeIntent):
                    no_trade += 1
                    continue
                proposal = observe_multiplier_proposal(proposal_gateway, market, decision)
                replay_multiplier_estimate(
                    decision,
                    entry_tick=ticks[index - 1],
                    exit_tick=ticks[index],
                    observed_commission=proposal.commission_amount,
                )
                entries += 1

        # A paper-only Multiplier session can never observe a sold exit, so any
        # directional signal only reaches an ESTIMATED result. That is not enough
        # evidence to declare an edge; absence of a signal is a falsification.
        conclusion = (
            ResearchConclusion.NO_EDGE if entries == 0 else ResearchConclusion.INSUFFICIENT_EVIDENCE
        )
        return _result(release, conclusion, forward, entries, no_trade)
    except ExpiredResearchSession:
        return _result(
            release, ResearchConclusion.INSUFFICIENT_EVIDENCE, forward, entries, no_trade
        )
    finally:
        session.close()


def _sha256(specification: dict[str, object]) -> str:
    payload = json.dumps(specification, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def even_odd_release(
    policy: DigitDecisionPolicy,
    *,
    code_version: str,
    ttl_seconds: int,
) -> StrategyRelease:
    """Build a reproducible Even/Odd release bound to the frozen policy."""
    specification: dict[str, object] = {
        "family": "EVEN_ODD",
        "min_samples": policy.min_samples,
        "z_score": str(policy.z_score),
        "min_edge_probability": str(policy.min_edge_probability),
    }
    risk: dict[str, object] = {"fixed_stake": "1.00", "maximum_open_positions": 1}
    return StrategyRelease(
        family=StrategyFamily.EVEN_ODD,
        specification_hash=_sha256(specification),
        code_version=code_version,
        risk_policy_hash=_sha256(risk),
        ttl_seconds=ttl_seconds,
    )


def multiplier_release(
    policy: MultiplierPolicy,
    *,
    code_version: str,
    ttl_seconds: int,
) -> StrategyRelease:
    """Build a reproducible Multiplier release bound to the frozen policy."""
    specification: dict[str, object] = {
        "family": "MULTIPLIER",
        "lookback_ticks": policy.lookback_ticks,
        "minimum_absolute_return": str(policy.minimum_absolute_return),
        "minimum_directional_consistency": str(policy.minimum_directional_consistency),
        "multiplier": str(policy.multiplier),
        "stake": str(policy.stake),
        "stop_loss": str(policy.stop_loss),
        "take_profit": str(policy.take_profit),
        "maximum_holding_ticks": policy.maximum_holding_ticks,
    }
    risk: dict[str, object] = {
        "fixed_stake": str(policy.stake),
        "maximum_open_positions": 1,
    }
    return StrategyRelease(
        family=StrategyFamily.MULTIPLIER,
        specification_hash=_sha256(specification),
        code_version=code_version,
        risk_policy_hash=_sha256(risk),
        ttl_seconds=ttl_seconds,
    )
