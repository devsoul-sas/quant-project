"""UTC wall clock adapter."""

from datetime import UTC, datetime


class SystemClock:
    """Read the host wall clock as a timezone-aware UTC instant."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)
