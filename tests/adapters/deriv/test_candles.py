"""Synthetic verification of the read-only candles adapter (S4.2 Línea B)."""

import json
from decimal import Decimal
from typing import Any

import pytest

from devsoul_quant.adapters.deriv.candles import (
    Candle,
    CandlesError,
    _decode,
    fetch_candles,
    request_candles,
)

DEMO_URL = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=secret-otp"


class FakeSocket:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = iter(messages)
        self.sent: list[dict[str, Any]] = []
        self.recv_timeouts: list[float | None] = []

    def __enter__(self) -> "FakeSocket":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def send(self, payload: str) -> None:
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


def _candle(epoch: int, o: float, h: float, lo: float, c: float) -> dict[str, Any]:
    return {"epoch": epoch, "open": o, "high": h, "low": lo, "close": c}


def _candles(*items: dict[str, Any]) -> dict[str, Any]:
    return {"candles": list(items)}


def test_request_candles_parses_ohlc() -> None:
    socket = FakeSocket([_candles(_candle(1000, 1.0, 1.5, 0.9, 1.2))])
    page = request_candles(
        DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket)
    )

    assert page.candles == (
        Candle(1000, Decimal("1.0"), Decimal("1.5"), Decimal("0.9"), Decimal("1.2")),
    )
    assert socket.sent[0]["ticks_history"] == "frxEURUSD"
    assert socket.sent[0]["granularity"] == 60
    assert socket.sent[0]["style"] == "candles"


def test_request_candles_rejects_provider_error() -> None:
    socket = FakeSocket([{"error": {"code": "X", "message": "bad"}}])
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket))


def test_request_candles_rejects_invalid_granularity() -> None:
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=0, count=1, connect=Connections())


def test_request_candles_rejects_invalid_count() -> None:
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=60, count=0, connect=Connections())


def test_request_candles_rejects_invalid_end() -> None:
    with pytest.raises(CandlesError):
        request_candles(
            DEMO_URL,
            "frxEURUSD",
            granularity=60,
            count=1,
            end=[],  # type: ignore[arg-type]
            connect=Connections(),
        )


def test_request_candles_rejects_real_endpoint() -> None:
    with pytest.raises(ValueError):
        request_candles(
            "wss://api.derivws.com/trading/v1/options/ws/real?otp=x",
            "frxEURUSD",
            granularity=60,
            count=1,
            connect=Connections(),
        )


def test_request_candles_rejects_high_below_low() -> None:
    socket = FakeSocket([_candles(_candle(1000, 1.0, 0.5, 0.9, 1.0))])
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket))


def test_request_candles_rejects_non_numeric_quote() -> None:
    socket = FakeSocket([_candles(_candle(1000, "x", 1.5, 0.9, 1.0))])  # type: ignore[arg-type]
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket))


def test_request_candles_rejects_non_integer_epoch() -> None:
    socket = FakeSocket([_candles(_candle("abc", 1.0, 1.5, 0.9, 1.0))])  # type: ignore[arg-type]
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket))


def test_request_candles_rejects_non_object_response() -> None:
    socket = FakeSocket([[]])  # type: ignore[list-item]
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket))


def test_request_candles_skips_non_candles_messages() -> None:
    socket = FakeSocket([{"msg_type": "ignore"}, _candles(_candle(1000, 1.0, 1.1, 0.9, 1.0))])
    page = request_candles(
        DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket)
    )
    assert len(page.candles) == 1


def test_request_candles_deadline_expiry() -> None:
    socket = FakeSocket([])
    times = iter([0.0, 1000.0])
    with pytest.raises(CandlesError):
        request_candles(
            DEMO_URL,
            "frxEURUSD",
            granularity=60,
            count=1,
            connect=Connections(socket),
            monotonic=lambda: next(times),
        )


def test_fetch_candles_paginates_backward_and_dedups() -> None:
    page1 = FakeSocket(
        [_candles(_candle(300, 2.0, 2.1, 1.9, 2.0), _candle(360, 2.0, 2.2, 1.8, 2.1))]
    )
    page2 = FakeSocket(
        [_candles(_candle(120, 1.0, 1.1, 0.9, 1.0), _candle(180, 1.0, 1.2, 0.8, 1.1))]
    )
    result = fetch_candles(
        lambda: DEMO_URL,
        "frxEURUSD",
        granularity=60,
        total_count=4,
        connect=Connections(page1, page2),
    )

    assert [c.epoch for c in result.candles] == [120, 180, 300, 360]
    assert result.pages == 2
    assert result.discontinuities == 1


