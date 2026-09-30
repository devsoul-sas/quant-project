from devsoul_quant.application.demo import run_synthetic_demo
from devsoul_quant.domain.contracts import ContractAction
from devsoul_quant.domain.execution_mode import ExecutionMode
from devsoul_quant.domain.replay import EconomyProvenance, Outcome
from devsoul_quant.domain.risk import RiskDisposition


def test_demo_report_is_reproducible_and_explicitly_non_economic() -> None:
    first = run_synthetic_demo(seed=42)
    repeated = run_synthetic_demo(seed=42)

    assert first == repeated
    assert first.seed == 42
    assert first.execution_mode is ExecutionMode.SYNTHETIC_PAPER
    assert first.data_source == "DEVSOUL_SYNTHETIC"
    assert first.action is ContractAction.ENTER_CONTRACT
    assert first.risk_disposition is RiskDisposition.APPROVED
    assert first.outcome is Outcome.LOSS
    assert first.wins == 0
    assert first.losses == 1
    assert first.no_trades == 0
    assert first.economy is EconomyProvenance.UNAVAILABLE
    assert first.ledger_valid
    assert len(first.ledger_head_hash) == 64
    assert first.event_count == 6
    assert len(first.ledger_hashes) == first.event_count
    assert first.ledger_hashes[-1] == first.ledger_head_hash
    assert len(set(first.ledger_hashes)) == first.event_count
    assert first.to_dict()["ledger_hashes"] == list(first.ledger_hashes)
    assert first.profitability_claim is False
    assert not ({"balance", "profit", "pnl", "roi"} & first.to_dict().keys())


def test_demo_records_no_trade_without_paper_execution() -> None:
    report = run_synthetic_demo(seed=7)

    assert report.action is ContractAction.NO_TRADE
    assert report.risk_disposition is RiskDisposition.NO_ACTION
    assert report.outcome is None
    assert report.wins == 0
    assert report.losses == 0
    assert report.no_trades == 1
    assert report.event_count == 5
    assert report.ledger_valid
