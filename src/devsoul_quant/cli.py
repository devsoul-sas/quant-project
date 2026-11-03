"""Command-line interface for safe, local DevSoul Quant workflows."""

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from devsoul_quant.application.demo import run_synthetic_demo
from devsoul_quant.application.ports.ledger import LedgerPort
from devsoul_quant.application.reporting import (
    InvalidResearchSpec,
    git_head_sha,
    git_is_dirty,
    parse_research_spec,
    run_research,
    write_evidence_package,
)


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

    live = commands.add_parser(
        "live-demo",
        help="collect ephemeral demo ticks and run one paper decision",
    )
    live.add_argument(
        "--url", default=None, help="Deriv demo OTP WebSocket URL (never the real endpoint)"
    )
    live.add_argument(
        "--otp",
        action="store_true",
        help="resolve the demo URL via OTP using DEVSOUL_QUANT_DERIV_TOKEN/APP_ID/ACCOUNT",
    )
    live.add_argument("--symbol", required=True, help="market symbol to subscribe")
    live.add_argument("--duration", type=int, default=3, help="contract tick duration")
    live.add_argument(
        "--count", type=int, default=None, help="ticks to collect (default: duration + 2)"
    )
    live.add_argument(
        "--ledger-backend",
        choices=("memory", "postgres"),
        default="memory",
        help="append-only ledger backend (default: memory)",
    )
    live.add_argument("--ledger-id", default=None, help="postgres ledger identifier")

    live_evaluate = commands.add_parser(
        "live-evaluate",
        help="evaluate an aggregate ephemeral demo tick sample without economic claims",
    )
    live_evaluate.add_argument(
        "--url", default=None, help="Deriv demo OTP WebSocket URL (never the real endpoint)"
    )
    live_evaluate.add_argument(
        "--otp",
        action="store_true",
        help="resolve the demo URL via OTP using DEVSOUL_QUANT_DERIV_TOKEN/APP_ID/ACCOUNT",
    )
    live_evaluate.add_argument("--symbol", required=True, help="market symbol to subscribe")
    live_evaluate.add_argument("--duration", type=int, default=3, help="contract tick duration")
    live_evaluate.add_argument(
        "--count", type=int, default=100, help="ephemeral ticks to collect (default: 100)"
    )
    live_evaluate.add_argument(
        "--folds", type=int, default=4, help="ordered temporal folds (default: 4)"
    )
    live_evaluate.add_argument(
        "--seed", type=int, default=42, help="deterministic bootstrap seed (default: 42)"
    )

    research = commands.add_parser(
        "research", help="run reproducible provider-independent research"
    )
    research_commands = research.add_subparsers(dest="research_command", required=True)
    synthetic = research_commands.add_parser(
        "synthetic", help="run the deterministic synthetic research pipeline"
    )
    synthetic.add_argument("--spec", type=Path, required=True, help="research spec JSON path")
    synthetic.add_argument(
        "--output", type=Path, required=True, help="output directory for the evidence package"
    )
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
    if arguments.command == "research":
        return _run_research(arguments, destination)
    if arguments.command == "live-demo":
        return _run_live_demo(arguments, destination)
    if arguments.command == "live-evaluate":
        return _run_live_evaluation(arguments, destination)
    raise AssertionError("argparse accepted an unsupported command")  # pragma: no cover


def _run_live_demo(arguments: argparse.Namespace, destination: TextIO) -> int:
    destination.write("error: Deriv-derived output is disabled pending written authorization\n")
    return 2


def _run_live_evaluation(arguments: argparse.Namespace, destination: TextIO) -> int:
    destination.write("error: Deriv-derived output is disabled pending written authorization\n")
    return 2


def _run_research(arguments: argparse.Namespace, destination: TextIO) -> int:
    if arguments.research_command != "synthetic":
        raise AssertionError(  # pragma: no cover
            "argparse accepted an unsupported research command"
        )
    try:
        spec_data = json.loads(arguments.spec.read_text(encoding="utf-8"))
        spec = parse_research_spec(spec_data)
    except (InvalidResearchSpec, KeyError, ValueError, OSError) as error:
        destination.write(f"error: {error}\n")
        return 2
    try:
        sha = git_head_sha()
        dirty = git_is_dirty()
    except (OSError, subprocess.CalledProcessError) as error:
        destination.write(f"error: could not read git state: {error}\n")
        return 2
    if dirty:
        destination.write("error: working tree is dirty; commit before producing evidence\n")
        return 2
    report = run_research(spec=spec, git_sha=sha)
    try:
        write_evidence_package(report, arguments.output)
    except (FileExistsError, OSError) as error:
        destination.write(f"error: {error}\n")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the console entry point
    raise SystemExit(main())
