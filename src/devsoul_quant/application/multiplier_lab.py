"""Fail-closed runtime market selection for the Multiplier paper lab."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from devsoul_quant.domain.multiplier import MultiplierIntent


class UnsupportedMultiplierContracts(ValueError):
    """Raised when no approved candidate exposes both Multiplier directions."""


@dataclass(frozen=True, slots=True)
class MarketSymbol:
    """Provider-neutral transient symbol identity."""

    symbol: str
    name: str


@dataclass(frozen=True, slots=True)
class ContractAvailability:
    """Provider-neutral contract constraints discovered for one symbol."""

    contract_type: str
    expiry_type: str
    barriers: int
    multiplier_range: tuple[Decimal, ...]


@dataclass(frozen=True, slots=True)
class SelectedMultiplierMarket:
    """Validated no-expiry market and the common allowed multipliers."""

    symbol: str
    allowed_multipliers: tuple[Decimal, ...]


@dataclass(frozen=True, slots=True)
class MultiplierProposal:
    """Minimal transient economics from one read-only Multiplier proposal."""

    proposal_id: str
    ask_price: Decimal
    spot: Decimal
    commission_percent: Decimal

    def __post_init__(self) -> None:
        if not self.proposal_id.strip():
            raise ValueError("proposal_id must be non-blank")
        for field in ("ask_price", "spot"):
            value = getattr(self, field)
            if not value.is_finite() or value <= 0:
                raise ValueError(f"{field} must be a positive finite Decimal")
        if (
            not self.commission_percent.is_finite()
            or self.commission_percent < 0
            or self.commission_percent > 100
        ):
            raise ValueError("commission_percent must be within [0, 100]")

    @property
    def commission_amount(self) -> Decimal:
        return self.ask_price * self.commission_percent / Decimal("100")


class MultiplierDiscoveryGateway(Protocol):
    """Read-only runtime discovery port."""

    def active_symbols(self) -> tuple[MarketSymbol, ...]: ...

    def available_contracts(self, symbol: str) -> tuple[ContractAvailability, ...]: ...


class MultiplierProposalGateway(Protocol):
    """Read-only port for observing contemporary Multiplier economics."""

    def propose_multiplier(self, intent: MultiplierIntent) -> MultiplierProposal: ...


def select_multiplier_market(
    gateway: MultiplierDiscoveryGateway,
    *,
    fallback_symbol: str = "R_10",
) -> SelectedMultiplierMarket:
    """Prefer standard Drift Switching with validated no-expiry constraints."""
    active = gateway.active_symbols()
    drift = [
        item.symbol
        for item in active
        if "drift switching" in item.name.casefold() and "1s" not in item.name.casefold()
    ]
    active_codes = {item.symbol for item in active}
    candidates = [*drift]
    if fallback_symbol in active_codes and fallback_symbol not in candidates:
        candidates.append(fallback_symbol)
    for symbol in candidates:
        discovered = tuple(
            item
            for item in gateway.available_contracts(symbol)
            if item.contract_type in {"MULTUP", "MULTDOWN"}
        )
        if len(discovered) != 2:
            continue
        contracts = {item.contract_type: item for item in discovered}
        if set(contracts) != {"MULTUP", "MULTDOWN"}:
            continue
        up = contracts["MULTUP"]
        down = contracts["MULTDOWN"]
        if (
            up.expiry_type != "no_expiry"
            or down.expiry_type != "no_expiry"
            or up.barriers != 0
            or down.barriers != 0
            or any(
                not value.is_finite() or value <= 0
                for value in (*up.multiplier_range, *down.multiplier_range)
            )
        ):
            continue
        common_multipliers = tuple(sorted(set(up.multiplier_range) & set(down.multiplier_range)))
        if common_multipliers:
            return SelectedMultiplierMarket(
                symbol=symbol,
                allowed_multipliers=common_multipliers,
            )
    raise UnsupportedMultiplierContracts("no approved symbol exposes both MULTUP and MULTDOWN")


def observe_multiplier_proposal(
    gateway: MultiplierProposalGateway,
    market: SelectedMultiplierMarket,
    intent: MultiplierIntent,
) -> MultiplierProposal:
    """Quote only parameters validated by the current runtime catalogue."""
    if intent.symbol != market.symbol:
        raise UnsupportedMultiplierContracts("intent symbol was not selected at runtime")
    if intent.multiplier not in market.allowed_multipliers:
        raise UnsupportedMultiplierContracts("multiplier was not allowed by contracts_for")
    return gateway.propose_multiplier(intent)
