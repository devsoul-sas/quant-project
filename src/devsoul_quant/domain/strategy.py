"""Provider-independent baseline strategies for synthetic validation."""

from collections.abc import Sequence
from decimal import Decimal

from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
    NoTradeIntent,
)
from devsoul_quant.domain.replay import Tick


class InvalidStrategyInput(ValueError):
    """Raised when a baseline cannot form a valid decision."""


def momentum_decision(
    *, history: Sequence[Tick], duration: int, amount_requested: Decimal
) -> EnterContractIntent | NoTradeIntent:
    """Compare the latest two owned synthetic ticks without economic claims."""
    if len(history) < 2:
        raise InvalidStrategyInput("momentum requires at least two ticks")
    if type(duration) is not int or duration <= 0:
        raise InvalidStrategyInput("duration must be a positive integer")
    if (
        not isinstance(amount_requested, Decimal)
        or not amount_requested.is_finite()
        or amount_requested <= 0
    ):
        raise InvalidStrategyInput("amount_requested must be a positive finite Decimal")

    previous, current = history[-2:]
    if current.epoch <= previous.epoch:
        raise InvalidStrategyInput("history must be strictly increasing")
    if current.quote == previous.quote:
        return NoTradeIntent(
            action=ContractAction.NO_TRADE,
            strategy_reason="synthetic momentum is flat",
        )

    contract_type = ContractType.CALL if current.quote > previous.quote else ContractType.PUT
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_OWNED",
        contract_type=contract_type,
        duration=duration,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=amount_requested,
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="synthetic two-tick momentum baseline",
    )
