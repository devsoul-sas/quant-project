from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

import devsoul_quant.domain.contracts as contracts
from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
)


def test_contract_actions_use_contract_semantics() -> None:
    assert {action.value for action in contracts.ContractAction} == {
        "ENTER_CONTRACT",
        "NO_TRADE",
        "EXIT_CONTRACT",
    }


def test_no_trade_is_a_discriminated_contract_intent() -> None:
    intent = TypeAdapter(contracts.ContractIntent).validate_python(
        {"action": "NO_TRADE", "strategy_reason": "risk gate rejected entry"}
    )

    assert isinstance(intent, contracts.NoTradeIntent)


def test_exit_is_a_discriminated_contract_intent() -> None:
    intent = TypeAdapter(contracts.ContractIntent).validate_python(
        {
            "action": "EXIT_CONTRACT",
            "position_id": "synthetic-position-1",
            "minimum_sell_price": None,
            "exit_reason": "risk limit",
        }
    )

    assert isinstance(intent, contracts.ExitContractIntent)


def test_contract_intent_rejects_a_blank_strategy_reason() -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(contracts.ContractIntent).validate_python(
            {"action": "NO_TRADE", "strategy_reason": "   "}
        )


def test_contract_intent_keeps_complete_contract_specification() -> None:
    intent = EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_RISE_FALL",
        contract_type=ContractType.CALL,
        duration=5,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1.00"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="synthetic tracer",
    )

    assert intent.amount_requested == Decimal("1.00")
    assert intent.strategy_reason == "synthetic tracer"
    assert intent.model_dump(mode="json")["contract_type"] == "CALL"


def test_contract_intent_rejects_binary_float_amounts() -> None:
    with pytest.raises(ValidationError):
        EnterContractIntent(
            action=ContractAction.ENTER_CONTRACT,
            symbol="SYNTH_RISE_FALL",
            contract_type=ContractType.CALL,
            duration=5,
            duration_unit=DurationUnit.TICKS,
            basis=Basis.STAKE,
            amount_requested=0.1,  # type: ignore[arg-type]
            currency="USD",
            barrier=None,
            exit_policy=ExitPolicy.EXPIRY,
            strategy_reason="synthetic tracer",
        )


@pytest.mark.parametrize("invalid_duration", [True, 1.0, "1"])
def test_contract_intent_rejects_coerced_duration(invalid_duration: object) -> None:
    with pytest.raises(ValidationError):
        EnterContractIntent(
            action=ContractAction.ENTER_CONTRACT,
            symbol="SYNTH_RISE_FALL",
            contract_type=ContractType.CALL,
            duration=invalid_duration,  # type: ignore[arg-type]
            duration_unit=DurationUnit.TICKS,
            basis=Basis.STAKE,
            amount_requested=Decimal("1.00"),
            currency="USD",
            barrier=None,
            exit_policy=ExitPolicy.EXPIRY,
            strategy_reason="synthetic tracer",
        )
