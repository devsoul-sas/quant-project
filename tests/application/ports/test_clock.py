from datetime import UTC, datetime, timedelta

import pytest

from devsoul_quant.adapters.clock.replay import ReplayClock
from devsoul_quant.adapters.clock.system import SystemClock


def test_system_clock_returns_a_timezone_aware_utc_instant() -> None:
    instant = SystemClock().now()

    assert instant.tzinfo is UTC


def test_replay_clock_returns_the_known_utc_instant() -> None:
    instant = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
    clock = ReplayClock(instant)

    assert clock.now() == instant
    assert clock.now() == instant


def test_replay_clock_advances_only_when_explicitly_requested() -> None:
    instant = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
    clock = ReplayClock(instant)

    clock.advance(timedelta(seconds=3))

    assert clock.now() == instant + timedelta(seconds=3)


@pytest.mark.parametrize(
    ("instant", "delta", "message"),
    [
        (datetime(2026, 9, 30, 15, 0), None, "timezone-aware"),
        (datetime(2026, 9, 30, 15, 0, tzinfo=UTC), timedelta(seconds=-1), "backwards"),
    ],
)
def test_replay_clock_rejects_unsafe_time(
    instant: datetime,
    delta: timedelta | None,
    message: str,
) -> None:
    if delta is None:
        with pytest.raises(ValueError, match=message):
            ReplayClock(instant)
        return

    clock = ReplayClock(instant)
    with pytest.raises(ValueError, match=message):
        clock.advance(delta)
