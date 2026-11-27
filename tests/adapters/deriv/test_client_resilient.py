"""Resilient multi-connection tick collection tests (offline, fake connections)."""

import asyncio
import json
from decimal import Decimal
from typing import Any

import pytest
from websockets.exceptions import ConnectionClosedError

from devsoul_quant.adapters.deriv.client import (
    CollectionTimeout,
    DerivClientError,
    collect_ticks_resilient,
)
from devsoul_quant.adapters.deriv.demo_url import UnsafeDerivUrl

DEMO_URL = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=abc123"
DEMO_URL_2 = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=def456"
DEMO_URL_3 = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=ghi789"


def _tick(epoch: int, quote: str) -> str:
    return json.dumps({"tick": {"epoch": epoch, "quote": quote}})


class DroppingWebSocket:
    """Yields ``messages`` then raises a connection-closed error on the next read."""

    def __init__(self, messages: list[str], *, drop_after: int | None = None) -> None:
        self._messages = iter(messages)
        self._drop_after = drop_after
        self._read = 0
        self.sent: list[str] = []

    async def __aenter__(self) -> "DroppingWebSocket":
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def send(self, data: str) -> None:
        self.sent.append(data)

    def __aiter__(self) -> "DroppingWebSocket":
        return self

    async def __anext__(self) -> str:
        if self._drop_after is not None and self._read >= self._drop_after:
            raise ConnectionClosedError(None, None)
        try:
            message = next(self._messages)
        except StopIteration:
            raise StopAsyncIteration from None
        self._read += 1
        return message


def _fake_connect(websockets_by_url: dict[str, Any]) -> Any:
    def connect(url: str) -> Any:
        return websockets_by_url[url]

    return connect


def _urls(*values: str) -> Any:
    iterator = iter(values)

    def resolve_url() -> str:
        return next(iterator)

    return resolve_url


def test_resilient_collection_reconnects_after_a_connection_drop() -> None:
    first = DroppingWebSocket([_tick(100, "1.0"), _tick(101, "2.0")], drop_after=2)
    second = DroppingWebSocket([_tick(102, "3.0"), _tick(103, "4.0"), _tick(104, "5.0")])

    ticks = asyncio.run(
        collect_ticks_resilient(
            _urls(DEMO_URL, DEMO_URL_2),
            "R_10",
            count=5,
            connect=_fake_connect({DEMO_URL: first, DEMO_URL_2: second}),
        )
    )

    assert [tick.quote for tick in ticks] == [
        Decimal("1.0"),
        Decimal("2.0"),
        Decimal("3.0"),
        Decimal("4.0"),
        Decimal("5.0"),
    ]
    assert json.loads(first.sent[0]) == {"ticks": "R_10", "subscribe": 1}
    assert json.loads(second.sent[0]) == {"ticks": "R_10", "subscribe": 1}


def test_resilient_collection_stops_as_soon_as_count_is_reached() -> None:
    websocket = DroppingWebSocket([_tick(100, "1.0"), _tick(101, "2.0"), _tick(102, "3.0")])
    called = 0

    def resolve_url() -> str:
        nonlocal called
        called += 1
        return DEMO_URL

    ticks = asyncio.run(
        collect_ticks_resilient(
            resolve_url,
            "R_10",
            count=2,
            connect=_fake_connect({DEMO_URL: websocket}),
        )
    )

    assert len(ticks) == 2
    assert called == 1


def test_resilient_collection_reconnects_until_count_is_reached() -> None:
    first = DroppingWebSocket([_tick(100, "1.0")], drop_after=1)
    second = DroppingWebSocket([_tick(101, "2.0")], drop_after=1)
    third = DroppingWebSocket([_tick(102, "3.0")])

    ticks = asyncio.run(
        collect_ticks_resilient(
            _urls(DEMO_URL, DEMO_URL_2, DEMO_URL_3),
            "R_10",
            count=3,
            connect=_fake_connect({DEMO_URL: first, DEMO_URL_2: second, DEMO_URL_3: third}),
        )
    )

    assert len(ticks) == 3


