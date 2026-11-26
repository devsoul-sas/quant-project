"""Execution-mode safety boundary."""

from enum import StrEnum


class UnsafeExecutionMode(ValueError):
    """Raised when a configuration requests real-money execution."""


class ExecutionMode(StrEnum):
    """Modes allowed before the market-data licence gate is resolved.

    ``DEMO_EXPLORATORY`` is an execution-mechanics validation mode: it runs
    controlled virtual-capital trades against the Deriv demo account to validate
    the economic execution path (quoting, staking, payout, settlement, latency).
    It is deliberately NOT a scientific promotion state and MUST NOT be conflated
    with ``PAPER_ELIGIBLE`` (a ``ResearchConclusion``) or any edge claim. An
    exploratory demo session never promotes a policy, never asserts profitability,
    and never authorizes real money.
    """

    SYNTHETIC_BACKTEST = "SYNTHETIC_BACKTEST"
    SYNTHETIC_PAPER = "SYNTHETIC_PAPER"
    EPHEMERAL_PUBLIC_INTEGRATION = "EPHEMERAL_PUBLIC_INTEGRATION"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    SHADOW_TRADING = "SHADOW_TRADING"
    DEMO_INTEGRATION = "DEMO_INTEGRATION"
    DEMO_EXPLORATORY = "DEMO_EXPLORATORY"


def parse_execution_mode(value: str) -> ExecutionMode:
    """Parse a mode while rejecting real-money execution."""
    normalized = value.strip().upper().replace("-", "_")
    if normalized in {"REAL", "REAL_MONEY", "REAL_TRADING"}:
        raise UnsafeExecutionMode("real-money execution is not available")
    return ExecutionMode(normalized)
