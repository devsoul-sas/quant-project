"""Ephemeral end-to-end demo session tests."""

from contextlib import AbstractContextManager
from decimal import Decimal
from typing import Any

from devsoul_quant.application.demo_execution import (
    DemoExecutionLimits,
    DemoProposal,
    DemoSettlement,
)
from devsoul_quant.application.demo_session import DemoSessionReceipt, run_demo_session
from devsoul_quant.domain.contracts import ContractType
from devsoul_quant.domain.replay import Tick


class Gateway(AbstractContextManager["Gateway"]):
    account_type = "demo"

    def __init__(self) -> None:
        self.entered = False
        self.exited = False
        self.proposed_contract_type: ContractType | None = None

    def __enter__(self) -> "Gateway":
        self.entered = True
        return self

    def __exit__(self, *args: object) -> bool:
        self.exited = True
        return False

    def propose(self, intent: Any) -> DemoProposal:
        self.proposed_contract_type = intent.contract_type
        return DemoProposal("p-1", Decimal("1.00"), Decimal("1.80"))

    def buy(self, proposal: DemoProposal) -> str:
        return "contract-1"

    def await_settlement(self, contract_id: str) -> DemoSettlement:
        return DemoSettlement(contract_id, Decimal("0.80"))

    def reconcile(self) -> tuple[str, ...]:
        return ()


def _limits() -> DemoExecutionLimits:
    return DemoExecutionLimits(
        fixed_stake=Decimal("1.00"),
        minimum_net_payout_ratio=Decimal("0.75"),
        maximum_contracts=1,
        maximum_session_loss=Decimal("1.00"),
        kill_switch_enabled=False,
    )


def test_demo_session_uses_distinct_otp_urls_and_clears_transient_state() -> None:
    urls = iter(("demo-ticks-url", "demo-execution-url"))
    resolved: list[str] = []
    collected_from: list[str] = []
    gateway_urls: list[str] = []
    gateway = Gateway()

    def resolve_url() -> str:
        url = next(urls)
        resolved.append(url)
        return url

    def collect(url: str, symbol: str, count: int) -> tuple[Tick, ...]:
        collected_from.append(url)
        return (
            Tick(epoch=1, quote=Decimal("100")),
            Tick(epoch=2, quote=Decimal("101")),
            Tick(epoch=3, quote=Decimal("102")),
            Tick(epoch=4, quote=Decimal("101")),
            Tick(epoch=5, quote=Decimal("100")),
        )

    def gateway_factory(url: str) -> Gateway:
        gateway_urls.append(url)
        return gateway

    receipt = run_demo_session(
        symbol="R_100",
        tick_count=5,
        duration=3,
        limits=_limits(),
        resolve_url=resolve_url,
        collect_ticks=collect,
        gateway_factory=gateway_factory,
    )

    assert receipt == DemoSessionReceipt()
    assert receipt.public_message == "demo session completed; inspect the provider demo account"
    assert resolved == ["demo-ticks-url", "demo-execution-url"]
    assert collected_from == ["demo-ticks-url"]
    assert gateway_urls == ["demo-execution-url"]
    assert gateway.entered is True
    assert gateway.exited is True
    assert gateway.proposed_contract_type is ContractType.PUT


def test_demo_session_does_not_request_execution_otp_for_no_trade() -> None:
    resolve_calls = 0

    def resolve_url() -> str:
        nonlocal resolve_calls
        resolve_calls += 1
        return "demo-ticks-url"

    receipt = run_demo_session(
        symbol="R_100",
        tick_count=2,
        duration=3,
        limits=_limits(),
        resolve_url=resolve_url,
        collect_ticks=lambda url, symbol, count: (
            Tick(epoch=1, quote=Decimal("100")),
            Tick(epoch=2, quote=Decimal("100")),
        ),
        gateway_factory=lambda url: Gateway(),
    )

    assert receipt == DemoSessionReceipt()
    assert receipt.public_message == "demo session completed; inspect the provider demo account"
    assert resolve_calls == 1
