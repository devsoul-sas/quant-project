"""PostgreSQL implementation of the append-only ledger port."""

import hashlib
from collections.abc import Mapping
from types import MappingProxyType

from sqlalchemy import Engine, MetaData, select, text
from sqlalchemy.engine import RowMapping

from devsoul_quant.adapters.persistence.models import ledger_events_table, validate_schema_name
from devsoul_quant.domain.ledger import (
    GENESIS_HASH,
    DuplicateEvent,
    LedgerEvent,
    LedgerScalar,
    build_ledger_event,
    verify_chain,
)


class PostgresLedger:
    """Transactional hash-chained ledger serialized by a PostgreSQL advisory lock."""

    @staticmethod
    def _advisory_lock_key(*parts: str) -> int:
        """Derive a stable, signed 64-bit lock key independent of PostgreSQL internals."""
        digest = hashlib.blake2b(
            b"\x00".join(part.encode() for part in parts),
            digest_size=8,
        ).digest()
        return int.from_bytes(digest, "big", signed=True)

    def __init__(self, engine: Engine, *, schema: str, ledger_id: str) -> None:
        if not isinstance(ledger_id, str) or not ledger_id.strip():
            raise ValueError("ledger_id must be a non-blank string")
        self.engine = engine
        self._schema = validate_schema_name(schema)
        self._ledger_id = ledger_id
        self._table = ledger_events_table(MetaData(), schema=self._schema)

    @staticmethod
    def _from_mapping(row: RowMapping) -> LedgerEvent:
        raw_payload = row["payload"]
        if not isinstance(raw_payload, dict):
            raise ValueError("stored ledger payload must be a JSON object")
        payload: dict[str, LedgerScalar] = {}
        for key, value in raw_payload.items():
            if not isinstance(key, str):
                raise ValueError("stored ledger payload keys must be strings")
            if value is not None and type(value) not in {str, int, bool}:
                raise ValueError("stored ledger payload contains an unsupported value")
            payload[key] = value
        return LedgerEvent(
            sequence=int(row["sequence"]),
            event_id=str(row["event_id"]),
            event_type=str(row["event_type"]),
            occurred_at=int(row["occurred_at"]),
            correlation_id=str(row["correlation_id"]),
            causation_id=str(row["causation_id"]) if row["causation_id"] is not None else None,
            payload=MappingProxyType(payload),
            previous_hash=str(row["previous_hash"]),
            event_hash=str(row["event_hash"]),
        )

    @property
    def events(self) -> tuple[LedgerEvent, ...]:
        statement = (
            select(self._table)
            .where(self._table.c.ledger_id == self._ledger_id)
            .order_by(self._table.c.sequence)
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings()
            return tuple(self._from_mapping(row) for row in rows)

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
        with self.engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": self._advisory_lock_key(self._schema, self._ledger_id)},
            )
            existing_row = (
                connection.execute(
                    select(self._table).where(
                        self._table.c.ledger_id == self._ledger_id,
                        self._table.c.event_id == event_id,
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing_row is not None:
                existing = self._from_mapping(existing_row)
                if (
                    existing.event_type == event_type
                    and existing.occurred_at == occurred_at
                    and existing.correlation_id == correlation_id
                    and existing.causation_id == causation_id
                    and dict(existing.payload) == dict(payload)
                ):
                    return existing
                raise DuplicateEvent(f"conflicting reuse of ledger event id: {event_id}")

            previous_row = (
                connection.execute(
                    select(self._table)
                    .where(self._table.c.ledger_id == self._ledger_id)
                    .order_by(self._table.c.sequence.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
            sequence = 0 if previous_row is None else int(previous_row["sequence"]) + 1
            previous_hash = (
                GENESIS_HASH if previous_row is None else str(previous_row["event_hash"])
            )
            event = build_ledger_event(
                sequence=sequence,
                event_id=event_id,
                event_type=event_type,
                occurred_at=occurred_at,
                correlation_id=correlation_id,
                causation_id=causation_id,
                payload=payload,
                previous_hash=previous_hash,
            )
            connection.execute(
                self._table.insert().values(
                    ledger_id=self._ledger_id,
                    sequence=event.sequence,
                    event_id=event.event_id,
                    event_type=event.event_type,
                    occurred_at=event.occurred_at,
                    correlation_id=event.correlation_id,
                    causation_id=event.causation_id,
                    payload=dict(event.payload),
                    previous_hash=event.previous_hash,
                    event_hash=event.event_hash,
                )
            )
            return event

    def verify(self) -> bool:
        try:
            return verify_chain(self.events)
        except (TypeError, ValueError):
            return False
