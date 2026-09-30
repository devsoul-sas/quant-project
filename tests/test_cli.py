import argparse
import json
import os
from io import StringIO

import pytest

from devsoul_quant.adapters.persistence.ledger_repository import PostgresLedger
from devsoul_quant.application.demo import run_synthetic_demo
from devsoul_quant.cli import CliError, _parser, _resolve_ledger, main


def test_demo_cli_emits_the_public_report_as_json() -> None:
    output = StringIO()

    exit_code = main(["demo", "--seed", "42"], stdout=output)

    payload = json.loads(output.getvalue())
    assert exit_code == 0
    assert payload == run_synthetic_demo(seed=42).to_dict()
    assert payload["execution_mode"] == "SYNTHETIC_PAPER"
    assert payload["economy"] == "UNAVAILABLE"
    assert payload["profitability_claim"] is False


def test_demo_cli_accepts_an_explicit_memory_backend() -> None:
    implicit = StringIO()
    explicit = StringIO()

    main(["demo", "--seed", "42"], stdout=implicit)
    main(["demo", "--seed", "42", "--ledger-backend", "memory"], stdout=explicit)

    assert explicit.getvalue() == implicit.getvalue()


def test_demo_cli_fails_closed_when_postgres_configuration_is_missing() -> None:
    previous_url = os.environ.pop("DEVSOUL_QUANT_DATABASE_URL", None)
    previous_schema = os.environ.pop("DEVSOUL_QUANT_DATABASE_SCHEMA", None)
    output = StringIO()
    try:
        exit_code = main(
            [
                "demo",
                "--seed",
                "42",
                "--ledger-backend",
                "postgres",
                "--ledger-id",
                "test-run",
            ],
            stdout=output,
        )
    finally:
        if previous_url is not None:
            os.environ["DEVSOUL_QUANT_DATABASE_URL"] = previous_url
        if previous_schema is not None:
            os.environ["DEVSOUL_QUANT_DATABASE_SCHEMA"] = previous_schema

    assert exit_code == 2
    assert "error:" in output.getvalue()


def test_postgres_backend_resolution_builds_an_engine_without_connecting() -> None:
    previous_url = os.environ.get("DEVSOUL_QUANT_DATABASE_URL")
    previous_schema = os.environ.get("DEVSOUL_QUANT_DATABASE_SCHEMA")
    os.environ["DEVSOUL_QUANT_DATABASE_URL"] = "postgresql+psycopg://u:p@127.0.0.1:5432/db"
    os.environ["DEVSOUL_QUANT_DATABASE_SCHEMA"] = "quant"
    try:
        arguments = _parser().parse_args(
            [
                "demo",
                "--seed",
                "42",
                "--ledger-backend",
                "postgres",
                "--ledger-id",
                "run-1",
            ]
        )
        ledger = _resolve_ledger(arguments)
    finally:
        if previous_url is None:
            os.environ.pop("DEVSOUL_QUANT_DATABASE_URL", None)
        else:
            os.environ["DEVSOUL_QUANT_DATABASE_URL"] = previous_url
        if previous_schema is None:
            os.environ.pop("DEVSOUL_QUANT_DATABASE_SCHEMA", None)
        else:
            os.environ["DEVSOUL_QUANT_DATABASE_SCHEMA"] = previous_schema

    assert isinstance(ledger, PostgresLedger)


def test_postgres_backend_requires_a_ledger_id() -> None:
    previous_url = os.environ.get("DEVSOUL_QUANT_DATABASE_URL")
    previous_schema = os.environ.get("DEVSOUL_QUANT_DATABASE_SCHEMA")
    os.environ["DEVSOUL_QUANT_DATABASE_URL"] = "postgresql+psycopg://u:p@127.0.0.1:5432/db"
    os.environ["DEVSOUL_QUANT_DATABASE_SCHEMA"] = "quant"
    try:
        arguments = argparse.Namespace(ledger_backend="postgres", ledger_id=None)
        with pytest.raises(CliError, match="ledger-id"):
            _resolve_ledger(arguments)
    finally:
        if previous_url is None:
            os.environ.pop("DEVSOUL_QUANT_DATABASE_URL", None)
        else:
            os.environ["DEVSOUL_QUANT_DATABASE_URL"] = previous_url
        if previous_schema is None:
            os.environ.pop("DEVSOUL_QUANT_DATABASE_SCHEMA", None)
        else:
            os.environ["DEVSOUL_QUANT_DATABASE_SCHEMA"] = previous_schema


