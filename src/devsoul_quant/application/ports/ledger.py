"""Append-only ledger application boundary."""

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from devsoul_quant.domain.ledger import LedgerEvent, LedgerScalar


@runtime_checkable
class LedgerPort(Protocol):
    """Store and verify own-domain events without exposing mutation."""

    @property
    def events(self) -> Sequence[LedgerEvent]: ...

    def append(
        self,
        *,
        event_id: str,
        event_type: str,
        occurred_at: int,
        correlation_id: str,
        causation_id: str | None,
        payload: Mapping[str, LedgerScalar],
    ) -> LedgerEvent: ...

    def verify(self) -> bool: ...
