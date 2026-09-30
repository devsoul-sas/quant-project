import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from devsoul_quant.adapters.persistence.ledger_repository import PostgresLedger
from devsoul_quant.domain.ledger import DuplicateEvent

OWNER_URL = os.getenv("TEST_DATABASE_OWNER_URL")
APP_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.integration


@pytest.fixture()
def ledgers() -> tuple[PostgresLedger, PostgresLedger]:
    if not OWNER_URL or not APP_URL:
        pytest.skip("PostgreSQL integration URLs are not configured")
    owner_engine = create_engine(OWNER_URL)
    app_engine = create_engine(APP_URL)
    with owner_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE quant_test.ledger_events"))
    return (
        PostgresLedger(app_engine, schema="quant_test", ledger_id="test-run"),
        PostgresLedger(app_engine, schema="quant_test", ledger_id="test-run"),
    )


def _event_payload(seed: int = 42) -> dict[str, int]:
    return {"seed": seed}


def test_postgres_ledger_persists_reads_and_handles_idempotency(
    ledgers: tuple[PostgresLedger, PostgresLedger],
) -> None:
    first_repository, second_repository = ledgers
    arguments = {
        "event_id": "event-1",
        "event_type": "DEMO_STARTED",
        "occurred_at": 1_700_000_000,
        "correlation_id": "demo-42",
        "causation_id": None,
        "payload": _event_payload(),
    }

    inserted = first_repository.append(**arguments)
    retried = second_repository.append(**arguments)

    assert retried == inserted
    assert second_repository.events == (inserted,)
    assert second_repository.verify()

    with pytest.raises(DuplicateEvent, match="conflicting"):
        second_repository.append(**{**arguments, "payload": _event_payload(43)})


def test_postgres_ledger_app_role_cannot_update_or_delete_closed_events(
    ledgers: tuple[PostgresLedger, PostgresLedger],
) -> None:
    repository, _ = ledgers
    repository.append(
        event_id="event-1",
        event_type="DEMO_STARTED",
        occurred_at=1_700_000_000,
        correlation_id="demo-42",
        causation_id=None,
        payload=_event_payload(),
    )

    with pytest.raises(DBAPIError), repository.engine.begin() as connection:
        connection.execute(text("UPDATE quant_test.ledger_events SET event_type = 'FORGED'"))
    with pytest.raises(DBAPIError), repository.engine.begin() as connection:
        connection.execute(text("DELETE FROM quant_test.ledger_events"))

    adjustment = repository.append(
        event_id="event-2",
        event_type="ADJUSTMENT",
        occurred_at=1_700_000_001,
        correlation_id="demo-42",
        causation_id="event-1",
        payload={"original_event_id": "event-1", "reason": "correct metadata"},
    )
    assert adjustment.sequence == 1
    assert repository.verify()


def test_postgres_ledger_trigger_rejects_mutation_even_for_a_privileged_role() -> None:
    if not OWNER_URL or not APP_URL:
        pytest.skip("PostgreSQL integration URLs are not configured")
    owner_engine = create_engine(OWNER_URL)
    app_engine = create_engine(APP_URL)
    with owner_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE quant_test.ledger_events"))
    repository = PostgresLedger(app_engine, schema="quant_test", ledger_id="test-run")
    repository.append(
        event_id="event-1",
        event_type="DEMO_STARTED",
        occurred_at=1_700_000_000,
        correlation_id="demo-42",
        causation_id=None,
        payload=_event_payload(),
    )

    # The owner role has UPDATE/DELETE privileges, so the append-only trigger is the
    # only thing standing between a privileged actor and a silent mutation.
    with pytest.raises(DBAPIError, match="append-only"), owner_engine.begin() as connection:
        connection.execute(text("UPDATE quant_test.ledger_events SET event_type = 'FORGED'"))
    with pytest.raises(DBAPIError, match="append-only"), owner_engine.begin() as connection:
        connection.execute(text("DELETE FROM quant_test.ledger_events"))

    assert repository.events[0].event_type == "DEMO_STARTED"
    assert repository.verify()


def test_postgres_ledger_concurrent_identical_retries_do_not_duplicate(
    ledgers: tuple[PostgresLedger, PostgresLedger],
) -> None:
    first_repository, second_repository = ledgers
    arguments = {
        "event_id": "event-1",
        "event_type": "DEMO_STARTED",
        "occurred_at": 1_700_000_000,
        "correlation_id": "demo-42",
        "causation_id": None,
        "payload": _event_payload(),
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        events = tuple(
            executor.map(
                lambda repo: repo.append(**arguments), (first_repository, second_repository)
            )
        )

    assert events[0] == events[1]
    assert len(first_repository.events) == 1
    assert first_repository.verify()


def test_postgres_ledger_isolates_independent_run_chains() -> None:
    if not OWNER_URL or not APP_URL:
        pytest.skip("PostgreSQL integration URLs are not configured")
    owner_engine = create_engine(OWNER_URL)
    app_engine = create_engine(APP_URL)
    with owner_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE quant_test.ledger_events"))
    first = PostgresLedger(app_engine, schema="quant_test", ledger_id="run-a")
    second = PostgresLedger(app_engine, schema="quant_test", ledger_id="run-b")

    first_event = first.append(
        event_id="event-1",
        event_type="DEMO_STARTED",
        occurred_at=1_700_000_000,
        correlation_id="demo-42",
        causation_id=None,
        payload=_event_payload(),
    )
    second_event = second.append(
        event_id="event-1",
        event_type="DEMO_STARTED",
        occurred_at=1_700_000_000,
        correlation_id="demo-42",
        causation_id=None,
        payload=_event_payload(),
    )

    assert first_event.sequence == second_event.sequence == 0
    assert first.events == (first_event,)
    assert second.events == (second_event,)