def test_fetch_candles_counts_discontinuities() -> None:
    page = FakeSocket(
        [_candles(_candle(120, 1.0, 1.1, 0.9, 1.0), _candle(300, 1.0, 1.2, 0.8, 1.0))]
    )
    result = fetch_candles(
        lambda: DEMO_URL, "frxEURUSD", granularity=60, total_count=2, connect=Connections(page)
    )

    assert result.discontinuities == 1


def test_fetch_candles_stops_early_on_deadline() -> None:
    result = fetch_candles(
        lambda: DEMO_URL,
        "frxEURUSD",
        granularity=60,
        total_count=10,
        deadline_remaining=0,
        connect=Connections(),
    )

    assert result.ended_early is True
    assert result.candles == ()
    assert result.pages == 0


def test_fetch_candles_stops_on_empty_page() -> None:
    page = FakeSocket([_candles()])
    result = fetch_candles(
        lambda: DEMO_URL, "frxEURUSD", granularity=60, total_count=10, connect=Connections(page)
    )

    assert result.candles == ()
    assert result.pages == 1
    assert result.ended_early is False


def test_fetch_candles_rejects_invalid_total_count() -> None:
    with pytest.raises(CandlesError):
        fetch_candles(
            lambda: DEMO_URL, "frxEURUSD", granularity=60, total_count=0, connect=Connections()
        )


def test_fetch_candles_rejects_invalid_granularity() -> None:
    with pytest.raises(CandlesError):
        fetch_candles(
            lambda: DEMO_URL, "frxEURUSD", granularity=0, total_count=10, connect=Connections()
        )


def test_decode_rejects_invalid() -> None:
    with pytest.raises(CandlesError):
        _decode("not json")
    with pytest.raises(CandlesError):
        _decode("[]")
    with pytest.raises(CandlesError):
        _decode(b"[]")
    with pytest.raises(CandlesError):
        _decode(b"not json")


def test_request_candles_rejects_blank_symbol() -> None:
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "  ", granularity=60, count=1, connect=Connections())


def test_request_candles_rejects_non_positive_quote() -> None:
    socket = FakeSocket([_candles(_candle(1000, 0.0, 1.5, 0.9, 1.0))])
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket))


def test_request_candles_rejects_non_list_candles() -> None:
    socket = FakeSocket([{"candles": "x"}])
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket))


class _RaisingConnections:
    def __call__(self, url: str) -> FakeSocket:
        raise RuntimeError("boom")


def test_request_candles_wraps_connection_error() -> None:
    with pytest.raises(CandlesError):
        request_candles(
            DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=_RaisingConnections()
        )


def test_fetch_candles_stops_on_non_positive_epoch() -> None:
    page = FakeSocket([_candles(_candle(0, 1.0, 1.1, 0.9, 1.0))])
    result = fetch_candles(
        lambda: DEMO_URL, "frxEURUSD", granularity=60, total_count=10, connect=Connections(page)
    )

    assert result.pages == 1
    assert [c.epoch for c in result.candles] == [0]


@pytest.mark.parametrize(
    "item",
    [
        _candle(1000, 0.8, 1.5, 0.9, 1.2),
        _candle(1000, 1.0, 1.5, 0.9, 1.6),
    ],
)
def test_request_candles_rejects_open_or_close_outside_range(item: dict[str, Any]) -> None:
    socket = FakeSocket([_candles(item)])
    with pytest.raises(CandlesError):
        request_candles(DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=Connections(socket))


def test_fetch_candles_stops_when_a_page_adds_no_new_epochs() -> None:
    repeated = _candles(_candle(120, 1.0, 1.1, 0.9, 1.0))
    result = fetch_candles(
        lambda: DEMO_URL,
        "frxEURUSD",
        granularity=60,
        total_count=2,
        connect=Connections(FakeSocket([repeated]), FakeSocket([repeated])),
    )
    assert result.pages == 2
    assert result.ended_early is True
    assert len(result.candles) == 1


def test_fetch_candles_caps_each_request_by_session_deadline() -> None:
    page = FakeSocket([_candles(_candle(120, 1.0, 1.1, 0.9, 1.0))])
    fetch_candles(
        lambda: DEMO_URL,
        "frxEURUSD",
        granularity=60,
        total_count=1,
        deadline_remaining=5,
        request_timeout_seconds=30,
        connect=Connections(page),
        monotonic=lambda: 0.0,
    )
    assert page.recv_timeouts == [5.0]


def test_request_candles_sanitizes_connection_errors() -> None:
    class SensitiveConnections:
        def __call__(self, url: str) -> FakeSocket:
            raise RuntimeError(f"failed for {url}")

    with pytest.raises(CandlesError) as captured:
        request_candles(
            DEMO_URL, "frxEURUSD", granularity=60, count=1, connect=SensitiveConnections()
        )
    assert "secret-otp" not in str(captured.value)
    assert str(captured.value) == "demo websocket failed"
