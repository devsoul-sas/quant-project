import inspect
from decimal import Decimal

import pytest

import devsoul_quant.application.ports.broker as broker_module
import devsoul_quant.application.ports.ledger as ledger_module
import devsoul_quant.application.ports.market_data as market_data_module
from devsoul_quant.application.ports.broker import (
    ContractObservation,
    ContractProposal,
    InvalidProposal,
    OpenedContract,
)
from devsoul_quant.application.ports.ledger import LedgerPort
from devsoul_quant.application.ports.market_data import MarketDataBatch
from devsoul_quant.domain.ledger import InMemoryLedger
from devsoul_quant.domain.money import Money
from devsoul_quant.domain.replay import EconomyProvenance, Tick


def test_in_memory_ledger_satisfies_the_application_port() -> None:
    assert isinstance(InMemoryLedger(), LedgerPort)


def test_contract_proposal_never_infers_missing_economics() -> None:
    unavailable = ContractProposal(
        proposal_id="proposal-1",
        economy=EconomyProvenance.UNAVAILABLE,
        ask_price=None,
        payout=None,
    )

    assert unavailable.ask_price is None
    assert unavailable.payout is None

    with pytest.raises(InvalidProposal, match="unavailable"):
        ContractProposal(
            proposal_id="proposal-2",
            economy=EconomyProvenance.UNAVAILABLE,
            ask_price=Money(Decimal("1.00"), "USD"),
            payout=Money(Decimal("1.80"), "USD"),
        )


def test_observed_contract_proposal_requires_complete_same_currency_economics() -> None:
    with pytest.raises(InvalidProposal, match="complete"):
        ContractProposal(
            proposal_id="proposal-1",
            economy=EconomyProvenance.OBSERVED,
            ask_price=Money(Decimal("1.00"), "USD"),
            payout=None,
        )

    with pytest.raises(InvalidProposal, match="currency"):
        ContractProposal(
            proposal_id="proposal-2",
            economy=EconomyProvenance.OBSERVED,
            ask_price=Money(Decimal("1.00"), "USD"),
            payout=Money(Decimal("1.80"), "EUR"),
        )


def test_observed_contract_proposal_accepts_complete_matching_economics() -> None:
    proposal = ContractProposal(
        proposal_id="proposal-1",
        economy=EconomyProvenance.OBSERVED,
        ask_price=Money(Decimal("1.00"), "USD"),
        payout=Money(Decimal("1.80"), "USD"),
    )

    assert proposal.ask_price is not None
    assert proposal.ask_price.amount == Decimal("1.00")


def test_broker_envelopes_reject_blank_or_invalid_identifiers() -> None:
    proposal = ContractProposal(
        proposal_id="proposal-1",
        economy=EconomyProvenance.UNAVAILABLE,
        ask_price=None,
        payout=None,
    )
    with pytest.raises(ValueError, match="proposal_id"):
        ContractProposal(
            proposal_id=" ",
            economy=EconomyProvenance.UNAVAILABLE,
            ask_price=None,
            payout=None,
        )
    with pytest.raises(ValueError, match="position_id"):
        OpenedContract(position_id=" ", proposal=proposal)
    with pytest.raises(ValueError, match="position_id"):
        ContractObservation(position_id=" ", is_open=True)
    with pytest.raises(ValueError, match="is_open"):
        ContractObservation(position_id="position-1", is_open=1)  # type: ignore[arg-type]


def test_market_data_batch_carries_source_license_and_provenance() -> None:
    batch = MarketDataBatch(
        source="DEVSOUL_SYNTHETIC",
        license_reference="DEVSOUL_OWNED",
        provenance=EconomyProvenance.UNAVAILABLE,
        ticks=(Tick(epoch=1, quote=Decimal("100.00")),),
    )

    assert batch.license_reference == "DEVSOUL_OWNED"
    assert batch.ticks[0].epoch == 1

    with pytest.raises(ValueError, match="license_reference"):
        MarketDataBatch(
            source="DEVSOUL_SYNTHETIC",
            license_reference=" ",
            provenance=EconomyProvenance.UNAVAILABLE,
            ticks=(),
        )


def test_application_ports_do_not_import_adapters_or_sqlalchemy() -> None:
    for module in (broker_module, ledger_module, market_data_module):
        source = inspect.getsource(module)
        assert "devsoul_quant.adapters" not in source
        assert "sqlalchemy" not in source.lower()
