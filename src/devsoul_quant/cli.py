"""Command-line interface for safe, local DevSoul Quant workflows."""

import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from devsoul_quant.application.demo import run_synthetic_demo


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="devsoul-quant")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="run a deterministic synthetic paper demo")
    demo.add_argument("--seed", type=int, required=True, help="deterministic scenario seed")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    """Run a supported safe command and return a process exit code."""
    arguments = _parser().parse_args(argv)
    destination = stdout if stdout is not None else sys.stdout
    if arguments.command == "demo":
        report = run_synthetic_demo(seed=arguments.seed)
        json.dump(report.to_dict(), destination, ensure_ascii=True, sort_keys=True)
        destination.write("\n")
        return 0
    raise AssertionError("argparse accepted an unsupported command")


if __name__ == "__main__":  # pragma: no cover - exercised through the console entry point
    raise SystemExit(main())
