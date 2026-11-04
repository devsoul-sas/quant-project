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


def _validate_direction_inputs(
    *, duration: object, amount_requested: object, symbol: object
) -> None:
    if type(duration) is not int or duration <= 0:
        raise InvalidStrategyInput("duration must be a positive integer")
    if (
        not isinstance(amount_requested, Decimal)
        or not amount_requested.is_finite()
        or amount_requested <= 0
    ):
        raise InvalidStrategyInput("amount_requested must be a positive finite Decimal")
    if not isinstance(symbol, str) or not symbol.strip():
        raise InvalidStrategyInput("symbol must be a non-blank string")


def _enter_contract(
    *,
    contract_type: ContractType,
    duration: int,
    amount_requested: Decimal,
    symbol: str,
    strategy_reason: str,
) -> EnterContractIntent:
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol=symbol,
        contract_type=contract_type,
        duration=duration,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=amount_requested,
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason=strategy_reason,
    )


def momentum_decision(
    *,
    history: Sequence[Tick],
    duration: int,
    amount_requested: Decimal,
    symbol: str = "SYNTH_OWNED",
) -> EnterContractIntent | NoTradeIntent:
    """Compare the latest two owned ticks without economic claims."""
    if len(history) < 2:
        raise InvalidStrategyInput("momentum requires at least two ticks")
    _validate_direction_inputs(duration=duration, amount_requested=amount_requested, symbol=symbol)

    previous, current = history[-2:]
    if current.epoch <= previous.epoch:
        raise InvalidStrategyInput("history must be strictly increasing")
    if current.quote == previous.quote:
        return NoTradeIntent(
            action=ContractAction.NO_TRADE,
            strategy_reason="synthetic momentum is flat",
        )

    contract_type = ContractType.CALL if current.quote > previous.quote else ContractType.PUT
    return _enter_contract(
        contract_type=contract_type,
        duration=duration,
        amount_requested=amount_requested,
        symbol=symbol,
        strategy_reason="synthetic two-tick momentum baseline",
    )


def momentum_window_decision(
    *,
    history: Sequence[Tick],
    lookback: int,
    duration: int,
    amount_requested: Decimal,
    symbol: str = "SYNTH_OWNED",
) -> EnterContractIntent | NoTradeIntent:
    """Momentum over a lookback window: CALL when the latest tick exceeds N back."""
    return _window_decision(
        history=history,
        lookback=lookback,
        duration=duration,
        amount_requested=amount_requested,
        symbol=symbol,
        invert=False,
    )


def mean_reversion_decision(
    *,
    history: Sequence[Tick],
    lookback: int,
    duration: int,
    amount_requested: Decimal,
    symbol: str = "SYNTH_OWNED",
) -> EnterContractIntent | NoTradeIntent:
    """Mean-reversion over a lookback window: fade the move (CALL on a fall)."""
    return _window_decision(
        history=history,
        lookback=lookback,
        duration=duration,
        amount_requested=amount_requested,
        symbol=symbol,
        invert=True,
    )


def _window_decision(
    *,
    history: Sequence[Tick],
    lookback: int,
    duration: int,
    amount_requested: Decimal,
    symbol: str,
    invert: bool,
) -> EnterContractIntent | NoTradeIntent:
    if type(lookback) is not int or lookback < 1:
        raise InvalidStrategyInput("lookback must be a positive integer")
    if len(history) < lookback + 1:
        raise InvalidStrategyInput("history is too short for the requested lookback")
    _validate_direction_inputs(duration=duration, amount_requested=amount_requested, symbol=symbol)

    reference, current = history[-1 - lookback], history[-1]
    if current.epoch <= reference.epoch:
        raise InvalidStrategyInput("history must be strictly increasing")
    family = "mean-reversion" if invert else "momentum"
    if current.quote == reference.quote:
        return NoTradeIntent(
            action=ContractAction.NO_TRADE,
            strategy_reason=f"synthetic {family} is flat",
        )

    rose = current.quote > reference.quote
    go_call = (not rose) if invert else rose
    contract_type = ContractType.CALL if go_call else ContractType.PUT
    return _enter_contract(
        contract_type=contract_type,
        duration=duration,
        amount_requested=amount_requested,
        symbol=symbol,
        strategy_reason=f"synthetic {family} lookback={lookback}",
    )
