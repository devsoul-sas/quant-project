"""Async demo WebSocket client tests (offline, with a fake connection)."""

import asyncio
import json
from decimal import Decimal
from typing import Any

import pytest

from devsoul_quant.adapters.deriv.client import (
    MAX_TICK_COUNT,
    DerivClientError,
    collect_ticks,
)
from devsoul_quant.adapters.deriv.demo_url import UnsafeDerivUrl
from devsoul_quant.adapters.deriv.ephemeral import OPERATIONAL_MARGIN_SECONDS

DEMO_URL = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=abc123"


class FakeWebSocket:
    def __init__(self, messages: list[str | bytes]) -> None:
        self._messages = iter(messages)
        self.sent: list[str] = []

    async def __aenter__(self) -> "FakeWebSocket":
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def send(self, data: str) -> None:
        self.sent.append(data)

    def __aiter__(self) -> "FakeWebSocket":
        return self

    async def __anext__(self) -> str | bytes:
        try:
            return next(self._messages)
        except StopIteration:
            raise StopAsyncIteration from None


def _connect_returning(websocket: FakeWebSocket) -> Any:
    def connect(url: str) -> FakeWebSocket:
        assert url == DEMO_URL
        return websocket

    return connect


def test_collect_ticks_parses_and_releases_the_subscription() -> None:
    websocket = FakeWebSocket(
        [
            json.dumps({"subscription": {"id": "sub-1"}}),
            json.dumps({"tick": {"epoch": 100, "quote": "10.5"}}),
            json.dumps({"tick": {"epoch": 101, "quote": 10.6}}),
        ]
    )

    ticks = asyncio.run(
        collect_ticks(DEMO_URL, "R_100", count=2, connect=_connect_returning(websocket))
    )

    assert [tick.quote for tick in ticks] == [Decimal("10.5"), Decimal("10.6")]
    assert json.loads(websocket.sent[0]) == {"ticks": "R_100", "subscribe": 1}
    assert json.loads(websocket.sent[-1]) == {"forget": "sub-1"}


def test_collect_ticks_sends_forget_all_without_a_subscription_ack() -> None:
    websocket = FakeWebSocket(
        [
            json.dumps({"tick": {"epoch": 100, "quote": "1.0"}}),
        ]
    )

    ticks = asyncio.run(
        collect_ticks(DEMO_URL, "R_100", count=1, connect=_connect_returning(websocket))
    )

    assert len(ticks) == 1
    assert json.loads(websocket.sent[-1]) == {"forget_all": "ticks"}


def test_collect_ticks_rejects_the_real_money_url() -> None:
    real_url = "wss://api.derivws.com/trading/v1/options/ws/real?otp=abc123"

    with pytest.raises(UnsafeDerivUrl):
        asyncio.run(collect_ticks(real_url, "R_100", count=1))


def test_collect_ticks_raises_on_deriv_error_messages() -> None:
    websocket = FakeWebSocket([json.dumps({"error": {"code": "X", "message": "boom"}})])

    with pytest.raises(DerivClientError, match="boom"):
        asyncio.run(
            collect_ticks(DEMO_URL, "R_100", count=1, connect=_connect_returning(websocket))
        )


def test_collect_ticks_wraps_connection_failures() -> None:
    def failing_connect(url: str) -> FakeWebSocket:
        raise OSError("network down")

    with pytest.raises(DerivClientError, match="network down"):
        asyncio.run(collect_ticks(DEMO_URL, "R_100", count=1, connect=failing_connect))


@pytest.mark.parametrize(
    ("symbol", "count"),
    [("   ", 1), ("R_100", 0)],
)
def test_collect_ticks_rejects_invalid_arguments(symbol: str, count: int) -> None:
    with pytest.raises(DerivClientError):
        asyncio.run(collect_ticks(DEMO_URL, symbol, count=count))


def test_collect_ticks_rejects_a_subscription_ack_without_id() -> None:
    websocket = FakeWebSocket([json.dumps({"subscription": {"id": ""}})])

    with pytest.raises(DerivClientError, match="missing an id"):
        asyncio.run(
            collect_ticks(DEMO_URL, "R_100", count=1, connect=_connect_returning(websocket))
        )


def test_collect_ticks_decodes_bytes_frames() -> None:
    websocket = FakeWebSocket(
        [json.dumps({"tick": {"epoch": 100, "quote": "2.5"}}).encode("utf-8")]
    )

    ticks = asyncio.run(
        collect_ticks(DEMO_URL, "R_100", count=1, connect=_connect_returning(websocket))
    )

    assert ticks[0].quote == Decimal("2.5")


def test_collect_ticks_expires_entries_during_collection() -> None:
    websocket = FakeWebSocket(
        [
            json.dumps({"tick": {"epoch": 100, "quote": "1.0"}}),
            json.dumps({"tick": {"epoch": 101, "quote": "2.0"}}),
        ]
    )
    receipt_times = iter((100, 100 + OPERATIONAL_MARGIN_SECONDS + 1))

    ticks = asyncio.run(
        collect_ticks(
            DEMO_URL,
            "R_100",
            count=2,
            connect=_connect_returning(websocket),
            clock=lambda: next(receipt_times),
        )
    )

    assert [tick.quote for tick in ticks] == [Decimal("2.0")]


def test_collect_ticks_rejects_unbounded_samples_before_connecting() -> None:
    connected = False

    def connect(url: str) -> FakeWebSocket:
        nonlocal connected
        connected = True
        return FakeWebSocket([])

    with pytest.raises(DerivClientError, match="at most"):
        asyncio.run(collect_ticks(DEMO_URL, "R_100", count=MAX_TICK_COUNT + 1, connect=connect))

    assert connected is False
