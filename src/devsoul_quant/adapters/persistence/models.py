"""SQLAlchemy table metadata for the append-only ledger.

This metadata mirrors the Alembic migration 0001_append_only_ledger so that
runtime queries (SELECT/INSERT) share one source of truth with the DDL.
"""

import re

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql

_SCHEMA_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


def validate_schema_name(schema: str) -> str:
    if _SCHEMA_PATTERN.fullmatch(schema) is None:
        raise ValueError("schema must be a safe lowercase PostgreSQL identifier")
    return schema


def ledger_events_table(metadata: MetaData, *, schema: str) -> Table:
    """Build the ledger table metadata for an explicitly selected schema."""
    validate_schema_name(schema)
    return Table(
        "ledger_events",
        metadata,
        Column("ledger_id", String, primary_key=True),
        Column("sequence", BigInteger, primary_key=True, autoincrement=False),
        Column("event_id", String, nullable=False),
        Column("event_type", String, nullable=False),
        Column("occurred_at", BigInteger, nullable=False),
        Column("correlation_id", String, nullable=False),
        Column("causation_id", String, nullable=True),
        Column("payload", postgresql.JSONB(), nullable=False),
        Column("previous_hash", String(64), nullable=False),
        Column("event_hash", String(64), nullable=False),
        CheckConstraint("sequence >= 0", name="ck_ledger_events_sequence_nonnegative"),
        CheckConstraint("length(previous_hash) = 64", name="ck_ledger_events_previous_hash"),
        CheckConstraint("length(event_hash) = 64", name="ck_ledger_events_event_hash"),
        UniqueConstraint("ledger_id", "event_id"),
        UniqueConstraint("ledger_id", "event_hash"),
        schema=schema,
    )
