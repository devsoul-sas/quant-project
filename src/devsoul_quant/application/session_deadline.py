"""Centralized monotonic session deadline (S3.10 phase D).

A single monotonic deadline coordinates every blocking operation so that tick
collection, quoting and reconnection can never silently run past the global
session bound. The contractual 24-hour ceiling is a hard exclusive maximum
(``MAX_SESSION_SECONDS``); the preventive 23-hour cap (``PREVENTIVE_SESSION_SECONDS``)
is the default operational limit and leaves one hour for final evaluation and
cleanup.

The session clock starts the moment the deadline is created, i.e. before the
first data request, and is never reset by reconnection, copying or structure
changes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

MAX_SESSION_SECONDS: Final = 24 * 60 * 60
PREVENTIVE_SESSION_SECONDS: Final = 23 * 60 * 60


class SessionDeadlineExceeded(RuntimeError):
    """Raised when an operation would run past the session deadline."""


class SessionDeadline:
    """Fail-closed monotonic deadline for one bounded research session."""

    def __init__(self, *, session_seconds: int, monotonic: Callable[[], float]) -> None:
        if type(session_seconds) is not int or not 1 <= session_seconds < MAX_SESSION_SECONDS:
            raise ValueError(f"session_seconds must be within [1, {MAX_SESSION_SECONDS})")
        self._monotonic = monotonic
        self._started = monotonic()
        self._deadline = self._started + session_seconds

    @property
    def started(self) -> float:
        return self._started

    @property
    def deadline(self) -> float:
        return self._deadline

    def elapsed(self) -> float:
        return max(0.0, self._monotonic() - self._started)

    def remaining(self) -> float:
        return max(0.0, self._deadline - self._monotonic())

    def remaining_seconds(self) -> int:
        return int(self.remaining())

    def ensure_open(self) -> None:
        if self._monotonic() >= self._deadline:
            raise SessionDeadlineExceeded("session deadline elapsed")
