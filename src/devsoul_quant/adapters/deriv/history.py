"""Read-only ``ticks_history`` adapter for the Deriv demo WebSocket.

Fetches bounded historical ticks (never ``buy``/``sell``) with backward
pagination, epoch deduplication, discontinuity detection and a hard session
deadline. Every payload stays in local variables; nothing is persisted.

``style="ticks"`` responses carry ``history.prices`` and ``history.times``. The
observed per-request cap is 2000 ticks; the caller pages backward with
``end=<oldest_epoch - 1>`` until the requested unique count is reached, the feed
is exhausted, or the deadline elapses.
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
from devsoul_quant.domain.replay import Tick

MAX_PAGE_COUNT = 2000
MAX_TOTAL_COUNT = 100_000
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0


class HistoryError(RuntimeError):
    """Raised when a ticks_history request cannot complete safely."""


def _default_connect(url: str) -> Any:
    from websockets.sync.client import connect

    return connect(url)


@dataclass(frozen=True, slots=True)
class HistoryPage:
    """One page of historical ticks, ascending by epoch."""

    ticks: tuple[Tick, ...]
    pip_size: int | None


@dataclass(frozen=True, slots=True)
class HistoryResult:
    """Deduplicated historical ticks plus fetch metadata."""

    ticks: tuple[Tick, ...]
    pages: int
    discontinuities: int
    ended_early: bool


def _parse_pip_size(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    return None


def _decode(raw: object) -> Mapping[str, Any]:
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        message = json.loads(raw)  # type: ignore[arg-type]
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        raise HistoryError("Deriv returned an invalid response") from None
    if not isinstance(message, Mapping):
        raise HistoryError("Deriv returned a non-object response")
    return message


def request_ticks_history(
    url: str,
    symbol: str,
    *,
    count: int,
    end: str | int = "latest",
    connect: Callable[[str], Any] | None = None,
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
) -> HistoryPage:
    """Request one page of ``ticks_history`` and return it as ``Tick`` objects."""
    validate_demo_websocket_url(url)
    if not isinstance(symbol, str) or not symbol.strip():
        raise HistoryError("symbol must be a non-blank string")
    if type(count) is not int or count < 1 or count > MAX_PAGE_COUNT:
        raise HistoryError(f"count must be within [1, {MAX_PAGE_COUNT}]")
    if not isinstance(end, (str, int)):
        raise HistoryError("end must be 'latest' or an epoch")
    connector = connect if connect is not None else _default_connect
    deadline = monotonic() + float(request_timeout_seconds)
    try:
        with connector(url) as websocket:
            websocket.send(
                json.dumps(
                    {"ticks_history": symbol, "count": count, "end": end, "style": "ticks"},
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise HistoryError("ticks_history request deadline expired")
                message = _decode(websocket.recv(timeout=remaining))
                if "error" in message:
                    raise HistoryError("Deriv rejected the ticks_history request")
                if "history" not in message:
                    continue
                history = message["history"]
                if not isinstance(history, Mapping):
                    raise HistoryError("Deriv ticks_history payload is malformed")
                prices = history.get("prices")
                times = history.get("times")
                if not isinstance(prices, list) or not isinstance(times, list):
                    raise HistoryError("Deriv ticks_history is missing prices or times")
                if len(prices) != len(times):
                    raise HistoryError("Deriv ticks_history prices and times mismatch")
                pip_size = _parse_pip_size(message.get("pip_size"))
                ticks: list[Tick] = []
                for price, epoch in zip(prices, times, strict=True):
                    if type(epoch) is not int:
                        raise HistoryError("Deriv tick epoch is not an integer")
                    try:
                        quote = Decimal(str(price))
                    except (InvalidOperation, ValueError):
                        raise HistoryError("Deriv tick quote is not numeric") from None
                    if not quote.is_finite() or quote <= 0:
                        raise HistoryError("Deriv tick quote is not a positive finite number")
                    ticks.append(Tick(epoch=epoch, quote=quote, pip_size=pip_size))
                return HistoryPage(ticks=tuple(ticks), pip_size=pip_size)
    except HistoryError:
        raise
    except Exception:
        # Transport errors may include the authenticated OTP URL. Never surface
        # provider exception text or preserve it as a chained traceback.
        raise HistoryError("demo websocket failed") from None


def fetch_ticks_history(
    resolve_url: Callable[[], str],
    symbol: str,
    *,
    total_count: int,
    cadence_seconds: int = 1,
    deadline_remaining: float | None = None,
    connect: Callable[[str], Any] | None = None,
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
) -> HistoryResult:
    """Fetch up to ``total_count`` unique ticks with backward pagination.

    Pages backward from the latest tick, deduplicates by epoch, and stops early
    when the feed is exhausted or ``deadline_remaining`` elapses. Discontinuities
    (epoch gaps wider than ``cadence_seconds``) are counted but not dropped.
    """
    if type(total_count) is not int or total_count < 1 or total_count > MAX_TOTAL_COUNT:
        raise HistoryError(f"total_count must be within [1, {MAX_TOTAL_COUNT}]")
    if type(cadence_seconds) is not int or cadence_seconds < 1:
        raise HistoryError("cadence_seconds must be a positive integer")
    deadline = None if deadline_remaining is None else monotonic() + float(deadline_remaining)
    by_epoch: dict[int, Tick] = {}
    pages = 0
    end: str | int = "latest"
    ended_early = False
    while len(by_epoch) < total_count:
        request_timeout = request_timeout_seconds
        if deadline is not None:
            remaining = deadline - monotonic()
            if remaining <= 0:
                ended_early = True
                break
            request_timeout = min(request_timeout_seconds, remaining)
        page = request_ticks_history(
            resolve_url(),
            symbol,
            count=min(total_count - len(by_epoch), MAX_PAGE_COUNT),
            end=end,
            connect=connect,
            request_timeout_seconds=request_timeout,
            monotonic=monotonic,
        )
        pages += 1
        if not page.ticks:
            break
        previous_count = len(by_epoch)
        for tick in page.ticks:
            by_epoch.setdefault(tick.epoch, tick)
        if len(by_epoch) == previous_count:
            ended_early = True
            break
        oldest = min(tick.epoch for tick in page.ticks)
        if oldest <= 0:
            break
        end = oldest - 1
    ticks = tuple(sorted(by_epoch.values(), key=lambda tick: tick.epoch))
    discontinuities = 0
    for previous, current in pairwise(ticks):
        if current.epoch - previous.epoch > cadence_seconds:
            discontinuities += 1
    return HistoryResult(
        ticks=ticks,
        pages=pages,
        discontinuities=discontinuities,
        ended_early=ended_early,
    )
