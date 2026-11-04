"""One bounded, memory-only Deriv demo execution session."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass

from devsoul_quant.application.demo_execution import (
    DemoExecutionGateway,
    DemoExecutionLimits,
    DemoSession,
    execute_demo_intent,
)
from devsoul_quant.domain.contracts import EnterContractIntent
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.strategy import momentum_decision


@dataclass(frozen=True, slots=True)
class DemoSessionReceipt:
    """Constant operational receipt containing no provider-derived state."""

    @property
    def public_message(self) -> str:
        return "demo session completed; inspect the provider demo account"


GatewayContext = AbstractContextManager[DemoExecutionGateway]


def run_demo_session(
    *,
    symbol: str,
    tick_count: int,
    duration: int,
    limits: DemoExecutionLimits,
    resolve_url: Callable[[], str],
    collect_ticks: Callable[[str, str, int], Sequence[Tick]],
    gateway_factory: Callable[[str], GatewayContext],
) -> DemoSessionReceipt:
    """Observe, decide, and settle at most one demo contract, then discard state."""
    tick_url = resolve_url()
    ticks = tuple(collect_ticks(tick_url, symbol, tick_count))
    if len(ticks) < 2:
        return DemoSessionReceipt()
    intent = momentum_decision(
        history=ticks,
        duration=duration,
        amount_requested=limits.fixed_stake,
        symbol=symbol,
    )
    if not isinstance(intent, EnterContractIntent):
        return DemoSessionReceipt()

    execution_url = resolve_url()
    session = DemoSession()
    try:
        with gateway_factory(execution_url) as gateway:
            execute_demo_intent(intent, gateway=gateway, limits=limits, session=session)
        return DemoSessionReceipt()
    finally:
        session.clear()
        ticks = ()
