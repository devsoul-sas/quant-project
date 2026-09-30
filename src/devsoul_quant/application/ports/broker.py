"""Provider-independent broker lifecycle boundary."""

from dataclasses import dataclass
from typing import Protocol

from devsoul_quant.domain.contracts import EnterContractIntent, ExitContractIntent
from devsoul_quant.domain.money import Money
from devsoul_quant.domain.replay import EconomyProvenance


class InvalidProposal(ValueError):
    """Raised when proposal economics are incomplete or contradictory."""


def _require_non_blank(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string")


@dataclass(frozen=True, slots=True)
class ContractProposal:
    """Provider-neutral economics offered for one contract intent."""

    proposal_id: str
    economy: EconomyProvenance
    ask_price: Money | None
    payout: Money | None

    def __post_init__(self) -> None:
        _require_non_blank(self.proposal_id, "proposal_id")
        if self.economy is EconomyProvenance.UNAVAILABLE:
            if self.ask_price is not None or self.payout is not None:
                raise InvalidProposal("unavailable economics cannot contain prices")
            return
        if self.ask_price is None or self.payout is None:
            raise InvalidProposal("observed or estimated economics must be complete")
        if self.ask_price.currency != self.payout.currency:
            raise InvalidProposal("proposal economics must use one currency")


@dataclass(frozen=True, slots=True)
class OpenedContract:
    position_id: str
    proposal: ContractProposal

    def __post_init__(self) -> None:
        _require_non_blank(self.position_id, "position_id")


@dataclass(frozen=True, slots=True)
class ContractObservation:
    position_id: str
    is_open: bool

    def __post_init__(self) -> None:
        _require_non_blank(self.position_id, "position_id")
        if type(self.is_open) is not bool:
            raise ValueError("is_open must be a boolean")


class BrokerPort(Protocol):
    """Propose and manage contracts without provider-specific request types."""

    def propose(self, intent: EnterContractIntent) -> ContractProposal: ...

    def open(self, intent: EnterContractIntent, proposal: ContractProposal) -> OpenedContract: ...

    def observe(self, position_id: str) -> ContractObservation: ...

    def close(self, intent: ExitContractIntent) -> ContractObservation: ...
