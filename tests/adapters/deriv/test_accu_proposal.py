"""Synthetic verification of the read-only ACCU proposal adapter (S4.1)."""

import json
from decimal import Decimal
from typing import Any

import pytest

from devsoul_quant.adapters.deriv.accu_proposal import (
    AccumulatorProposal,
    ProposalError,
    _decimal,
    _decode,
    _json_number,
    _mapping,
    _percentage,
    propose_accumulator,
)

DEMO_URL = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=secret-otp"


class FakeSocket:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = iter(messages)
        self.sent: list[dict[str, Any]] = []

    def __enter__(self) -> "FakeSocket":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    def recv(self, timeout: float | None = None) -> str:
        return json.dumps(next(self.messages))


class Connections:
    def __init__(self, *sockets: FakeSocket) -> None:
        self.sockets = iter(sockets)
        self.urls: list[str] = []

    def __call__(self, url: str) -> FakeSocket:
        self.urls.append(url)
        return next(self.sockets)


def _proposal_message() -> dict[str, Any]:
    return {
        "proposal": {
            "id": "p-1",
            "spot": 398.31,
            "contract_details": {
                "barrier_spot_distance": "0.193",
                "high_barrier": "398.503",
                "low_barrier": "398.117",
                "tick_size_barrier": 0.000483474879,
                "tick_size_barrier_percentage": "0.04835%",
                "maximum_ticks": 50,
                "maximum_payout": 6000,
                "minimum_stake": "1.00",
                "maximum_stake": "1000.00",
                "ticks_stayed_in": [0, 6, 43, 30, 1],
            },
        },
        "req_id": 1,
    }


def test_propose_accumulator_parses_contract_fields() -> None:
    socket = FakeSocket([_proposal_message()])
    proposal = propose_accumulator(
        DEMO_URL,
        "R_100",
        growth_rate=Decimal("0.05"),
        stake=Decimal("1"),
        connect=Connections(socket),
    )

    assert proposal == AccumulatorProposal(
        proposal_id="p-1",
        symbol="R_100",
        growth_rate=Decimal("0.05"),
        barrier_fraction=Decimal("0.000483474879"),
        barrier_percentage=Decimal("0.04835"),
        high_barrier=Decimal("398.503"),
        low_barrier=Decimal("398.117"),
        barrier_spot_distance=Decimal("0.193"),
        spot=Decimal("398.31"),
        maximum_ticks=50,
        maximum_payout=Decimal("6000"),
        minimum_stake=Decimal("1.00"),
        maximum_stake=Decimal("1000.00"),
        ticks_stayed_in=(0, 6, 43, 30, 1),
    )
    sent = socket.sent[0]
    assert sent["contract_type"] == "ACCU"
    assert sent["amount"] == 1.0
    assert sent["growth_rate"] == 0.05
    assert sent["underlying_symbol"] == "R_100"


def test_propose_accumulator_sends_stake_as_number() -> None:
    socket = FakeSocket([_proposal_message()])
    propose_accumulator(
        DEMO_URL,
        "R_100",
        growth_rate=Decimal("0.05"),
        stake=Decimal("1.00"),
        connect=Connections(socket),
    )
    assert isinstance(socket.sent[0]["amount"], float)
    assert isinstance(socket.sent[0]["growth_rate"], float)


def test_propose_accumulator_rejects_provider_error() -> None:
    socket = FakeSocket([{"error": {"code": "X", "message": "bad"}, "req_id": 1}])
    with pytest.raises(ProposalError):
        propose_accumulator(
            DEMO_URL,
            "R_100",
            growth_rate=Decimal("0.05"),
            stake=Decimal("1"),
            connect=Connections(socket),
        )


def test_propose_accumulator_rejects_invalid_growth_rate() -> None:
    with pytest.raises(ProposalError):
        propose_accumulator(
            DEMO_URL,
            "R_100",
            growth_rate=Decimal("1.5"),
            stake=Decimal("1"),
            connect=Connections(),
        )


