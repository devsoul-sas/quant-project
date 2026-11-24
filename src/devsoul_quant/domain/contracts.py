"""Provider-independent contract intent types."""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

type NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type StrictNonNegativeDecimal = Annotated[Decimal, Field(ge=0, strict=True)]


class ContractAction(StrEnum):
    """Provider-independent contract lifecycle actions."""

    ENTER_CONTRACT = "ENTER_CONTRACT"
    NO_TRADE = "NO_TRADE"
    EXIT_CONTRACT = "EXIT_CONTRACT"


class ContractType(StrEnum):
    """Supported provider-independent option contract directions."""

    CALL = "CALL"
    PUT = "PUT"
    DIGITEVEN = "DIGITEVEN"
    DIGITODD = "DIGITODD"
    MULTUP = "MULTUP"
    MULTDOWN = "MULTDOWN"


class DurationUnit(StrEnum):
    """Supported duration unit for the first tracer."""

    TICKS = "t"


class Basis(StrEnum):
    """How the requested synthetic amount is interpreted."""

    STAKE = "stake"


class ExitPolicy(StrEnum):
    """Provider-independent exit policy."""

    EXPIRY = "expiry"


class EnterContractIntent(BaseModel):
    """Complete immutable request to enter one contract before risk approval."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: Literal[ContractAction.ENTER_CONTRACT]
    symbol: NonBlankText
    contract_type: ContractType
    duration: Annotated[int, Field(gt=0, strict=True)]
    duration_unit: DurationUnit
    basis: Basis
    amount_requested: Annotated[Decimal, Field(gt=0, strict=True)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    barrier: Decimal | None
    exit_policy: ExitPolicy
    strategy_reason: NonBlankText


class NoTradeIntent(BaseModel):
    """Explicit decision not to enter a contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: Literal[ContractAction.NO_TRADE]
    strategy_reason: NonBlankText


class ExitContractIntent(BaseModel):
    """Explicit request to close an existing contract when supported."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: Literal[ContractAction.EXIT_CONTRACT]
    position_id: NonBlankText
    minimum_sell_price: StrictNonNegativeDecimal | None
    exit_reason: NonBlankText


type ContractIntent = Annotated[
    EnterContractIntent | NoTradeIntent | ExitContractIntent,
    Field(discriminator="action"),
]
