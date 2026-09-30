"""Execution-mode safety boundary."""

from enum import StrEnum


class UnsafeExecutionMode(ValueError):
    """Raised when a configuration requests real-money execution."""


class ExecutionMode(StrEnum):
    """Modes allowed before the market-data licence gate is resolved."""

    SYNTHETIC_BACKTEST = "SYNTHETIC_BACKTEST"
    SYNTHETIC_PAPER = "SYNTHETIC_PAPER"
    EPHEMERAL_PUBLIC_INTEGRATION = "EPHEMERAL_PUBLIC_INTEGRATION"


def parse_execution_mode(value: str) -> ExecutionMode:
    """Parse a mode while rejecting real-money execution."""
    normalized = value.strip().upper()
    if normalized == "REAL":
        raise UnsafeExecutionMode("real-money execution is not available")
    return ExecutionMode(normalized)
