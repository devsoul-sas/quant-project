"""Command-line interface for safe, local DevSoul Quant workflows."""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from typing import TextIO

from devsoul_quant.application.demo import run_synthetic_demo
from devsoul_quant.application.ports.ledger import LedgerPort


class CliError(RuntimeError):
    """Raised when a CLI invocation cannot proceed safely."""


def _resolve_ledger(arguments: argparse.Namespace) -> LedgerPort | None:
    backend = arguments.ledger_backend
    if backend == "memory":
        return None
    if backend == "postgres":
        database_url = os.getenv("DEVSOUL_QUANT_DATABASE_URL")
        schema = os.getenv("DEVSOUL_QUANT_DATABASE_SCHEMA")
        if not database_url or not schema:
            raise CliError(
                "postgres ledger requires DEVSOUL_QUANT_DATABASE_URL and "
                "DEVSOUL_QUANT_DATABASE_SCHEMA"
            )
        if not arguments.ledger_id:
            raise CliError("postgres ledger requires --ledger-id")
        from sqlalchemy import create_engine

        from devsoul_quant.adapters.persistence.ledger_repository import PostgresLedger

        return PostgresLedger(
            create_engine(database_url),
            schema=schema,
            ledger_id=arguments.ledger_id,
        )
    raise CliError(f"unsupported ledger backend: {backend}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="devsoul-quant")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="run a deterministic synthetic paper demo")
    demo.add_argument("--seed", type=int, required=True, help="deterministic scenario seed")
    demo.add_argument(
        "--ledger-backend",
        choices=("memory", "postgres"),
        default="memory",
        help="append-only ledger backend (default: memory)",
    )
    demo.add_argument("--ledger-id", default=None, help="postgres ledger identifier")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    """Run a supported safe command and return a process exit code."""
    arguments = _parser().parse_args(argv)
    destination = stdout if stdout is not None else sys.stdout
    if arguments.command == "demo":
        try:
            ledger = _resolve_ledger(arguments)
        except (CliError, ValueError) as error:
            destination.write(f"error: {error}\n")
            return 2
        try:
            report = run_synthetic_demo(seed=arguments.seed, ledger=ledger)
        except ValueError as error:
            destination.write(f"error: {error}\n")
            return 2
        except Exception as error:
            if type(error).__module__.split(".")[0] == "sqlalchemy":
                destination.write("error: could not connect to the configured ledger\n")
                return 2
            raise
        json.dump(report.to_dict(), destination, ensure_ascii=True, sort_keys=True)
        destination.write("\n")
        return 0
    raise AssertionError("argparse accepted an unsupported command")


if __name__ == "__main__":  # pragma: no cover - exercised through the console entry point
    raise SystemExit(main())
