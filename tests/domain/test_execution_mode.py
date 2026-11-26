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


def test_demo_exploratory_mode_parses_and_is_distinct() -> None:
    mode = parse_execution_mode("DEMO_EXPLORATORY")

    assert mode is ExecutionMode.DEMO_EXPLORATORY
    # The exploratory mode is a mode, not a promotion state or real money.
    assert mode not in (ExecutionMode.SYNTHETIC_PAPER, ExecutionMode.EPHEMERAL_PUBLIC_INTEGRATION)
    assert mode.value == "DEMO_EXPLORATORY"


def test_demo_exploratory_mode_is_not_real_money() -> None:
    # Real money must remain structurally unavailable regardless of mode spelling.
    for value in ("demo_exploratory", "DEMO_EXPLORATORY"):
        assert parse_execution_mode(value) is ExecutionMode.DEMO_EXPLORATORY
    with pytest.raises(UnsafeExecutionMode):
        parse_execution_mode("REAL")


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("observe_only", ExecutionMode.OBSERVE_ONLY),
        ("shadow_trading", ExecutionMode.SHADOW_TRADING),
        ("demo_integration", ExecutionMode.DEMO_INTEGRATION),
        ("demo_exploratory", ExecutionMode.DEMO_EXPLORATORY),
    ),
)
def test_autonomous_demo_modes_are_typed(value: str, expected: ExecutionMode) -> None:
    assert parse_execution_mode(value) is expected


@pytest.mark.parametrize("value", ("REAL", "REAL_TRADING", "real-money"))
def test_real_trading_spellings_are_structurally_rejected(value: str) -> None:
    with pytest.raises(UnsafeExecutionMode, match="real-money execution is not available"):
        parse_execution_mode(value)
