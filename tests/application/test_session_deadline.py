"""S3.10/D temporal-policy tests using injected monotonic clocks.

No test waits real time: the fake monotonic clock is advanced manually to
simulate minutes or hours of session lifetime, including the TTL boundary.
"""

from collections.abc import Callable

import pytest

from devsoul_quant.application.session_deadline import (
    MAX_SESSION_SECONDS,
    PREVENTIVE_SESSION_SECONDS,
    SessionDeadline,
    SessionDeadlineExceeded,
)


def _clock(start: float = 0.0) -> tuple[dict[str, float], Callable[[], float]]:
    state: dict[str, float] = {"now": start}

    def monotonic() -> float:
        return state["now"]

    return state, monotonic


def test_deadline_starts_before_data_and_never_resets_on_reconnect() -> None:
    state, monotonic = _clock(100.0)
    deadline = SessionDeadline(session_seconds=600, monotonic=monotonic)

    assert deadline.started == 100.0
    assert deadline.deadline == 700.0

    state["now"] = 400.0  # simulate reconnection / elapsed wall time
    assert deadline.started == 100.0
    assert deadline.remaining() == 300.0


def test_remaining_and_elapsed_clamp_at_zero() -> None:
    state, monotonic = _clock(0.0)
    deadline = SessionDeadline(session_seconds=10, monotonic=monotonic)

    state["now"] = 99.0
    assert deadline.remaining() == 0.0
    assert deadline.remaining_seconds() == 0
    assert deadline.elapsed() == 99.0


def test_ensure_open_raises_exactly_at_the_deadline() -> None:
    state, monotonic = _clock(0.0)
    deadline = SessionDeadline(session_seconds=10, monotonic=monotonic)

    state["now"] = 9.0
    deadline.ensure_open()

    state["now"] = 10.0
    with pytest.raises(SessionDeadlineExceeded):
        deadline.ensure_open()


def test_contractual_ceiling_and_preventive_cap_are_distinct() -> None:
    assert PREVENTIVE_SESSION_SECONDS == 23 * 60 * 60
    assert MAX_SESSION_SECONDS == 24 * 60 * 60


def test_session_length_must_be_strictly_below_the_24h_ceiling() -> None:
    with pytest.raises(ValueError):
        SessionDeadline(session_seconds=MAX_SESSION_SECONDS, monotonic=lambda: 0.0)
    with pytest.raises(ValueError):
        SessionDeadline(session_seconds=0, monotonic=lambda: 0.0)
    with pytest.raises(ValueError):
        SessionDeadline(session_seconds=-1, monotonic=lambda: 0.0)

    # the preventive cap is a valid session length (leaves one hour for shutdown)
    SessionDeadline(session_seconds=PREVENTIVE_SESSION_SECONDS, monotonic=lambda: 0.0)
