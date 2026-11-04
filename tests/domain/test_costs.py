"""Execution-cost model tests."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.contracts import ContractType
from devsoul_quant.domain.costs import (
    ExecutionCostModel,
    InvalidCostModel,
    direction_clears_spread,
    net_outcome,
)
from devsoul_quant.domain.replay import Outcome


def test_cost_model_accepts_zero_and_positive_spread() -> None:
    ExecutionCostModel(spread_fraction=Decimal("0"))
    ExecutionCostModel(spread_fraction=Decimal("0.0001"))


@pytest.mark.parametrize("bad", [Decimal("-0.001"), Decimal("NaN"), Decimal("Infinity")])
def test_cost_model_rejects_invalid_spread(bad: Decimal) -> None:
    with pytest.raises(InvalidCostModel):
        ExecutionCostModel(spread_fraction=bad)


def test_cost_model_rejects_non_decimal() -> None:
    with pytest.raises(InvalidCostModel):
        ExecutionCostModel(spread_fraction=0.0001)  # type: ignore[arg-type]


def test_zero_spread_matches_raw_direction() -> None:
    assert direction_clears_spread(
        entry=Decimal("1.10"),
        exit=Decimal("1.11"),
        contract_type=ContractType.CALL,
        spread_fraction=Decimal("0"),
    )
    assert not direction_clears_spread(
        entry=Decimal("1.10"),
        exit=Decimal("1.09"),
        contract_type=ContractType.CALL,
        spread_fraction=Decimal("0"),
    )


def test_call_must_clear_spread() -> None:
    spread = Decimal("0.01")
    assert direction_clears_spread(
        entry=Decimal("1.00"),
        exit=Decimal("1.10"),
        contract_type=ContractType.CALL,
        spread_fraction=spread,
    )
    assert not direction_clears_spread(
        entry=Decimal("1.00"),
        exit=Decimal("1.005"),
        contract_type=ContractType.CALL,
        spread_fraction=spread,
    )


def test_put_must_clear_spread() -> None:
    spread = Decimal("0.01")
    assert direction_clears_spread(
        entry=Decimal("1.00"),
        exit=Decimal("0.90"),
        contract_type=ContractType.PUT,
        spread_fraction=spread,
    )
    assert not direction_clears_spread(
        entry=Decimal("1.00"),
        exit=Decimal("0.995"),
        contract_type=ContractType.PUT,
        spread_fraction=spread,
    )


def test_net_outcome_reclassifies_net_of_spread() -> None:
    assert (
        net_outcome(
            entry=Decimal("1.00"),
            exit=Decimal("1.10"),
            contract_type=ContractType.CALL,
            spread_fraction=Decimal("0.01"),
        )
        is Outcome.WIN
    )
    assert (
        net_outcome(
            entry=Decimal("1.00"),
            exit=Decimal("1.005"),
            contract_type=ContractType.CALL,
            spread_fraction=Decimal("0.01"),
        )
        is Outcome.LOSS
    )


def test_direction_clears_spread_rejects_unknown_contract_type() -> None:
    with pytest.raises(InvalidCostModel):
        direction_clears_spread(
            entry=Decimal("1.00"),
            exit=Decimal("1.10"),
            contract_type="NOT_A_TYPE",  # type: ignore[arg-type]
            spread_fraction=Decimal("0"),
        )


def test_net_outcome_rejects_negative_spread() -> None:
    with pytest.raises(InvalidCostModel):
        net_outcome(
            entry=Decimal("1.00"),
            exit=Decimal("1.10"),
            contract_type=ContractType.CALL,
            spread_fraction=Decimal("-0.01"),
        )
