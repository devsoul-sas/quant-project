"""Append-only, tamper-evident ledger for DevSoul-owned events."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

type LedgerScalar = str | int | bool | None
GENESIS_HASH = "0" * 64


class DuplicateEvent(ValueError):
    """Raised when idempotency rejects an existing event identifier."""


def _require_non_blank(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string")


def _validate_payload(payload: Mapping[str, LedgerScalar]) -> None:
    for key, value in payload.items():
        _require_non_blank(key, "payload key")
        if value is not None and type(value) not in {str, int, bool}:
            raise ValueError("payload values must be JSON ledger scalars")


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    """One immutable event linked to the previous event hash."""

    sequence: int
    event_id: str
    event_type: str
    occurred_at: int
    correlation_id: str
    causation_id: str | None
    payload: Mapping[str, LedgerScalar]
    previous_hash: str
    event_hash: str

    def canonical_json(self) -> str:
        """Return the exact canonical envelope that was hashed."""
        return _canonical_json(
            sequence=self.sequence,
            event_id=self.event_id,
            event_type=self.event_type,
            occurred_at=self.occurred_at,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            payload=self.payload,
            previous_hash=self.previous_hash,
        )


def _canonical_json(
    *,
    sequence: int,
    event_id: str,
    event_type: str,
    occurred_at: int,
    correlation_id: str,
    causation_id: str | None,
    payload: Mapping[str, LedgerScalar],
    previous_hash: str,
) -> str:
    return json.dumps(
        {
            "causation_id": causation_id,
            "correlation_id": correlation_id,
            "event_id": event_id,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "payload": dict(payload),
            "previous_hash": previous_hash,
            "sequence": sequence,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _event_hash(
    *,
    sequence: int,
    event_id: str,
    event_type: str,
    occurred_at: int,
    correlation_id: str,
    causation_id: str | None,
    payload: Mapping[str, LedgerScalar],
    previous_hash: str,
) -> str:
    canonical = _canonical_json(
        sequence=sequence,
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at,
        correlation_id=correlation_id,
        causation_id=causation_id,
        payload=payload,
        previous_hash=previous_hash,
    )
    return sha256(canonical.encode()).hexdigest()


class InMemoryLedger:
    """Append-only in-memory ledger used by deterministic synthetic runs."""

    def __init__(self) -> None:
        self._events: list[LedgerEvent] = []
        self._event_ids: set[str] = set()

    @property
    def events(self) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)

    def append(
        self,
        *,
        event_id: str,
        event_type: str,
        occurred_at: int,
        correlation_id: str,
        causation_id: str | None,
        payload: Mapping[str, LedgerScalar],
    ) -> LedgerEvent:
        _require_non_blank(event_id, "event_id")
        _require_non_blank(event_type, "event_type")
        if type(occurred_at) is not int:
            raise ValueError("occurred_at must be an integer")
        _require_non_blank(correlation_id, "correlation_id")
        if causation_id is not None:
            _require_non_blank(causation_id, "causation_id")
        _validate_payload(payload)
        if event_id in self._event_ids:
            existing = next(event for event in self._events if event.event_id == event_id)
            if (
                existing.event_type == event_type
                and existing.occurred_at == occurred_at
                and existing.correlation_id == correlation_id
                and existing.causation_id == causation_id
                and dict(existing.payload) == dict(payload)
            ):
                return existing
            raise DuplicateEvent(f"conflicting reuse of ledger event id: {event_id}")
        sequence = len(self._events)
        previous_hash = self._events[-1].event_hash if self._events else GENESIS_HASH
        immutable_payload = MappingProxyType(dict(payload))
        event_hash = _event_hash(
            sequence=sequence,
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=immutable_payload,
            previous_hash=previous_hash,
        )
        event = LedgerEvent(
            sequence=sequence,
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=immutable_payload,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self._events.append(event)
        self._event_ids.add(event_id)
        return event

    def verify(self) -> bool:
        return verify_chain(self._events)


def verify_chain(events: Sequence[LedgerEvent]) -> bool:
    """Verify sequence, linkage, and content hashes for an event chain."""
    previous_hash = GENESIS_HASH
    event_ids: set[str] = set()
    for sequence, event in enumerate(events):
        try:
            expected_hash = _event_hash(
                sequence=sequence,
                event_id=event.event_id,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                payload=event.payload,
                previous_hash=previous_hash,
            )
        except (TypeError, ValueError):
            return False
        if (
            event.event_id in event_ids
            or event.sequence != sequence
            or event.previous_hash != previous_hash
            or event.event_hash != expected_hash
        ):
            return False
        event_ids.add(event.event_id)
        previous_hash = event.event_hash
    return True
