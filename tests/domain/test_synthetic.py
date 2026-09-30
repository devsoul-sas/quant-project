from decimal import ROUND_DOWN, Decimal, localcontext
from itertools import pairwise

import pytest

from devsoul_quant.domain.contracts import (
    ContractAction,
    ContractType,
    EnterContractIntent,
    NoTradeIntent,
)
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.strategy import InvalidStrategyInput, momentum_decision
from devsoul_quant.domain.synthetic import InvalidSyntheticScenario, generate_ticks


def test_synthetic_ticks_are_deterministic_and_provider_owned() -> None:
    first = generate_ticks(seed=42, count=8)
    repeated = generate_ticks(seed=42, count=8)
    different = generate_ticks(seed=43, count=8)

    assert first == repeated
    assert first != different
    assert len(first) == 8
    assert first[0].epoch == 1_700_000_000
    assert all(current.epoch > previous.epoch for previous, current in pairwise(first))
    assert all(isinstance(tick.quote, Decimal) and tick.quote > 0 for tick in first)


def test_synthetic_ticks_ignore_the_mutable_global_decimal_context() -> None:
    expected = generate_ticks(seed=42, count=8)

    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_DOWN
        actual = generate_ticks(seed=42, count=8)

    assert actual == expected


@pytest.mark.parametrize(
    ("last_quote", "expected_type"),
    [(Decimal("100.1"), ContractType.CALL), (Decimal("99.9"), ContractType.PUT)],
)
def test_momentum_baseline_emits_a_complete_enter_contract_intent(
    last_quote: Decimal, expected_type: ContractType
) -> None:
    decision = momentum_decision(
        history=(Tick(epoch=1, quote=Decimal("100")), Tick(epoch=2, quote=last_quote)),
        duration=3,
        amount_requested=Decimal("1.00"),
    )

    assert isinstance(decision, EnterContractIntent)
    assert decision.action is ContractAction.ENTER_CONTRACT
    assert decision.contract_type is expected_type
    assert decision.symbol == "SYNTH_OWNED"
    assert decision.duration == 3
    assert decision.amount_requested == Decimal("1.00")
    assert decision.barrier is None


def test_momentum_baseline_emits_no_trade_when_quotes_are_equal() -> None:
    decision = momentum_decision(
        history=(
            Tick(epoch=1, quote=Decimal("100")),
            Tick(epoch=2, quote=Decimal("100")),
        ),
        duration=3,
        amount_requested=Decimal("1.00"),
    )

    assert isinstance(decision, NoTradeIntent)
    assert decision.action is ContractAction.NO_TRADE


@pytest.mark.parametrize(
    "arguments",
    [
        {"seed": True, "count": 2},
        {"seed": 1, "count": 1},
        {"seed": 1, "count": 2, "start_epoch": True},
        {"seed": 1, "count": 2, "start_quote": Decimal("NaN")},
    ],
)
def test_synthetic_generator_rejects_invalid_configuration(
    arguments: dict[str, object],
) -> None:
    with pytest.raises(InvalidSyntheticScenario):
        generate_ticks(**arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "arguments",
    [
        {
            "history": (Tick(epoch=1, quote=Decimal("100")),),
            "duration": 3,
            "amount_requested": Decimal("1"),
        },
        {
            "history": (
                Tick(epoch=1, quote=Decimal("100")),
                Tick(epoch=2, quote=Decimal("101")),
            ),
            "duration": True,
            "amount_requested": Decimal("1"),
        },
        {
            "history": (
                Tick(epoch=1, quote=Decimal("100")),
                Tick(epoch=2, quote=Decimal("101")),
            ),
            "duration": 3,
            "amount_requested": Decimal("NaN"),
        },
        {
            "history": (
                Tick(epoch=2, quote=Decimal("100")),
                Tick(epoch=1, quote=Decimal("101")),
            ),
            "duration": 3,
            "amount_requested": Decimal("1"),
        },
    ],
)
def test_momentum_baseline_rejects_invalid_inputs(arguments: dict[str, object]) -> None:
    with pytest.raises(InvalidStrategyInput):
        momentum_decision(**arguments)  # type: ignore[arg-type]
