"""Offline contract tests for the ephemeral Deriv demo execution adapter."""

import json
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest

from devsoul_quant.adapters.deriv.demo_execution import (
    DerivDemoExecutionError,
    DerivDemoExecutionGateway,
)
from devsoul_quant.application.demo_execution import DemoProposal
from devsoul_quant.application.multiplier_lab import ContractAvailability, MultiplierProposal
from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
)
from devsoul_quant.domain.multiplier import MultiplierIntent

DEMO_URL = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=secret-otp"


def _intent() -> EnterContractIntent:
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="R_100",
        contract_type=ContractType.CALL,
        duration=3,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1.00"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="frozen baseline",
    )


class FakeSocket:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages: Iterator[dict[str, Any]] = iter(messages)
        self.sent: list[dict[str, Any]] = []
        self.recv_timeouts: list[float | None] = []
        self.closed = False

    def __enter__(self) -> "FakeSocket":
        return self

    def __exit__(self, *args: object) -> bool:
        self.closed = True
        return False

    def send(self, payload: str) -> None:
        if self.closed:
            raise RuntimeError("socket is closed")
        self.sent.append(json.loads(payload))

    def recv(self, timeout: float | None = None) -> str:
        self.recv_timeouts.append(timeout)
        return json.dumps(next(self.messages))


class Connections:
    def __init__(self, *sockets: FakeSocket) -> None:
        self.sockets = iter(sockets)
        self.urls: list[str] = []

    def __call__(self, url: str) -> FakeSocket:
        self.urls.append(url)
        return next(self.sockets)


def test_gateway_builds_and_parses_a_demo_proposal() -> None:
    socket = FakeSocket([{"proposal": {"id": "p-1", "ask_price": 1.0, "payout": 1.8}, "req_id": 1}])
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))

    proposal = gateway.propose(_intent())

    assert proposal == DemoProposal("p-1", Decimal("1.0"), Decimal("1.8"))
    assert socket.sent == [
        {
            "proposal": 1,
            "amount": 1.0,
            "basis": "stake",
            "contract_type": "CALL",
            "currency": "USD",
            "duration": 3,
            "duration_unit": "t",
            "underlying_symbol": "R_100",
            "req_id": 1,
        }
    ]


def test_gateway_discovers_available_contract_types_for_symbol() -> None:
    socket = FakeSocket(
        [
            {
                "contracts_for": {
                    "available": [
                        {"contract_type": "DIGITEVEN"},
                        {"contract_type": "DIGITODD"},
                        {"contract_type": "MULTUP"},
                    ]
                },
                "req_id": 6,
            }
        ]
    )
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))

    available = gateway.available_contract_types("R_10")

    assert available == frozenset({"DIGITEVEN", "DIGITODD", "MULTUP"})
    assert socket.sent == [{"contracts_for": "R_10", "req_id": 6}]


def test_gateway_preserves_multiplier_contract_constraints() -> None:
    socket = FakeSocket(
        [
            {
                "contracts_for": {
                    "available": [
                        {
                            "contract_type": "MULTUP",
                            "expiry_type": "no_expiry",
                            "barriers": 0,
                            "multiplier_range": [40, 100],
                        },
                        {
                            "contract_type": "MULTDOWN",
                            "expiry_type": "no_expiry",
                            "barriers": 0,
                            "multiplier_range": [40, 100],
                        },
                    ]
                }
            }
        ]
    )
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))

    assert gateway.available_contracts("R_10") == (
        ContractAvailability("MULTUP", "no_expiry", 0, (Decimal("40"), Decimal("100"))),
        ContractAvailability("MULTDOWN", "no_expiry", 0, (Decimal("40"), Decimal("100"))),
    )
    assert socket.sent == [{"contracts_for": "R_10", "req_id": 6}]


def test_gateway_discovers_active_symbol_codes_and_names() -> None:
    socket = FakeSocket(
        [
            {
                "active_symbols": [
                    {
                        "underlying_symbol": "RDS10",
                        "underlying_symbol_name": "Drift Switching Index 10",
                    },
                    {
                        "underlying_symbol": "R_10",
                        "underlying_symbol_name": "Volatility 10 Index",
                    },
                ],
                "req_id": 7,
            }
        ]
    )
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))

    symbols = gateway.active_symbols()

    assert [(item.symbol, item.name) for item in symbols] == [
        ("RDS10", "Drift Switching Index 10"),
        ("R_10", "Volatility 10 Index"),
    ]
    assert socket.sent == [{"active_symbols": "brief", "req_id": 7}]


