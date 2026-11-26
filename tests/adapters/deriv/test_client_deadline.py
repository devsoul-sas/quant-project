"""S3.10/D deadline-propagation tests for the demo WebSocket client."""

import asyncio
import json
from decimal import Decimal
from typing import Any

import pytest

from devsoul_quant.adapters.deriv.client import DerivClientError, collect_ticks

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


class NeverEndingWebSocket(FakeWebSocket):
    """Socket whose read blocks past any reasonable collection deadline."""

    async def __anext__(self) -> str | bytes:
        await asyncio.sleep(3600)
        return b""


def _connect_returning(websocket: FakeWebSocket) -> Any:
    def connect(url: str) -> FakeWebSocket:
        assert url == DEMO_URL
        return websocket

    return connect


def test_collect_ticks_respects_a_tight_deadline_remaining() -> None:
    """A blocking feed is aborted once ``deadline_remaining`` elapses."""
    with pytest.raises(DerivClientError, match="timed out"):
        asyncio.run(
            collect_ticks(
                DEMO_URL,
                "R_100",
                count=1,
                connect=_connect_returning(NeverEndingWebSocket([])),
                deadline_remaining=0.05,
            )
        )


def test_collect_ticks_rejects_non_positive_deadline_remaining() -> None:
    with pytest.raises(DerivClientError, match="deadline_remaining"):
        asyncio.run(collect_ticks(DEMO_URL, "R_100", count=1, deadline_remaining=0))
    with pytest.raises(DerivClientError, match="deadline_remaining"):
        asyncio.run(collect_ticks(DEMO_URL, "R_100", count=1, deadline_remaining=-5))


def test_collect_ticks_accepts_deadline_remaining_above_the_hard_bound() -> None:
    """A generous deadline is clamped to the per-call hard bound, not raised."""
    websocket = FakeWebSocket([json.dumps({"tick": {"epoch": 100, "quote": "10.5"}})])
    ticks = asyncio.run(
        collect_ticks(
            DEMO_URL,
            "R_100",
            count=1,
            connect=_connect_returning(websocket),
            deadline_remaining=10_000_000.0,
        )
    )
    assert [tick.quote for tick in ticks] == [Decimal("10.5")]
