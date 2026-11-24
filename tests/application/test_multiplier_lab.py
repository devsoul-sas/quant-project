"""Runtime Multiplier market selection tests."""

from decimal import Decimal

import pytest

from devsoul_quant.application.multiplier_lab import (
    ContractAvailability,
    MarketSymbol,
    MultiplierProposal,
    SelectedMultiplierMarket,
    UnsupportedMultiplierContracts,
    observe_multiplier_proposal,
    select_multiplier_market,
)
from devsoul_quant.domain.contracts import ContractType
from devsoul_quant.domain.multiplier import MultiplierIntent


class FakeDiscoveryGateway:
    def __init__(
        self,
        symbols: tuple[MarketSymbol, ...],
        contracts: dict[str, tuple[ContractAvailability, ...]],
    ) -> None:
        self.symbols = symbols
        self.contracts = contracts
        self.queried: list[str] = []

    def active_symbols(self) -> tuple[MarketSymbol, ...]:
        return self.symbols

    def available_contracts(self, symbol: str) -> tuple[ContractAvailability, ...]:
        self.queried.append(symbol)
        return self.contracts[symbol]


def _availability(
    contract_type: str,
    *,
    multipliers: tuple[Decimal, ...] = (Decimal("40"), Decimal("100")),
    expiry_type: str = "no_expiry",
    barriers: int = 0,
) -> ContractAvailability:
    return ContractAvailability(
        contract_type=contract_type,
        expiry_type=expiry_type,
        barriers=barriers,
        multiplier_range=multipliers,
    )


def test_select_multiplier_market_prefers_non_1s_drift_switching() -> None:
    gateway = FakeDiscoveryGateway(
        (
            MarketSymbol("RDS_1S", "Drift Switching Index 10 (1s)"),
            MarketSymbol("RDS", "Drift Switching Index 10"),
            MarketSymbol("R_10", "Volatility 10 Index"),
        ),
        {
            "RDS": (_availability("MULTUP"), _availability("MULTDOWN")),
            "R_10": (_availability("MULTUP"), _availability("MULTDOWN")),
        },
    )

    assert select_multiplier_market(gateway) == SelectedMultiplierMarket(
        symbol="RDS",
        allowed_multipliers=(Decimal("40"), Decimal("100")),
    )
    assert gateway.queried == ["RDS"]


def test_select_multiplier_market_uses_r10_only_as_validated_fallback() -> None:
    gateway = FakeDiscoveryGateway(
        (
            MarketSymbol("RDS", "Drift Switching Index 10"),
            MarketSymbol("R_10", "Volatility 10 Index"),
        ),
        {
            "RDS": (_availability("MULTUP"),),
            "R_10": (_availability("MULTUP"), _availability("MULTDOWN")),
        },
    )

    assert select_multiplier_market(gateway).symbol == "R_10"
    assert gateway.queried == ["RDS", "R_10"]


@pytest.mark.parametrize(
    "contracts",
    [
        (_availability("MULTUP"),),
        (
            _availability("MULTUP", expiry_type="tick"),
            _availability("MULTDOWN"),
        ),
        (
            _availability("MULTUP", barriers=1),
            _availability("MULTDOWN"),
        ),
        (
            _availability("MULTUP", multipliers=(Decimal("40"),)),
            _availability("MULTDOWN", multipliers=(Decimal("100"),)),
        ),
        (
            _availability("MULTUP", multipliers=(Decimal("-40"),)),
            _availability("MULTDOWN", multipliers=(Decimal("-40"),)),
        ),
        (
            _availability("MULTUP"),
            _availability("MULTUP"),
            _availability("MULTDOWN"),
        ),
    ],
)
def test_select_multiplier_market_fails_closed_without_compatible_family(
    contracts: tuple[ContractAvailability, ...],
) -> None:
    gateway = FakeDiscoveryGateway(
        (MarketSymbol("R_10", "Volatility 10 Index"),),
        {"R_10": contracts},
    )

    with pytest.raises(UnsupportedMultiplierContracts, match="MULTUP and MULTDOWN"):
        select_multiplier_market(gateway)


@pytest.mark.parametrize(
    ("proposal_id", "ask", "spot", "commission"),
    [
        (" ", Decimal("1"), Decimal("100"), Decimal("0.5")),
        ("p", Decimal("0"), Decimal("100"), Decimal("0.5")),
        ("p", Decimal("1"), Decimal("NaN"), Decimal("0.5")),
        ("p", Decimal("1"), Decimal("100"), Decimal("-1")),
        ("p", Decimal("1"), Decimal("100"), Decimal("101")),
    ],
)
def test_multiplier_proposal_rejects_incomplete_economics(
    proposal_id: str,
    ask: Decimal,
    spot: Decimal,
    commission: Decimal,
) -> None:
    with pytest.raises(ValueError):
        MultiplierProposal(proposal_id, ask, spot, commission)


class FakeProposalGateway:
    def __init__(self) -> None:
        self.received: list[MultiplierIntent] = []

    def propose_multiplier(self, intent: MultiplierIntent) -> MultiplierProposal:
        self.received.append(intent)
        return MultiplierProposal("proposal-1", Decimal("1"), Decimal("100"), Decimal("0.5"))


def _intent(*, symbol: str = "R_10", multiplier: str = "40") -> MultiplierIntent:
    return MultiplierIntent(
        symbol=symbol,
        contract_type=ContractType.MULTUP,
        stake=Decimal("1"),
        multiplier=Decimal(multiplier),
        stop_loss=Decimal("0.5"),
        take_profit=Decimal("1"),
        maximum_holding_ticks=10,
        strategy_reason="test",
    )


def test_observe_multiplier_proposal_enforces_discovered_market() -> None:
    gateway = FakeProposalGateway()
    market = SelectedMultiplierMarket("R_10", (Decimal("40"), Decimal("100")))

    proposal = observe_multiplier_proposal(gateway, market, _intent())

    assert proposal.proposal_id == "proposal-1"
    assert gateway.received == [_intent()]


@pytest.mark.parametrize(
    "intent",
    [_intent(symbol="R_100"), _intent(multiplier="10")],
)
def test_observe_multiplier_proposal_rejects_undiscovered_parameters(
    intent: MultiplierIntent,
) -> None:
    gateway = FakeProposalGateway()
    market = SelectedMultiplierMarket("R_10", (Decimal("40"), Decimal("100")))

    with pytest.raises(UnsupportedMultiplierContracts):
        observe_multiplier_proposal(gateway, market, intent)

    assert gateway.received == []
