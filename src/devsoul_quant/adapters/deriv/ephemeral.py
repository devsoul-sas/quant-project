"""Ephemeral (<24h) in-memory tick handling for the Deriv demo feed.

Implements the API Users Terms 2.1-2.4 cache window: feed content may be cached
for a maximum of 24 hours from the request and must never be persisted to disk.
The default TTL applies the 23-hour operational margin required by ADR-005.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from devsoul_quant.domain.replay import InvalidTick, Tick

MAX_CACHE_SECONDS = 24 * 60 * 60
OPERATIONAL_MARGIN_SECONDS = 23 * 60 * 60


class InvalidEphemeralConfig(ValueError):
    """Raised when a cache TTL or timestamp falls outside the permitted window."""


class InvalidDerivTick(ValueError):
    """Raised when a Deriv tick message cannot be parsed safely."""


class EphemeralTickCache:
    """In-memory tick cache that expires entries and never persists them."""

    def __init__(self, *, ttl_seconds: int = OPERATIONAL_MARGIN_SECONDS) -> None:
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds < MAX_CACHE_SECONDS:
            raise InvalidEphemeralConfig(f"ttl_seconds must be within [1, {MAX_CACHE_SECONDS})")
        self.ttl_seconds = ttl_seconds
        self._entries: list[tuple[int, Tick]] = []

    def store(self, tick: Tick, *, now_epoch: int) -> None:
        """Cache one tick received at ``now_epoch``, rejecting future timestamps."""
        if type(now_epoch) is not int:
            raise InvalidEphemeralConfig("now_epoch must be an integer")
        if tick.epoch > now_epoch:
            raise InvalidTick("tick epoch must not be in the future")
        self._entries.append((now_epoch, tick))

    def expire(self, *, now_epoch: int) -> int:
        """Drop entries cached longer than the TTL and return the dropped count."""
        if type(now_epoch) is not int:
            raise InvalidEphemeralConfig("now_epoch must be an integer")
        cutoff = now_epoch - self.ttl_seconds
        kept = [entry for entry in self._entries if entry[0] > cutoff]
        dropped = len(self._entries) - len(kept)
        self._entries = kept
        return dropped

    @property
    def ticks(self) -> tuple[Tick, ...]:
        """Return the currently cached ticks in receipt order."""
        return tuple(tick for _, tick in self._entries)

    def clear(self) -> None:
        """Discard every cached tick without any on-disk write."""
        self._entries = []

    def __len__(self) -> int:
        return len(self._entries)


def parse_deriv_tick(message: Mapping[str, object]) -> Tick:
    """Parse one Deriv ``ticks`` subscription message into an owned Tick."""
    if not isinstance(message, Mapping):
        raise InvalidDerivTick("tick message must be an object")
    payload = message.get("tick")
    if not isinstance(payload, Mapping):
        raise InvalidDerivTick("tick message must contain a tick object")
    epoch = payload.get("epoch")
    if type(epoch) is not int:
        raise InvalidDerivTick("tick epoch must be an integer")
    quote = payload.get("quote")
    try:
        quote_decimal = Decimal(str(quote))
    except (InvalidOperation, ValueError):
        raise InvalidDerivTick("tick quote must be numeric") from None
    if not quote_decimal.is_finite():
        raise InvalidDerivTick("tick quote must be finite")
    return Tick(epoch=epoch, quote=quote_decimal)
