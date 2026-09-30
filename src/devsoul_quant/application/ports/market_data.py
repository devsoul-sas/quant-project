"""Licensed market-data application boundary."""

from dataclasses import dataclass
from typing import Protocol

from devsoul_quant.domain.replay import EconomyProvenance, Tick


def _require_non_blank(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string")


@dataclass(frozen=True, slots=True)
class MarketDataBatch:
    """Ticks with explicit source, license reference, and provenance."""

    source: str
    license_reference: str
    provenance: EconomyProvenance
    ticks: tuple[Tick, ...]

    def __post_init__(self) -> None:
        _require_non_blank(self.source, "source")
        _require_non_blank(self.license_reference, "license_reference")


class MarketDataPort(Protocol):
    """Load a provider-neutral, provenance-labelled tick batch."""

    def load_ticks(self, *, symbol: str, count: int) -> MarketDataBatch: ...
