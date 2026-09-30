import os

import pytest
from sqlalchemy import create_engine, text

from devsoul_quant.adapters.persistence.ledger_repository import PostgresLedger
from devsoul_quant.application.demo import run_synthetic_demo

OWNER_URL = os.getenv("TEST_DATABASE_OWNER_URL")
APP_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.integration


def test_synthetic_demo_is_identical_with_memory_and_postgres_ledgers() -> None:
    if not OWNER_URL or not APP_URL:
        pytest.skip("PostgreSQL integration URLs are not configured")
    owner_engine = create_engine(OWNER_URL)
    app_engine = create_engine(APP_URL)
    with owner_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE quant_test.ledger_events"))
    postgres_ledger = PostgresLedger(
        app_engine,
        schema="quant_test",
        ledger_id="demo-integration-42",
    )

    memory_report = run_synthetic_demo(seed=42)
    postgres_report = run_synthetic_demo(seed=42, ledger=postgres_ledger)

    assert postgres_report == memory_report
    assert postgres_ledger.verify()
    assert tuple(event.canonical_json() for event in postgres_ledger.events) == tuple(
        memory_report.ledger_events
    )
