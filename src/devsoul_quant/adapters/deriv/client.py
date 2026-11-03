"""Async demo WebSocket client that collects ephemeral ticks.

Connects only to a validated one-time-password demo URL (never ``/ws/real``),
collects a bounded number of ticks into memory, and releases the subscription.
Nothing is persisted: the returned ticks live only as long as the caller holds
them, subject to the ephemeral cache window enforced elsewhere.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable, Mapping
from typing import Any

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


async def collect_ticks(
    url: str,
    symbol: str,
    *,
    count: int,
    connect: Callable[..., Any] | None = None,
    clock: Callable[[], int] | None = None,
) -> tuple[Tick, ...]:
    """Collect ``count`` ticks from the demo feed and release the subscription."""
    validate_demo_websocket_url(url)
    if not isinstance(symbol, str) or not symbol.strip():
        raise DerivClientError("symbol must be a non-blank string")
    if type(count) is not int or count < 1:
        raise DerivClientError("count must be a positive integer")
    if count > MAX_TICK_COUNT:
        raise DerivClientError(f"count must be at most {MAX_TICK_COUNT}")

    connector = connect if connect is not None else _default_connect
    now = clock if clock is not None else lambda: int(time.time())
    cache = EphemeralTickCache()
    received = 0
    subscription_id: str | None = None
    try:
        async with asyncio.timeout(MAX_COLLECTION_SECONDS):
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
                        if received >= count:
                            break
                if subscription_id is not None:
                    await websocket.send(json.dumps({"forget": subscription_id}))
                else:
                    await websocket.send(json.dumps({"forget_all": "ticks"}))
        return cache.ticks
    except TimeoutError:
        raise DerivClientError("demo websocket collection timed out") from None
    except DerivClientError:
        raise
    except Exception as error:
        raise DerivClientError(f"demo websocket failed: {error}") from error
    finally:
        cache.clear()