def test_resilient_collection_validates_every_resolved_url() -> None:
    with pytest.raises(UnsafeDerivUrl):
        asyncio.run(
            collect_ticks_resilient(
                _urls("wss://api.derivws.com/trading/v1/options/ws/real?otp=abc123"),
                "R_10",
                count=1,
                connect=_fake_connect({}),
            )
        )


@pytest.mark.parametrize(("symbol", "count"), [("   ", 1), ("R_10", 0)])
def test_resilient_collection_rejects_invalid_arguments(symbol: str, count: int) -> None:
    with pytest.raises(DerivClientError):
        asyncio.run(collect_ticks_resilient(_urls(DEMO_URL), symbol, count=count))


def test_resilient_collection_raises_on_provider_errors_without_reconnecting() -> None:
    websocket = DroppingWebSocket([json.dumps({"error": {"code": "X", "message": "boom"}})])
    called = 0

    def resolve_url() -> str:
        nonlocal called
        called += 1
        return DEMO_URL

    with pytest.raises(DerivClientError, match="boom"):
        asyncio.run(
            collect_ticks_resilient(
                resolve_url,
                "R_10",
                count=1,
                connect=_fake_connect({DEMO_URL: websocket}),
            )
        )

    assert called == 1


class SlowWebSocket:
    """Yields ticks with a real-time delay so a bounded deadline elapses mid-batch."""

    def __init__(self, messages: list[str], delay: float) -> None:
        self._messages = iter(messages)
        self._delay = delay
        self.sent: list[str] = []

    async def __aenter__(self) -> "SlowWebSocket":
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def send(self, data: str) -> None:
        self.sent.append(data)

    def __aiter__(self) -> "SlowWebSocket":
        return self

    async def __anext__(self) -> str:
        try:
            message = next(self._messages)
        except StopIteration:
            raise StopAsyncIteration from None
        await asyncio.sleep(self._delay)
        return message


class HangingWebSocket:
    """Never yields a tick, so the collection window elapses without progress."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def __aenter__(self) -> "HangingWebSocket":
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def send(self, data: str) -> None:
        self.sent.append(data)

    def __aiter__(self) -> "HangingWebSocket":
        return self

    async def __anext__(self) -> str:
        await asyncio.sleep(10)
        return ""  # pragma: no cover - the timeout cancels this coroutine first


def test_deadline_driven_timeout_returns_partial_ticks() -> None:
    ws = SlowWebSocket([_tick(i, str(float(i))) for i in range(1000)], delay=0.01)
    ticks = asyncio.run(
        collect_ticks_resilient(
            _urls(DEMO_URL),
            "stpRNG",
            count=1000,
            connect=_fake_connect({DEMO_URL: ws}),
            deadline_remaining=0.2,
        )
    )
    assert 0 < len(ticks) < 1000


def test_stall_without_deadline_raises_collection_timeout(monkeypatch) -> None:
    import devsoul_quant.adapters.deriv.client as client_module

    monkeypatch.setattr(client_module, "MAX_COLLECTION_SECONDS", 0.1)
    ws = HangingWebSocket()

    with pytest.raises(CollectionTimeout):
        asyncio.run(
            collect_ticks_resilient(
                _urls(DEMO_URL),
                "stpRNG",
                count=10,
                connect=_fake_connect({DEMO_URL: ws}),
                deadline_remaining=None,
            )
        )


def test_reconnections_are_reported() -> None:
    first = DroppingWebSocket([_tick(100, "1.0")], drop_after=1)
    second = DroppingWebSocket([_tick(101, "2.0"), _tick(102, "3.0")])
    reconnects: list[int] = []

    ticks = asyncio.run(
        collect_ticks_resilient(
            _urls(DEMO_URL, DEMO_URL_2),
            "R_10",
            count=3,
            connect=_fake_connect({DEMO_URL: first, DEMO_URL_2: second}),
            reconnections=reconnects,
        )
    )

    assert len(ticks) == 3
    assert reconnects == [1]
