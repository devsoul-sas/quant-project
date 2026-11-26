"""Ephemeral Deriv demo execution contracts and safety tests."""

from decimal import Decimal

import pytest

from devsoul_quant.application.demo_execution import (
    AmbiguousDemoExecution,
    DemoExecutionLimits,
    DemoProposal,
    DemoSession,
    DemoSettlement,
    DemoTradeRejected,
    execute_demo_intent,
)
from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
)


def _intent(amount: str = "1.00") -> EnterContractIntent:
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="R_100",
        contract_type=ContractType.CALL,
        duration=3,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal(amount),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="frozen momentum baseline",
    )


class FakeGateway:
    account_type = "demo"

    def __init__(
        self,
        *,
        profit: str = "0.80",
        fail_buy: bool = False,
        fail_settlement: bool = False,
    ) -> None:
        self.profit = Decimal(profit)
        self.fail_buy = fail_buy
        self.fail_settlement = fail_settlement
        self.calls: list[str] = []

    def propose(self, intent: EnterContractIntent) -> DemoProposal:
        self.calls.append("propose")
        return DemoProposal(
            proposal_id="proposal-1",
            ask_price=Decimal("1.00"),
            payout=Decimal("1.80"),
        )

    def buy(self, proposal: DemoProposal) -> str:
        self.calls.append("buy")
        if self.fail_buy:
            raise TimeoutError("unknown buy outcome")
        return "contract-1"

    def await_settlement(self, contract_id: str) -> DemoSettlement:
        self.calls.append("settle")
        if self.fail_settlement:
            raise TimeoutError("ambiguous settlement")
        return DemoSettlement(contract_id=contract_id, profit=self.profit)

    def reconcile(self) -> tuple[str, ...]:
        self.calls.append("reconcile")
        return ("contract-unknown",)


def _limits(**overrides: object) -> DemoExecutionLimits:
    values: dict[str, object] = {
        "fixed_stake": Decimal("1.00"),
        "minimum_net_payout_ratio": Decimal("0.75"),
        "maximum_contracts": 3,
        "maximum_session_loss": Decimal("3.00"),
        "kill_switch_enabled": False,
    }
    values.update(overrides)
    return DemoExecutionLimits(**values)  # type: ignore[arg-type]


def test_demo_execution_is_killed_by_default() -> None:
    limits = DemoExecutionLimits(
        fixed_stake=Decimal("1.00"),
        minimum_net_payout_ratio=Decimal("0.75"),
        maximum_contracts=3,
        maximum_session_loss=Decimal("3.00"),
    )

    with pytest.raises(DemoTradeRejected, match="kill switch"):
        execute_demo_intent(_intent(), gateway=FakeGateway(), limits=limits, session=DemoSession())


def test_demo_execution_settles_one_fixed_stake_contract() -> None:
    gateway = FakeGateway()
    session = DemoSession()

    result = execute_demo_intent(_intent(), gateway=gateway, limits=_limits(), session=session)

    assert result.contract_id == "contract-1"
    assert result.profit == Decimal("0.80")
    assert result.net_payout_ratio == Decimal("0.80")
    assert session.contract_count == 1
    assert session.realized_profit == Decimal("0.80")
    assert gateway.calls == ["propose", "buy", "settle"]


def test_demo_execution_rejects_a_non_demo_gateway_before_proposal() -> None:
    gateway = FakeGateway()
    gateway.account_type = "real"

    with pytest.raises(DemoTradeRejected, match="demo account"):
        execute_demo_intent(_intent(), gateway=gateway, limits=_limits(), session=DemoSession())

    assert gateway.calls == []


def test_demo_execution_rejects_variable_stake() -> None:
    gateway = FakeGateway()

    with pytest.raises(DemoTradeRejected, match="fixed stake"):
        execute_demo_intent(
            _intent("2.00"), gateway=gateway, limits=_limits(), session=DemoSession()
        )

    assert gateway.calls == []


def test_demo_execution_rejects_proposal_below_minimum_payout() -> None:
    gateway = FakeGateway()
    gateway.propose = lambda intent: DemoProposal(
        proposal_id="low", ask_price=Decimal("1.00"), payout=Decimal("1.50")
    )

    with pytest.raises(DemoTradeRejected, match="payout"):
        execute_demo_intent(_intent(), gateway=gateway, limits=_limits(), session=DemoSession())


def test_demo_execution_enforces_session_count_and_loss_limits() -> None:
    gateway = FakeGateway(profit="-1.00")
    session = DemoSession()
    limits = _limits(maximum_contracts=2, maximum_session_loss=Decimal("2.00"))

    execute_demo_intent(_intent(), gateway=gateway, limits=limits, session=session)
    execute_demo_intent(_intent(), gateway=gateway, limits=limits, session=session)
    with pytest.raises(DemoTradeRejected, match=r"contract limit|loss limit"):
        execute_demo_intent(_intent(), gateway=gateway, limits=limits, session=session)


def test_ambiguous_buy_reconciles_once_and_never_retries() -> None:
    gateway = FakeGateway(fail_buy=True)

    with pytest.raises(AmbiguousDemoExecution, match="reconciled"):
        execute_demo_intent(_intent(), gateway=gateway, limits=_limits(), session=DemoSession())

    assert gateway.calls == ["propose", "buy", "reconcile"]


def test_ambiguous_buy_can_reconcile_with_a_fresh_demo_gateway() -> None:
    execution_gateway = FakeGateway(fail_buy=True)
    recovery_gateway = FakeGateway()

    with pytest.raises(AmbiguousDemoExecution) as captured:
        execute_demo_intent(
            _intent(),
            gateway=execution_gateway,
            reconciliation_gateway=recovery_gateway,
            limits=_limits(),
            session=DemoSession(),
        )

    assert captured.value.open_contract_ids == ("contract-unknown",)
    assert execution_gateway.calls == ["propose", "buy"]
    assert recovery_gateway.calls == ["reconcile"]


def test_ambiguous_settlement_reconciles_once_and_never_rebuys() -> None:
    gateway = FakeGateway(fail_settlement=True)

    with pytest.raises(AmbiguousDemoExecution) as captured:
        execute_demo_intent(_intent(), gateway=gateway, limits=_limits(), session=DemoSession())

    assert captured.value.open_contract_ids == ("contract-unknown",)
    assert gateway.calls == ["propose", "buy", "settle", "reconcile"]


def test_session_clear_discards_all_transient_results() -> None:
    session = DemoSession()
    execute_demo_intent(_intent(), gateway=FakeGateway(), limits=_limits(), session=session)

    session.clear()

    assert session.contract_count == 0
    assert session.realized_profit == Decimal("0")
    assert session.results == ()
