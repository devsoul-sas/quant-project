import json
from datetime import UTC, datetime
from decimal import ROUND_DOWN, localcontext
from hashlib import sha256

from devsoul_quant.adapters.clock.replay import ReplayClock
from devsoul_quant.application.demo import run_synthetic_demo
from devsoul_quant.domain.contracts import ContractAction
from devsoul_quant.domain.execution_mode import ExecutionMode
from devsoul_quant.domain.ledger import GENESIS_HASH, InMemoryLedger
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


def test_demo_uses_an_injected_clock_without_reading_system_time() -> None:
    clock = ReplayClock(datetime.fromtimestamp(1_700_000_000, tz=UTC))

    with_clock = run_synthetic_demo(seed=42, clock=clock)
    with_epoch = run_synthetic_demo(seed=42, start_epoch=1_700_000_000)

    assert with_clock == with_epoch


def test_demo_uses_an_injected_append_only_ledger() -> None:
    ledger = InMemoryLedger()

    report = run_synthetic_demo(seed=42, ledger=ledger)

    assert len(ledger.events) == report.event_count
    assert ledger.events[-1].event_hash == report.ledger_head_hash


def test_demo_report_ignores_the_mutable_global_decimal_context() -> None:
    expected = run_synthetic_demo(seed=42)

    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_DOWN
        actual = run_synthetic_demo(seed=42)

    assert actual == expected


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


def test_demo_ledger_is_externally_verifiable_and_preserves_the_full_contract_spec() -> None:
    report = run_synthetic_demo(seed=42)

    assert len(report.ledger_events) == report.event_count == len(report.ledger_hashes)

    previous_hash = GENESIS_HASH
    for canonical, claimed_hash in zip(report.ledger_events, report.ledger_hashes, strict=True):
        assert sha256(canonical.encode()).hexdigest() == claimed_hash
        assert json.loads(canonical)["previous_hash"] == previous_hash
        previous_hash = claimed_hash
    assert previous_hash == report.ledger_head_hash

    decided = json.loads(report.ledger_events[2])
    assert decided["event_type"] == "STRATEGY_DECIDED"
    for field in (
        "symbol",
        "contract_type",
        "duration",
        "duration_unit",
        "basis",
        "amount_requested",
        "currency",
        "exit_policy",
    ):
        assert field in decided["payload"]