def test_propose_accumulator_rejects_missing_ticks_stayed_in() -> None:
    message = _proposal_message()
    del message["proposal"]["contract_details"]["ticks_stayed_in"]
    socket = FakeSocket([message])
    with pytest.raises(ProposalError):
        propose_accumulator(
            DEMO_URL,
            "R_100",
            growth_rate=Decimal("0.05"),
            stake=Decimal("1"),
            connect=Connections(socket),
        )


def test_propose_accumulator_rejects_missing_contract_details() -> None:
    message = _proposal_message()
    del message["proposal"]["contract_details"]
    socket = FakeSocket([message])
    with pytest.raises(ProposalError):
        propose_accumulator(
            DEMO_URL,
            "R_100",
            growth_rate=Decimal("0.05"),
            stake=Decimal("1"),
            connect=Connections(socket),
        )


def test_propose_accumulator_rejects_missing_id() -> None:
    message = _proposal_message()
    message["proposal"]["id"] = ""
    socket = FakeSocket([message])
    with pytest.raises(ProposalError):
        propose_accumulator(
            DEMO_URL,
            "R_100",
            growth_rate=Decimal("0.05"),
            stake=Decimal("1"),
            connect=Connections(socket),
        )


def test_propose_accumulator_rejects_invalid_stayed_entry() -> None:
    message = _proposal_message()
    message["proposal"]["contract_details"]["ticks_stayed_in"] = [1, "x", 2]
    socket = FakeSocket([message])
    with pytest.raises(ProposalError):
        propose_accumulator(
            DEMO_URL,
            "R_100",
            growth_rate=Decimal("0.05"),
            stake=Decimal("1"),
            connect=Connections(socket),
        )


def test_propose_accumulator_rejects_missing_maximum_ticks() -> None:
    message = _proposal_message()
    del message["proposal"]["contract_details"]["maximum_ticks"]
    socket = FakeSocket([message])
    with pytest.raises(ProposalError):
        propose_accumulator(
            DEMO_URL,
            "R_100",
            growth_rate=Decimal("0.05"),
            stake=Decimal("1"),
            connect=Connections(socket),
        )


def test_propose_accumulator_skips_non_proposal_messages() -> None:
    socket = FakeSocket([{"msg_type": "ignore"}, _proposal_message()])
    proposal = propose_accumulator(
        DEMO_URL,
        "R_100",
        growth_rate=Decimal("0.05"),
        stake=Decimal("1"),
        connect=Connections(socket),
    )
    assert proposal.proposal_id == "p-1"


def test_propose_accumulator_deadline_expiry() -> None:
    socket = FakeSocket([])
    times = iter([0.0, 1000.0])
    with pytest.raises(ProposalError):
        propose_accumulator(
            DEMO_URL,
            "R_100",
            growth_rate=Decimal("0.05"),
            stake=Decimal("1"),
            connect=Connections(socket),
            monotonic=lambda: next(times),
        )


def test_propose_accumulator_rejects_non_object_response() -> None:
    socket = FakeSocket([[]])  # type: ignore[list-item]
    with pytest.raises(ProposalError):
        propose_accumulator(
            DEMO_URL,
            "R_100",
            growth_rate=Decimal("0.05"),
            stake=Decimal("1"),
            connect=Connections(socket),
        )


def test_helper_decimal_rejects_invalid() -> None:
    with pytest.raises(ProposalError):
        _decimal("abc", "field")
    with pytest.raises(ProposalError):
        _decimal("NaN", "field")


def test_helper_percentage_strips_percent_sign() -> None:
    assert _percentage("0.04835%", "field") == Decimal("0.04835")
    with pytest.raises(ProposalError):
        _percentage("-1%", "field")


def test_helper_mapping_rejects_non_mapping() -> None:
    with pytest.raises(ProposalError):
        _mapping([], "field")


def test_helper_decode_rejects_invalid() -> None:
    with pytest.raises(ProposalError):
        _decode("not json")
    with pytest.raises(ProposalError):
        _decode("[]")


def test_helper_json_number_rejects_invalid() -> None:
    with pytest.raises(ProposalError):
        _json_number(Decimal("1e400"), "field")
    assert _json_number(Decimal("0.05"), "field") == 0.05
