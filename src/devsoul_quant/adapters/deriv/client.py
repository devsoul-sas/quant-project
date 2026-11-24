"""Async demo WebSocket client that collects ephemeral ticks.

Connects only to a validated one-time-password demo URL (never ``/ws/real``),
collects a bounded number of ticks into memory, and releases the subscription.
Nothing is persisted: the returned ticks live only as long as the caller holds
them, subject to the ephemeral cache window enforced elsewhere.

The demo OTP WebSocket has a short server-side lifetime, so a single connection
can drop before the requested number of ticks arrives. ``collect_ticks_resilient``
reconnects with a fresh OTP URL until the count is reached, while ``collect_ticks``
keeps the single-connection semantics for callers that only need a small window.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable, Mapping
from typing import Any

from websockets.exceptions import ConnectionClosed

from devsoul_quant.adapters.deriv.demo_url import validate_demo_websocket_url
from devsoul_quant.adapters.deriv.ephemeral import EphemeralTickCache, parse_deriv_tick
from devsoul_quant.domain.replay import Tick

MAX_TICK_COUNT = 10_000
MAX_COLLECTION_SECONDS = 60 * 60


class DerivClientError(RuntimeError):
    """Raised when the demo WebSocket flow cannot complete safely."""


def _default_connect(url: str) -> Any:
    import websockets

    return websockets.connect(url)


def _as_text(raw: Any) -> str:
    return raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw


def _subscription_id(message: Mapping[str, Any]) -> str:
    subscription = message.get("subscription")
    if isinstance(subscription, Mapping):
        identifier = subscription.get("id")
        if isinstance(identifier, str) and identifier:
            return identifier
    raise DerivClientError("subscription acknowledgement is missing an id")


def _validate(symbol: str, count: int) -> None:
    if not isinstance(symbol, str) or not symbol.strip():
        raise DerivClientError("symbol must be a non-blank string")
    if type(count) is not int or count < 1:
        raise DerivClientError("count must be a positive integer")
    if count > MAX_TICK_COUNT:
        raise DerivClientError(f"count must be at most {MAX_TICK_COUNT}")


async def _collect_once(
    url: str,
    symbol: str,
    *,
    remaining: int,
    connector: Callable[..., Any],
    now: Callable[[], int],
    cache: EphemeralTickCache,
) -> int:
    """Collect up to ``remaining`` ticks from one connection and return the count.

    A connection that ends before ``remaining`` ticks (a clean or abrupt close) is
    treated as a normal end of the connection so a resilient caller can reconnect
    with a fresh OTP URL. Provider error messages and invalid payloads still raise.
    """
    received = 0
    subscription_id: str | None = None
    try:
        async with connector(url) as websocket:
            await websocket.send(json.dumps({"ticks": symbol, "subscribe": 1}))
            async for raw in websocket:
                message = json.loads(_as_text(raw))
                if "error" in message:
                    raise DerivClientError(f"deriv returned an error: {message['error']}")
                if "subscription" in message and subscription_id is None:
                    subscription_id = _subscription_id(message)
                    continue
                if "tick" in message:
                    tick = parse_deriv_tick(message)
                    receipt_epoch = max(now(), tick.epoch)
                    cache.store(tick, now_epoch=receipt_epoch)
                    cache.expire(now_epoch=receipt_epoch)
                    received += 1
                    if received >= remaining:
                        break
            if subscription_id is not None:
                await websocket.send(json.dumps({"forget": subscription_id}))
            else:
                await websocket.send(json.dumps({"forget_all": "ticks"}))
    except ConnectionClosed:
        return received
    except DerivClientError:
        raise
    except Exception as error:
        raise DerivClientError(f"demo websocket failed: {error}") from error
    return received


async def collect_ticks(
    url: str,
    symbol: str,
    *,
    count: int,
    connect: Callable[..., Any] | None = None,
    clock: Callable[[], int] | None = None,
) -> tuple[Tick, ...]:
    """Collect ``count`` ticks from a single demo connection and release it."""
    validate_demo_websocket_url(url)
    _validate(symbol, count)

    connector = connect if connect is not None else _default_connect
    now = clock if clock is not None else lambda: int(time.time())
    cache = EphemeralTickCache()
    try:
        async with asyncio.timeout(MAX_COLLECTION_SECONDS):
            received = await _collect_once(
                url, symbol, remaining=count, connector=connector, now=now, cache=cache
            )
        if received < count:
            raise DerivClientError(f"demo connection ended before {count} ticks were collected")
        return cache.ticks
    except TimeoutError:
        raise DerivClientError("demo websocket collection timed out") from None
    finally:
        cache.clear()


async def collect_ticks_resilient(
    resolve_url: Callable[[], str],
    symbol: str,
    *,
    count: int,
    connect: Callable[..., Any] | None = None,
    clock: Callable[[], int] | None = None,
) -> tuple[Tick, ...]:
    """Collect ``count`` ticks across as many OTP connections as needed.

    The demo OTP WebSocket has a short server-side lifetime, so a single connection
    can drop before ``count`` is reached. This reconnects with a fresh OTP URL and
    accumulates strictly newer ticks until ``count`` is reached or the overall
    collection deadline elapses.
    """
    _validate(symbol, count)

    connector = connect if connect is not None else _default_connect
    now = clock if clock is not None else lambda: int(time.time())
    cache = EphemeralTickCache()
    collected = 0
    try:
        async with asyncio.timeout(MAX_COLLECTION_SECONDS):
            while collected < count:
                url = resolve_url()
                validate_demo_websocket_url(url)
                collected += await _collect_once(
                    url,
                    symbol,
                    remaining=count - collected,
                    connector=connector,
                    now=now,
                    cache=cache,
                )
        return cache.ticks
    except TimeoutError:
        raise DerivClientError("demo websocket collection timed out") from None
    finally:
        cache.clear()
