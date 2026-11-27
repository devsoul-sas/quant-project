"""Synthetic verification of the read-only ticks_history adapter (S4.1)."""

import json
from decimal import Decimal
from typing import Any

import pytest

from devsoul_quant.adapters.deriv.history import (
    HistoryError,
    _decode,
    _parse_pip_size,
    fetch_ticks_history,
    request_ticks_history,
)
from devsoul_quant.domain.replay import Tick

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


def _history(prices: list[float], times: list[int], pip_size: float = 2.0) -> dict[str, Any]:
    return {"history": {"prices": prices, "times": times}, "pip_size": pip_size}


def test_request_ticks_history_parses_ticks() -> None:
    socket = FakeSocket([_history([100.0, 100.5], [1000, 1002])])
    page = request_ticks_history(DEMO_URL, "R_100", count=2, connect=Connections(socket))

    assert page.ticks == (
        Tick(1000, Decimal("100.0"), 2),
        Tick(1002, Decimal("100.5"), 2),
    )
    assert page.pip_size == 2
    assert socket.sent[0]["ticks_history"] == "R_100"
    assert socket.sent[0]["style"] == "ticks"


def test_request_ticks_history_rejects_provider_error() -> None:
    socket = FakeSocket([{"error": {"code": "X", "message": "bad"}}])
    with pytest.raises(HistoryError):
        request_ticks_history(DEMO_URL, "R_100", count=2, connect=Connections(socket))


def test_request_ticks_history_rejects_malformed_payload() -> None:
    socket = FakeSocket([{"history": {"prices": [1.0], "times": [1, 2]}}])
    with pytest.raises(HistoryError):
        request_ticks_history(DEMO_URL, "R_100", count=2, connect=Connections(socket))


def test_request_ticks_history_rejects_real_endpoint() -> None:
    with pytest.raises(ValueError):
        request_ticks_history(
            "wss://api.derivws.com/trading/v1/options/ws/real?otp=x",
            "R_100",
            count=2,
            connect=Connections(),
        )


def test_request_ticks_history_rejects_invalid_count() -> None:
    with pytest.raises(HistoryError):
        request_ticks_history(DEMO_URL, "R_100", count=0, connect=Connections())


def test_fetch_ticks_history_dedups_by_epoch() -> None:
    page1 = FakeSocket([_history([1.0, 2.0, 3.0], [100, 102, 102])])
    page2 = FakeSocket([_history([], [])])
    result = fetch_ticks_history(
        lambda: DEMO_URL,
        "R_100",
        total_count=3,
        cadence_seconds=2,
        connect=Connections(page1, page2),
    )

    assert [tick.epoch for tick in result.ticks] == [100, 102]
    assert result.pages == 2
    assert result.discontinuities == 0
    assert result.ended_early is False


def test_fetch_ticks_history_counts_discontinuities() -> None:
    page = FakeSocket([_history([1.0, 2.0, 3.0], [100, 102, 110])])
    result = fetch_ticks_history(
        lambda: DEMO_URL, "R_100", total_count=3, cadence_seconds=2, connect=Connections(page)
    )

    assert result.discontinuities == 1
    assert result.ticks


def test_fetch_ticks_history_paginates_backward() -> None:
    page1 = FakeSocket([_history([2.0, 2.01], [200, 202])])
    page2 = FakeSocket([_history([1.0, 1.01], [100, 102])])
    result = fetch_ticks_history(
        lambda: DEMO_URL,
        "R_100",
        total_count=4,
        cadence_seconds=2,
        connect=Connections(page1, page2),
    )

    assert [tick.epoch for tick in result.ticks] == [100, 102, 200, 202]
    assert result.pages == 2
    assert result.discontinuities == 1


def test_fetch_ticks_history_stops_early_on_deadline() -> None:
    result = fetch_ticks_history(
        lambda: DEMO_URL,
        "R_100",
        total_count=10,
        cadence_seconds=2,
        deadline_remaining=0,
        connect=Connections(),
    )

    assert result.ended_early is True
    assert result.ticks == ()
    assert result.pages == 0


def test_fetch_ticks_history_stops_on_empty_page() -> None:
    page = FakeSocket([_history([], [])])
    result = fetch_ticks_history(
        lambda: DEMO_URL, "R_100", total_count=10, cadence_seconds=2, connect=Connections(page)
    )

    assert result.ticks == ()
    assert result.pages == 1
    assert result.ended_early is False


def test_request_ticks_history_rejects_invalid_end() -> None:
    with pytest.raises(HistoryError):
        request_ticks_history(
            DEMO_URL,
            "R_100",
            count=2,
            end=[],
            connect=Connections(),  # type: ignore[arg-type]
        )


def test_request_ticks_history_rejects_negative_quote() -> None:
    socket = FakeSocket([_history([-1.0], [1000])])
    with pytest.raises(HistoryError):
        request_ticks_history(DEMO_URL, "R_100", count=1, connect=Connections(socket))


def test_request_ticks_history_rejects_non_integer_epoch() -> None:
    socket = FakeSocket([_history([1.0], ["abc"])])  # type: ignore[list-item]
    with pytest.raises(HistoryError):
        request_ticks_history(DEMO_URL, "R_100", count=1, connect=Connections(socket))


def test_request_ticks_history_rejects_non_list_prices() -> None:
    socket = FakeSocket([{"history": {"prices": "x", "times": [1]}, "pip_size": 2.0}])
    with pytest.raises(HistoryError):
        request_ticks_history(DEMO_URL, "R_100", count=1, connect=Connections(socket))


def test_request_ticks_history_rejects_non_object_response() -> None:
    socket = FakeSocket([[]])  # type: ignore[list-item]
    with pytest.raises(HistoryError):
        request_ticks_history(DEMO_URL, "R_100", count=1, connect=Connections(socket))


def test_request_ticks_history_skips_non_history_messages() -> None:
    socket = FakeSocket([{"msg_type": "ignore"}, _history([1.0], [1000])])
    page = request_ticks_history(DEMO_URL, "R_100", count=1, connect=Connections(socket))
    assert len(page.ticks) == 1


def test_request_ticks_history_deadline_expiry() -> None:
    socket = FakeSocket([])
    times = iter([0.0, 1000.0])
    with pytest.raises(HistoryError):
        request_ticks_history(
            DEMO_URL,
            "R_100",
            count=1,
            connect=Connections(socket),
            monotonic=lambda: next(times),
        )


def test_parse_pip_size_edge_cases() -> None:
    assert _parse_pip_size(None) is None
    assert _parse_pip_size(True) is None
    assert _parse_pip_size(-1) is None
    assert _parse_pip_size(2.5) is None
    assert _parse_pip_size(2.0) == 2
    assert _parse_pip_size(5) == 5


def test_decode_rejects_invalid() -> None:
    with pytest.raises(HistoryError):
        _decode("not json")
    with pytest.raises(HistoryError):
        _decode("[]")


def test_fetch_ticks_history_rejects_invalid_total_count() -> None:
    with pytest.raises(HistoryError):
        fetch_ticks_history(
            lambda: DEMO_URL, "R_100", total_count=0, cadence_seconds=2, connect=Connections()
        )


def test_fetch_ticks_history_rejects_invalid_cadence() -> None:
    with pytest.raises(HistoryError):
        fetch_ticks_history(
            lambda: DEMO_URL, "R_100", total_count=10, cadence_seconds=0, connect=Connections()
        )
