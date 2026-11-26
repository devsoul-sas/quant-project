"""Declarative provider constraints and storage routing for the data layer.

The research and backtest layers must know, per provider, whether its ticks may
be retained and for how long, without special-casing provider names in code.
Constraints are declared as data:

- ``retention_seconds`` is ``None`` for unlimited persistence, ``0`` for
  in-memory-only (ephemeral, zeroized on close), and ``0 < N < 86400`` for
  bounded retention that must be deleted before the 24-hour mark.
- Deriv is registered as ephemeral-only; DevSoul synthetic is persistable.
"""

from dataclasses import dataclass
from enum import StrEnum

from devsoul_quant.domain.data_rights import DERIV_SOURCE_ID, DataSourceKind

_MAX_RETENTION_SECONDS = 86_400
_DEVSOUL_SYNTHETIC_ID = "devsoul-synthetic"


class InvalidProviderConstraints(ValueError):
    """Raised when provider constraints cannot fail safely."""


class UnknownProvider(ValueError):
    """Raised when no provider is registered for a source identifier."""


class StorageDisposition(StrEnum):
    """Whether a provider's ticks may be stored at all."""

    PERSIST = "PERSIST"
    EPHEMERAL = "EPHEMERAL"


@dataclass(frozen=True, slots=True)
class ProviderConstraints:
    """Declared data-availability and retention constraints for one provider."""

    source_id: str
    source_kind: DataSourceKind
    retention_seconds: int | None
    historical_available: bool
    live_available: bool

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise InvalidProviderConstraints("source_id must be a non-blank string")
        if not isinstance(self.source_kind, DataSourceKind):
            raise InvalidProviderConstraints("source_kind must be a DataSourceKind")
        retention = self.retention_seconds
        if retention is not None and (
            type(retention) is not int or retention < 0 or retention >= _MAX_RETENTION_SECONDS
        ):
            raise InvalidProviderConstraints(
                "retention_seconds must be None or an integer strictly below 24 hours"
            )
        for name in ("historical_available", "live_available"):
            if type(getattr(self, name)) is not bool:
                raise InvalidProviderConstraints(f"{name} must be a boolean")

    def storage_disposition(self) -> StorageDisposition:
        """Return EPHEMERAL when no retention is allowed, PERSIST otherwise."""
        if self.retention_seconds == 0:
            return StorageDisposition.EPHEMERAL
        return StorageDisposition.PERSIST


DEVSOUL_SYNTHETIC_PROVIDER = ProviderConstraints(
    source_id=_DEVSOUL_SYNTHETIC_ID,
    source_kind=DataSourceKind.DEVSOUL_SYNTHETIC,
    retention_seconds=None,
    historical_available=True,
    live_available=False,
)

DERIV_PROVIDER = ProviderConstraints(
    source_id=DERIV_SOURCE_ID,
    source_kind=DataSourceKind.LICENSED_EXTERNAL,
    retention_seconds=0,
    historical_available=False,
    live_available=True,
)

_REGISTRY: tuple[ProviderConstraints, ...] = (
    DEVSOUL_SYNTHETIC_PROVIDER,
    DERIV_PROVIDER,
)


def provider_constraints(source_id: str) -> ProviderConstraints:
    """Look up the registered constraints for a source identifier."""
    for constraints in _REGISTRY:
        if constraints.source_id == source_id:
            return constraints
    raise UnknownProvider(f"no provider registered for source_id {source_id!r}")


def registered_source_ids() -> tuple[str, ...]:
    """Return the registered source identifiers in declaration order."""
    return tuple(constraints.source_id for constraints in _REGISTRY)
