"""Create the append-only own-event ledger.

Revision ID: 0001_append_only_ledger
Revises:
Create Date: 2026-09-30
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0001_append_only_ledger"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


def _identifier(name: str, field: str) -> str:
    if _IDENTIFIER.fullmatch(name) is None:
        raise ValueError(f"{field} must be a safe lowercase PostgreSQL identifier")
    return name


def _arguments() -> tuple[str, str | None]:
    arguments = context.get_x_argument(as_dictionary=True)
    schema = _identifier(arguments.get("schema", "public"), "schema")
    app_role = arguments.get("app_role")
    if app_role is not None:
        app_role = _identifier(app_role, "app_role")
    return schema, app_role


def upgrade() -> None:
    schema, app_role = _arguments()
    op.create_table(
        "ledger_events",
        sa.Column("ledger_id", sa.String(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.BigInteger(), nullable=False),
        sa.Column("correlation_id", sa.String(), nullable=False),
        sa.Column("causation_id", sa.String(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.CheckConstraint("sequence >= 0", name="ck_ledger_events_sequence_nonnegative"),
        sa.CheckConstraint("length(previous_hash) = 64", name="ck_ledger_events_previous_hash"),
        sa.CheckConstraint("length(event_hash) = 64", name="ck_ledger_events_event_hash"),
        sa.PrimaryKeyConstraint("ledger_id", "sequence"),
        sa.UniqueConstraint("ledger_id", "event_hash"),
        sa.UniqueConstraint("ledger_id", "event_id"),
        schema=schema,
    )
    op.execute(
        sa.text(
            f"""
            CREATE FUNCTION {schema}.reject_ledger_mutation()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'ledger_events is append-only';
            END;
            $$
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE TRIGGER ledger_events_append_only
            BEFORE UPDATE OR DELETE ON {schema}.ledger_events
            FOR EACH ROW EXECUTE FUNCTION {schema}.reject_ledger_mutation()
            """
        )
    )
    if app_role is not None:
        op.execute(sa.text(f"GRANT USAGE ON SCHEMA {schema} TO {app_role}"))
        op.execute(sa.text(f"GRANT SELECT, INSERT ON {schema}.ledger_events TO {app_role}"))


def downgrade() -> None:
    schema, _ = _arguments()
    op.drop_table("ledger_events", schema=schema)
    op.execute(sa.text(f"DROP FUNCTION {schema}.reject_ledger_mutation()"))
