"""Clock boundary for deterministic application services."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Provide a timezone-aware current instant."""

    def now(self) -> datetime:
        """Return the current timezone-aware instant."""
        ...
