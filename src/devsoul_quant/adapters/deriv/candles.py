"""Read-only ``candles`` adapter for the Deriv demo WebSocket.

Fetches bounded OHLC candles (never ``buy``/``sell``) with backward pagination,
epoch deduplication, discontinuity detection and a hard session deadline. Every
payload stays in local variables; nothing is persisted.

``style="candles"`` responses carry ``candles`` as a list of objects with
``open``, ``high``, ``low``, ``close`` and ``epoch``. ``granularity`` is the
candle span in seconds (60 = M1, 300 = M5, 900 = M15).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from typing import Any

from devsoul_quant.adapters.deriv.demo_url import validate_demo_websocket_url

MAX_PAGE_COUNT = 5000
MAX_TOTAL_COUNT = 100_000
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0


class CandlesError(RuntimeError):
    """Raised when a candles request cannot complete safely."""


def _default_connect(url: str) -> Any:  # pragma: no cover - thin network wrapper
    from websockets.sync.client import connect

    return connect(url)


@dataclass(frozen=True, slots=True)
class Candle:
    """One OHLC candle."""

    epoch: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class CandlesPage:
    """One page of candles, ascending by epoch."""

    candles: tuple[Candle, ...]


@dataclass(frozen=True, slots=True)
class CandlesResult:
    """Deduplicated candles plus fetch metadata."""

    candles: tuple[Candle, ...]
    pages: int
    discontinuities: int
    ended_early: bool


def _decode(raw: object) -> Mapping[str, Any]:
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        message = json.loads(raw)  # type: ignore[arg-type]
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        raise CandlesError("Deriv returned an invalid response") from None
    if not isinstance(message, Mapping):
        raise CandlesError("Deriv returned a non-object response")
    return message


def _candle_from(value: Mapping[str, Any]) -> Candle:
    epoch = value.get("epoch")
    if type(epoch) is not int:
        raise CandlesError("Deriv candle epoch is not an integer")
    quotes: list[Decimal] = []
    for field in ("open", "high", "low", "close"):
        try:
            quote = Decimal(str(value.get(field)))
        except (InvalidOperation, ValueError):
            raise CandlesError(f"Deriv candle {field} is not numeric") from None
        if not quote.is_finite() or quote <= 0:
            raise CandlesError(f"Deriv candle {field} is not a positive finite number")
        quotes.append(quote)
    open_q, high_q, low_q, close_q = quotes
    if high_q < low_q:
        raise CandlesError("Deriv candle high is below its low")
    return Candle(epoch=epoch, open=open_q, high=high_q, low=low_q, close=close_q)


def request_candles(
    url: str,
    symbol: str,
    *,
    granularity: int,
    count: int,
    end: str | int = "latest",
    connect: Callable[[str], Any] | None = None,
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
) -> CandlesPage:
    """Request one page of ``candles`` and return it as ``Candle`` objects."""
    validate_demo_websocket_url(url)
    if not isinstance(symbol, str) or not symbol.strip():
        raise CandlesError("symbol must be a non-blank string")
    if type(granularity) is not int or granularity < 1:
        raise CandlesError("granularity must be a positive integer of seconds")
    if type(count) is not int or count < 1 or count > MAX_PAGE_COUNT:
        raise CandlesError(f"count must be within [1, {MAX_PAGE_COUNT}]")
    if not isinstance(end, (str, int)):
        raise CandlesError("end must be 'latest' or an epoch")
    connector = connect if connect is not None else _default_connect
    deadline = monotonic() + float(request_timeout_seconds)
    try:
        with connector(url) as websocket:
            websocket.send(
                json.dumps(
                    {
                        "ticks_history": symbol,
                        "granularity": granularity,
                        "count": count,
                        "end": end,
                        "style": "candles",
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise CandlesError("candles request deadline expired")
                message = _decode(websocket.recv(timeout=remaining))
                if "error" in message:
                    raise CandlesError("Deriv rejected the candles request")
                if "candles" not in message:
                    continue
                candles = message["candles"]
                if not isinstance(candles, list):
                    raise CandlesError("Deriv candles payload is malformed")
                parsed = tuple(_candle_from(item) for item in candles if isinstance(item, Mapping))
                return CandlesPage(candles=parsed)
    except CandlesError:
        raise
    except Exception as error:
        raise CandlesError(f"demo websocket failed: {error}") from error


def fetch_candles(
    resolve_url: Callable[[], str],
    symbol: str,
    *,
    granularity: int,
    total_count: int,
    deadline_remaining: float | None = None,
    connect: Callable[[str], Any] | None = None,
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
) -> CandlesResult:
    """Fetch up to ``total_count`` unique candles with backward pagination."""
    if type(total_count) is not int or total_count < 1 or total_count > MAX_TOTAL_COUNT:
        raise CandlesError(f"total_count must be within [1, {MAX_TOTAL_COUNT}]")
    if type(granularity) is not int or granularity < 1:
        raise CandlesError("granularity must be a positive integer of seconds")
    deadline = None if deadline_remaining is None else monotonic() + float(deadline_remaining)
    by_epoch: dict[int, Candle] = {}
    pages = 0
    end: str | int = "latest"
    ended_early = False
    while len(by_epoch) < total_count:
        if deadline is not None and monotonic() >= deadline:
            ended_early = True
            break
        page = request_candles(
            resolve_url(),
            symbol,
            granularity=granularity,
            count=min(total_count - len(by_epoch), MAX_PAGE_COUNT),
            end=end,
            connect=connect,
            request_timeout_seconds=request_timeout_seconds,
            monotonic=monotonic,
        )
        pages += 1
        if not page.candles:
            break
        for candle in page.candles:
            by_epoch.setdefault(candle.epoch, candle)
        oldest = min(candle.epoch for candle in page.candles)
        if oldest <= 0:
            break
        end = oldest - 1
    candles = tuple(sorted(by_epoch.values(), key=lambda candle: candle.epoch))
    discontinuities = 0
    for previous, current in pairwise(candles):
        if current.epoch - previous.epoch > granularity:
            discontinuities += 1
    return CandlesResult(
        candles=candles,
        pages=pages,
        discontinuities=discontinuities,
        ended_early=ended_early,
    )