def test_unsupported_ledger_backend_fails_closed() -> None:
    arguments = argparse.Namespace(ledger_backend="bogus", ledger_id=None)

    with pytest.raises(CliError, match="unsupported"):
        _resolve_ledger(arguments)


def test_demo_cli_reports_invalid_schema_without_traceback() -> None:
    previous_url = os.environ.get("DEVSOUL_QUANT_DATABASE_URL")
    previous_schema = os.environ.get("DEVSOUL_QUANT_DATABASE_SCHEMA")
    os.environ["DEVSOUL_QUANT_DATABASE_URL"] = "postgresql+psycopg://u:p@127.0.0.1:5432/db"
    os.environ["DEVSOUL_QUANT_DATABASE_SCHEMA"] = "Bad Schema!"
    output = StringIO()
    try:
        exit_code = main(
            [
                "demo",
                "--seed",
                "42",
                "--ledger-backend",
                "postgres",
                "--ledger-id",
                "run-1",
            ],
            stdout=output,
        )
    finally:
        if previous_url is None:
            os.environ.pop("DEVSOUL_QUANT_DATABASE_URL", None)
        else:
            os.environ["DEVSOUL_QUANT_DATABASE_URL"] = previous_url
        if previous_schema is None:
            os.environ.pop("DEVSOUL_QUANT_DATABASE_SCHEMA", None)
        else:
            os.environ["DEVSOUL_QUANT_DATABASE_SCHEMA"] = previous_schema

    assert exit_code == 2
    assert "error:" in output.getvalue()
    assert "Traceback" not in output.getvalue()


def test_demo_cli_hides_database_connection_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.exc import OperationalError

    def fail(*args: object, **kwargs: object) -> object:
        raise OperationalError("SELECT 1", {}, RuntimeError("connection refused"))

    monkeypatch.setattr("devsoul_quant.cli.run_synthetic_demo", fail)
    previous_url = os.environ.get("DEVSOUL_QUANT_DATABASE_URL")
    previous_schema = os.environ.get("DEVSOUL_QUANT_DATABASE_SCHEMA")
    os.environ["DEVSOUL_QUANT_DATABASE_URL"] = "postgresql+psycopg://u:p@127.0.0.1:5432/db"
    os.environ["DEVSOUL_QUANT_DATABASE_SCHEMA"] = "quant"
    output = StringIO()
    try:
        exit_code = main(
            [
                "demo",
                "--seed",
                "42",
                "--ledger-backend",
                "postgres",
                "--ledger-id",
                "run-1",
            ],
            stdout=output,
        )
    finally:
        if previous_url is None:
            os.environ.pop("DEVSOUL_QUANT_DATABASE_URL", None)
        else:
            os.environ["DEVSOUL_QUANT_DATABASE_URL"] = previous_url
        if previous_schema is None:
            os.environ.pop("DEVSOUL_QUANT_DATABASE_SCHEMA", None)
        else:
            os.environ["DEVSOUL_QUANT_DATABASE_SCHEMA"] = previous_schema

    assert exit_code == 2
    assert "could not connect" in output.getvalue()
    assert "connection refused" not in output.getvalue()
    assert "Traceback" not in output.getvalue()


def test_demo_cli_reports_domain_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise ValueError("invalid scenario")

    monkeypatch.setattr("devsoul_quant.cli.run_synthetic_demo", fail)
    output = StringIO()

    exit_code = main(["demo", "--seed", "42"], stdout=output)

    assert exit_code == 2
    assert "error: invalid scenario" in output.getvalue()
    assert "Traceback" not in output.getvalue()
