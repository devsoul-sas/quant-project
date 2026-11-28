"""Async demo WebSocket client that collects ephemeral ticks.

Connects only to a validated one-time-password demo URL (never ``/ws/real``),
collects a bounded number of ticks into memory, and releases the subscription.
Nothing is persisted: the returned ticks live only as long as the caller holds
them, subject to the ephemeral cache window enforced elsewhere.

The demo OTP WebSocket has a short server-side lifetime and drops the connection
abruptly (close code 1006) after ~120 s unless the client sends a keepalive
``{"ping": 1}`` frame. ``_collect_once`` therefore runs a periodic heartbeat while
collecting. A connection that still ends before ``remaining`` ticks (a clean or
abrupt close) is treated as a normal end of the connection so a resilient caller
can reconnect with a fresh OTP URL. Provider error messages and invalid payloads
still raise.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable, Mapping
from contextlib import suppress
from typing import Any

from websockets.exceptions import ConnectionClosed

from devsoul_quant.adapters.deriv.demo_url import validate_demo_websocket_url
from devsoul_quant.adapters.deriv.ephemeral import EphemeralTickCache, parse_deriv_tick
from devsoul_quant.domain.replay import Tick

MAX_TICK_COUNT = 10_000
MAX_COLLECTION_SECONDS = 60 * 60
DEFAULT_HEARTBEAT_SECONDS = 30


class DerivClientError(RuntimeError):
    """Raised when the demo WebSocket flow cannot complete safely."""


class CollectionTimeout(DerivClientError):
    """Raised when a bounded collection window elapses without a deadline expiry.

    A genuine stall (the feed stops producing ticks and reconnection cannot
    complete within the full per-batch window) is a failure. A deadline-driven
    end to the final batch is NOT: that is handled by returning the partial
    ticks already cached so the caller can evaluate them normally.
    """


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


def _validate_heartbeat(heartbeat_seconds: int) -> None:
    if type(heartbeat_seconds) is not int or heartbeat_seconds < 0:
        raise DerivClientError("heartbeat_seconds must be a non-negative integer")


def _collection_timeout(deadline_remaining: float | None) -> float:
    """Cap collection time by the session deadline, never above the hard bound."""
    if deadline_remaining is None:
        return MAX_COLLECTION_SECONDS
    if (
        isinstance(deadline_remaining, bool)
        or not isinstance(deadline_remaining, (int, float))
        or deadline_remaining <= 0
    ):
        raise DerivClientError("deadline_remaining must be a positive number")
    return min(float(MAX_COLLECTION_SECONDS), float(deadline_remaining))


async def _collect_once(
    url: str,
    symbol: str,
    *,
    remaining: int,
    connector: Callable[..., Any],
    now: Callable[[], int],
    cache: EphemeralTickCache,
    heartbeat_seconds: int = DEFAULT_HEARTBEAT_SECONDS,
    sleep: Callable[[float], Any] = asyncio.sleep,
) -> int:
    """Collect up to ``remaining`` ticks from one connection and return the count.

    A connection that ends before ``remaining`` ticks (a clean or abrupt close) is
    treated as a normal end of the connection so a resilient caller can reconnect
    with a fresh OTP URL. Provider error messages and invalid payloads still raise.

    While collecting, a periodic ``{"ping": 1}`` keepalive is sent so the demo
    server does not drop the connection for lack of client activity.
    """
    received = 0
    subscription_id: str | None = None
    try:
        async with connector(url) as websocket:
            await websocket.send(json.dumps({"ticks": symbol, "subscribe": 1}))

            async def _heartbeat() -> None:
                while True:
                    await sleep(heartbeat_seconds)
                    await websocket.send(json.dumps({"ping": 1}))

            heartbeat_task = asyncio.create_task(_heartbeat()) if heartbeat_seconds > 0 else None
            try:
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
            finally:
                if heartbeat_task is not None:
                    heartbeat_task.cancel()
                    with suppress(asyncio.CancelledError, ConnectionClosed):
                        await heartbeat_task

            if subscription_id is not None:
                await websocket.send(json.dumps({"forget": subscription_id}))
            else:
                await websocket.send(json.dumps({"forget_all": "ticks"}))
    except ConnectionClosed:
        return received
    except DerivClientError:
        raise
    except Exception:
        raise DerivClientError("demo websocket failed") from None
    return received


async def collect_ticks(
    url: str,
    symbol: str,
    *,
    count: int,
    connect: Callable[..., Any] | None = None,
    clock: Callable[[], int] | None = None,
    heartbeat_seconds: int = DEFAULT_HEARTBEAT_SECONDS,
    sleep: Callable[[float], Any] = asyncio.sleep,
    deadline_remaining: float | None = None,
) -> tuple[Tick, ...]:
    """Collect ``count`` ticks from a single demo connection and release it."""
    validate_demo_websocket_url(url)
    _validate(symbol, count)
    _validate_heartbeat(heartbeat_seconds)

    connector = connect if connect is not None else _default_connect
    now = clock if clock is not None else lambda: int(time.time())
    cache = EphemeralTickCache()
    try:
        async with asyncio.timeout(_collection_timeout(deadline_remaining)):
            received = await _collect_once(
                url,
                symbol,
                remaining=count,
                connector=connector,
                now=now,
                cache=cache,
                heartbeat_seconds=heartbeat_seconds,
                sleep=sleep,
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
    heartbeat_seconds: int = DEFAULT_HEARTBEAT_SECONDS,
    sleep: Callable[[float], Any] = asyncio.sleep,
    deadline_remaining: float | None = None,
    reconnections: list[int] | None = None,
) -> tuple[Tick, ...]:
    """Collect ``count`` ticks across as many OTP connections as needed.

    The demo OTP WebSocket has a short server-side lifetime, so a single connection
    can drop before ``count`` is reached. This reconnects with a fresh OTP URL and
    accumulates strictly newer ticks until ``count`` is reached or the overall
    collection deadline elapses.

    When the deadline (bounded by ``deadline_remaining``) elapses mid-batch, the
    ticks already cached are returned rather than raising, so the caller can
    evaluate the valid observations collected before the session bound. A genuine
    stall — the full per-batch window elapses while the deadline is still open —
    raises :class:`CollectionTimeout`. The number of reconnections (fresh OTP URLs
    beyond the first) is appended to ``reconnections`` when provided.
    """
    _validate(symbol, count)
    _validate_heartbeat(heartbeat_seconds)

    connector = connect if connect is not None else _default_connect
    now = clock if clock is not None else lambda: int(time.time())
    cache = EphemeralTickCache()
    collected = 0
    reconnects = 0
    try:
        async with asyncio.timeout(_collection_timeout(deadline_remaining)):
            while collected < count:
                url = resolve_url()
                validate_demo_websocket_url(url)
                reconnects += 1
                collected += await _collect_once(
                    url,
                    symbol,
                    remaining=count - collected,
                    connector=connector,
                    now=now,
                    cache=cache,
                    heartbeat_seconds=heartbeat_seconds,
                    sleep=sleep,
                )
    except TimeoutError:
        if deadline_remaining is not None and deadline_remaining < MAX_COLLECTION_SECONDS:
            # The session deadline elapsed mid-batch: a normal, bounded end.
            pass
        else:
            raise CollectionTimeout(
                "demo websocket collection timed out before the deadline"
            ) from None
    finally:
        if reconnections is not None:
            reconnections.append(max(0, reconnects - 1))
        ticks = cache.ticks
        cache.clear()
    return ticks
