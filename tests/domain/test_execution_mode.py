import pytest

from devsoul_quant.domain.execution_mode import (
    ExecutionMode,
    UnsafeExecutionMode,
    parse_execution_mode,
)


def test_real_execution_mode_is_rejected() -> None:
    with pytest.raises(UnsafeExecutionMode, match="real-money execution is not available"):
        parse_execution_mode("REAL")


def test_allowed_execution_mode_is_a_typed_value() -> None:
    mode = parse_execution_mode("synthetic_backtest")

    assert isinstance(mode, ExecutionMode)
    assert mode.value == "SYNTHETIC_BACKTEST"
