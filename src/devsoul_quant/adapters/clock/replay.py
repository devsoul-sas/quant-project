"""Deterministic replay clock."""

from dataclasses import dataclass
from datetime import datetime, timedelta


def _require_aware(instant: datetime) -> None:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("clock instant must be timezone-aware")


@dataclass(slots=True)
class ReplayClock:
    """Clock that moves only through explicit replay instructions."""

    _instant: datetime

    def __post_init__(self) -> None:
        _require_aware(self._instant)

    def now(self) -> datetime:
        return self._instant

    def advance(self, delta: timedelta) -> None:
        if delta < timedelta(0):
            raise ValueError("replay clock cannot move backwards")
        self._instant += delta
