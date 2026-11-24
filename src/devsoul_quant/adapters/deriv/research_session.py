"""Strictly bounded in-memory lifecycle for Deriv research state."""

from collections.abc import Callable
from typing import Literal, Self

from devsoul_quant.adapters.deriv.ephemeral import EphemeralTickCache
from devsoul_quant.domain.replay import Tick


class ExpiredResearchSession(RuntimeError):
    """Raised after session TTL expiry or explicit closure."""


class EphemeralResearchSession[ResultT]:
    """Own transient ticks/results and zeroize them at a strict TTL boundary."""

    def __init__(self, *, clock: Callable[[], int], ttl_seconds: int) -> None:
        self._clock = clock
        self._cache = EphemeralTickCache(ttl_seconds=ttl_seconds)
        self._results: list[ResultT] = []
        self._closed = False
        self._started_epoch = self._now()

    def _now(self) -> int:
        value = self._clock()
        if type(value) is not int:
            raise TypeError("research session clock must return an integer epoch")
        return value

    def _ensure_open(self) -> int:
        now = self._now()
        if self._closed:
            raise ExpiredResearchSession("research session is closed")
        if now - self._started_epoch >= self._cache.ttl_seconds:
            self.close()
            raise ExpiredResearchSession("research session expired at its TTL boundary")
        return now

    def add_tick(self, tick: Tick) -> None:
        """Store one tick after checking the total session lifetime."""
        now = self._ensure_open()
        self._cache.expire(now_epoch=now)
        self._cache.store(tick, now_epoch=now)

    def record_result(self, result: ResultT) -> None:
        """Keep one typed research result in memory for this session only."""
        self._ensure_open()
        self._results.append(result)

    @property
    def ticks(self) -> tuple[Tick, ...]:
        return self._cache.ticks

    @property
    def results(self) -> tuple[ResultT, ...]:
        return tuple(self._results)

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        """Drop all owned references without writing provider-derived state."""
        self._cache.clear()
        self._results.clear()
        self._closed = True

    def __enter__(self) -> Self:
        self._ensure_open()
        return self

    def __exit__(self, *args: object) -> Literal[False]:
        self.close()
        return False