def test_gateway_builds_and_parses_multiplier_proposal_without_buying() -> None:
    socket = FakeSocket(
        [
            {
                "proposal": {
                    "id": "pm-1",
                    "ask_price": 1.0,
                    "spot": 100.25,
                    "commission": 0.5,
                },
                "req_id": 8,
            }
        ]
    )
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))
    intent = MultiplierIntent(
        symbol="RDS",
        contract_type=ContractType.MULTUP,
        stake=Decimal("1"),
        multiplier=Decimal("10"),
        stop_loss=Decimal("0.50"),
        take_profit=Decimal("1.00"),
        maximum_holding_ticks=5,
        strategy_reason="test",
    )

    proposal = gateway.propose_multiplier(intent)

    assert proposal == MultiplierProposal(
        proposal_id="pm-1",
        ask_price=Decimal("1.0"),
        spot=Decimal("100.25"),
        commission_percent=Decimal("0.5"),
    )
    assert proposal.commission_amount == Decimal("0.005")
    assert socket.sent == [
        {
            "proposal": 1,
            "amount": 1.0,
            "basis": "stake",
            "contract_type": "MULTUP",
            "currency": "USD",
            "multiplier": 10.0,
            "limit_order": {"stop_loss": 0.5, "take_profit": 1.0},
            "underlying_symbol": "RDS",
            "req_id": 8,
        }
    ]


def test_gateway_buys_at_the_observed_ask_price() -> None:
    socket = FakeSocket([{"buy": {"contract_id": 123}, "req_id": 2}])
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))

    contract_id = gateway.buy(DemoProposal("p-1", Decimal("1.00"), Decimal("1.80")))

    assert contract_id == "123"
    assert socket.sent == [{"buy": "p-1", "price": 1.0, "req_id": 2}]


def test_gateway_rejects_boolean_contract_id() -> None:
    socket = FakeSocket([{"buy": {"contract_id": True}, "req_id": 2}])
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))

    with pytest.raises(DerivDemoExecutionError, match="contract_id"):
        gateway.buy(DemoProposal("p-1", Decimal("1.00"), Decimal("1.80")))


def test_gateway_rejects_money_outside_provider_json_number_range() -> None:
    socket = FakeSocket([])
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))
    proposal = DemoProposal("p-1", Decimal("1e10000"), Decimal("2e10000"))

    with pytest.raises(DerivDemoExecutionError, match="provider numeric range"):
        gateway.buy(proposal)

    assert socket.sent == []


def test_gateway_waits_for_settlement_and_releases_subscription() -> None:
    socket = FakeSocket(
        [
            {
                "proposal_open_contract": {
                    "contract_id": 123,
                    "is_sold": 0,
                },
                "subscription": {"id": "sub-contract"},
            },
            {
                "proposal_open_contract": {
                    "contract_id": 123,
                    "is_sold": 1,
                    "profit": "0.80",
                }
            },
        ]
    )
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))

    settlement = gateway.await_settlement("123")

    assert settlement.contract_id == "123"
    assert settlement.profit == Decimal("0.80")
    assert socket.sent[0] == {
        "proposal_open_contract": 1,
        "contract_id": 123,
        "subscribe": 1,
        "req_id": 3,
    }
    assert socket.sent[-1] == {"forget": "sub-contract", "req_id": 4}


def test_gateway_enforces_one_absolute_settlement_deadline() -> None:
    socket = FakeSocket(
        [
            {
                "proposal_open_contract": {"contract_id": 123, "is_sold": 0},
                "subscription": {"id": "sub-contract"},
            }
        ]
    )
    times = iter((0.0, 2.0, 6.0))
    gateway = DerivDemoExecutionGateway(
        DEMO_URL,
        connect=Connections(socket),
        settlement_timeout_seconds=5.0,
        monotonic=lambda: next(times),
    )

    with pytest.raises(DerivDemoExecutionError, match="deadline"):
        gateway.await_settlement("123")

    assert socket.recv_timeouts == [3.0]
    assert socket.sent[-1] == {"forget": "sub-contract", "req_id": 4}


def test_gateway_reconciles_open_demo_contracts() -> None:
    socket = FakeSocket([{"portfolio": {"contracts": [{"contract_id": 7}, {"contract_id": "8"}]}}])
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))

    assert gateway.reconcile() == ("7", "8")
    assert socket.sent == [{"portfolio": 1, "req_id": 5}]


def test_gateway_errors_never_echo_the_authenticated_url() -> None:
    socket = FakeSocket([{"error": {"code": "Bad", "message": DEMO_URL}}])
    gateway = DerivDemoExecutionGateway(DEMO_URL, connect=Connections(socket))

    with pytest.raises(DerivDemoExecutionError) as captured:
        gateway.propose(_intent())

    assert "secret-otp" not in str(captured.value)
    assert "wss://" not in str(captured.value)


def test_gateway_reuses_one_otp_connection_for_the_full_lifecycle() -> None:
    socket = FakeSocket(
        [
            {"proposal": {"id": "p-1", "ask_price": 1.0, "payout": 1.8}},
            {"buy": {"contract_id": 123}},
            {
                "proposal_open_contract": {
                    "contract_id": 123,
                    "is_sold": 1,
                    "profit": "0.80",
                },
                "subscription": {"id": "sub-1"},
            },
        ]
    )
    connections = Connections(socket)

    with DerivDemoExecutionGateway(DEMO_URL, connect=connections) as gateway:
        proposal = gateway.propose(_intent())
        contract_id = gateway.buy(proposal)
        settlement = gateway.await_settlement(contract_id)

    assert settlement.profit == Decimal("0.80")
    assert connections.urls == [DEMO_URL]
    assert socket.closed is True
