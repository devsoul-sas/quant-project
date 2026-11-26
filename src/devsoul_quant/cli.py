"""Command-line interface for safe, local DevSoul Quant workflows."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import TextIO

from devsoul_quant.application.autonomous_demo import (
    AutonomousDemoConfig,
    AutonomousDemoSnapshot,
    DemoStrategy,
    run_autonomous_demo,
)
from devsoul_quant.application.demo import run_synthetic_demo
from devsoul_quant.application.demo_execution import DemoExecutionLimits
from devsoul_quant.application.demo_session import run_demo_session
from devsoul_quant.application.ports.ledger import LedgerPort
from devsoul_quant.application.reporting import (
    InvalidResearchSpec,
    git_head_sha,
    git_is_dirty,
    parse_research_spec,
    run_research,
    write_evidence_package,
)
from devsoul_quant.application.research_runner import (
    even_odd_release,
    multiplier_release,
    run_even_odd_session,
    run_multiplier_session,
)
from devsoul_quant.domain.digit_strategy import DigitDecisionPolicy
from devsoul_quant.domain.execution_mode import parse_execution_mode
from devsoul_quant.domain.multiplier import MultiplierPolicy


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

    demo_execute = commands.add_parser(
        "demo-execute", help="execute at most one explicitly armed Deriv demo contract"
    )
    demo_execute.add_argument("--symbol", required=True)
    demo_execute.add_argument("--duration", type=int, default=3)
    demo_execute.add_argument("--count", type=int, default=5)
    demo_execute.add_argument("--stake", type=Decimal, default=Decimal("1.00"))
    demo_execute.add_argument("--minimum-net-payout-ratio", type=Decimal, default=Decimal("0.75"))
    demo_execute.add_argument("--maximum-session-loss", type=Decimal, default=Decimal("1.00"))
    demo_execute.add_argument("--confirm-demo-only", action="store_true")

    autonomous = commands.add_parser(
        "autonomous-demo", help="run the bounded local autonomous demo runner"
    )
    autonomous.add_argument(
        "--mode",
        choices=("OBSERVE_ONLY", "SHADOW_TRADING", "DEMO_INTEGRATION", "DEMO_EXPLORATORY"),
        required=True,
    )
    autonomous.add_argument("--symbol", required=True)
    autonomous.add_argument(
        "--strategy",
        choices=("EVEN_ODD", "MOMENTUM", "CONTROLLED_RANDOM", "ADAPTIVE_ENSEMBLE"),
        required=True,
    )
    autonomous.add_argument("--session-seconds", type=int, default=3600)
    autonomous.add_argument("--ticks-per-cycle", type=int, default=30)
    autonomous.add_argument("--contract-duration", type=int, default=1)
    autonomous.add_argument("--maximum-cycles", type=int, default=120)
    autonomous.add_argument("--stake", type=Decimal, default=Decimal("1.00"))
    autonomous.add_argument("--experimental-budget", type=Decimal, default=Decimal("2.00"))
    autonomous.add_argument("--maximum-contracts", type=int, default=2)
    autonomous.add_argument("--maximum-session-loss", type=Decimal, default=Decimal("2.00"))
    autonomous.add_argument("--minimum-net-payout-ratio", type=Decimal, default=Decimal("0.01"))
    autonomous.add_argument("--seed", type=int, default=42)
    autonomous.add_argument("--arm-demo", action="store_true")

    paper_session = commands.add_parser(
        "paper-session", help="run one ephemeral paper-only Deriv demo session"
    )
    paper_session.add_argument("--strategy", choices=("even-odd", "multiplier"), required=True)
    paper_session.add_argument("--symbol", default=None, help="market symbol (even-odd only)")
    paper_session.add_argument(
        "--fallback-symbol", default="R_10", help="multiplier fallback symbol"
    )
    paper_session.add_argument("--tick-count", type=int, default=120)
    paper_session.add_argument("--warmup-ticks", type=int, default=100)
    paper_session.add_argument(
        "--multiplier",
        type=Decimal,
        default=Decimal("400"),
        help="maximum multiplier ceiling; the session uses the minimum available at runtime",
    )
    paper_session.add_argument("--confirm-paper-only", action="store_true")

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
    if arguments.command == "demo-execute":
        return _run_demo_execute(arguments, destination)
    if arguments.command == "autonomous-demo":
        return _run_autonomous_demo(arguments, destination)
    if arguments.command == "paper-session":
        return _run_paper_session(arguments, destination)
    raise AssertionError("argparse accepted an unsupported command")  # pragma: no cover


def _run_live_demo(arguments: argparse.Namespace, destination: TextIO) -> int:
    destination.write(
        "error: Deriv-derived output is disabled outside the <24h ephemeral session\n"
    )
    return 2


def _run_live_evaluation(arguments: argparse.Namespace, destination: TextIO) -> int:
    destination.write(
        "error: Deriv-derived output is disabled outside the <24h ephemeral session\n"
    )
    return 2


def _run_demo_execute(arguments: argparse.Namespace, destination: TextIO) -> int:
    if not arguments.confirm_demo_only:
        destination.write("error: pass --confirm-demo-only to arm one demo contract\n")
        return 2
    token = os.getenv("DEVSOUL_QUANT_DERIV_TOKEN", "")
    app_id = os.getenv("DEVSOUL_QUANT_DERIV_APP_ID", "")
    account_id = os.getenv("DEVSOUL_QUANT_DERIV_ACCOUNT") or None
    if not token or not app_id:
        destination.write("error: demo credentials are not configured\n")
        return 2

    from devsoul_quant.adapters.deriv.client import collect_ticks
    from devsoul_quant.adapters.deriv.demo_execution import DerivDemoExecutionGateway
    from devsoul_quant.adapters.deriv.otp import UrllibSession, resolve_demo_url

    limits = DemoExecutionLimits(
        fixed_stake=arguments.stake,
        minimum_net_payout_ratio=arguments.minimum_net_payout_ratio,
        maximum_contracts=1,
        maximum_session_loss=arguments.maximum_session_loss,
        kill_switch_enabled=False,
    )

    def resolve_url() -> str:
        return resolve_demo_url(UrllibSession(), token=token, app_id=app_id, account_id=account_id)

    def collect(url: str, symbol: str, count: int) -> object:
        return asyncio.run(collect_ticks(url, symbol, count=count))

    try:
        receipt = run_demo_session(
            symbol=arguments.symbol,
            tick_count=arguments.count,
            duration=arguments.duration,
            limits=limits,
            resolve_url=resolve_url,
            collect_ticks=collect,  # type: ignore[arg-type]
            gateway_factory=lambda url: DerivDemoExecutionGateway(url),
        )
    except Exception:
        destination.write("error: demo session failed safely; inspect provider account state\n")
        return 2
    destination.write(f"{receipt.public_message}\n")
    return 0


def _autonomous_snapshot_payload(snapshot: AutonomousDemoSnapshot) -> dict[str, object]:
    economics = snapshot.economics
    adaptive = snapshot.adaptive
    return {
        "connection_state": snapshot.connection_state,
        "instrument": snapshot.instrument,
        "strategy": snapshot.strategy,
        "ticks_processed": snapshot.ticks_processed,
        "signal": snapshot.signal,
        "virtual_balance": str(snapshot.virtual_balance),
        "open_contracts": snapshot.open_contracts,
        "settled_contracts": snapshot.settled_contracts,
        "quotes_consulted": snapshot.quotes_consulted,
        "profit_loss": str(snapshot.profit_loss),
        "win_rate": None if snapshot.win_rate is None else str(snapshot.win_rate),
        "break_even": None if snapshot.break_even is None else str(snapshot.break_even),
        "drawdown": str(snapshot.drawdown),
        "risk_state": snapshot.risk_state,
        "elapsed_seconds": str(snapshot.elapsed_seconds),
        "abstention_reasons": list(snapshot.abstention_reasons),
        "experimental_budget": str(snapshot.experimental_budget),
        "budget_used": str(snapshot.budget_used),
        "budget_remaining": str(snapshot.budget_remaining),
        "adaptive": (
            None
            if adaptive is None
            else {
                "resolved_labels": adaptive.resolved_labels,
                "evaluation_labels": adaptive.evaluation_labels,
                "pending_labels": adaptive.pending_labels,
                "decision": adaptive.decision,
                "candidate_models": list(adaptive.candidate_models),
                "decision_reasons": list(adaptive.decision_reasons),
                "parity_resolved_labels": adaptive.parity_resolved_labels,
                "parity_constant_brier": (
                    None
                    if adaptive.parity_constant_brier is None
                    else str(adaptive.parity_constant_brier)
                ),
                "parity_frequency_brier": (
                    None
                    if adaptive.parity_frequency_brier is None
                    else str(adaptive.parity_frequency_brier)
                ),
                "models": [
                    {
                        "model": item.model,
                        "observations": item.observations,
                        "brier_score": (
                            None if item.brier_score is None else str(item.brier_score)
                        ),
                        "log_loss": None if item.log_loss is None else str(item.log_loss),
                        "accuracy": None if item.accuracy is None else str(item.accuracy),
                        "expected_calibration_error": (
                            None
                            if item.expected_calibration_error is None
                            else str(item.expected_calibration_error)
                        ),
                        "quoted_opportunities": item.quoted_opportunities,
                        "signals": item.signals,
                        "signal_coverage": (
                            None if item.signal_coverage is None else str(item.signal_coverage)
                        ),
                        "mean_break_even": (
                            None if item.mean_break_even is None else str(item.mean_break_even)
                        ),
                        "mean_estimated_value": (
                            None
                            if item.mean_estimated_value is None
                            else str(item.mean_estimated_value)
                        ),
                        "brier_improvement_vs_causal": (
                            None
                            if item.brier_improvement_vs_causal is None
                            else str(item.brier_improvement_vs_causal)
                        ),
                        "first_half_brier_improvement": (
                            None
                            if item.first_half_brier_improvement is None
                            else str(item.first_half_brier_improvement)
                        ),
                        "second_half_brier_improvement": (
                            None
                            if item.second_half_brier_improvement is None
                            else str(item.second_half_brier_improvement)
                        ),
                        "bootstrap_lower_bound": (
                            None
                            if item.bootstrap_lower_bound is None
                            else str(item.bootstrap_lower_bound)
                        ),
                    }
                    for item in adaptive.models
                ],
            }
        ),
        "economics": {
            "decisions": economics.decisions,
            "abstentions": economics.abstentions,
            "abstention_frequency": (
                None
                if economics.abstention_frequency is None
                else str(economics.abstention_frequency)
            ),
            "wins": economics.wins,
            "losses": economics.losses,
            "stakes": str(economics.stakes),
            "effective_net_payout": (
                None
                if economics.effective_net_payout is None
                else str(economics.effective_net_payout)
            ),
            "break_even": None if economics.break_even is None else str(economics.break_even),
            "estimated_probability": (
                None
                if economics.estimated_probability is None
                else str(economics.estimated_probability)
            ),
            "estimated_value": (
                None if economics.estimated_value is None else str(economics.estimated_value)
            ),
            "gross_profit": str(economics.gross_profit),
            "gross_loss": str(economics.gross_loss),
            "net_profit": str(economics.net_profit),
            "profit_factor": (
                None if economics.profit_factor is None else str(economics.profit_factor)
            ),
            "roi_on_stakes": (
                None if economics.roi_on_stakes is None else str(economics.roi_on_stakes)
            ),
            "by_contract_type": [
                {
                    "contract_type": item.contract_type,
                    "operations": item.operations,
                    "wins": item.wins,
                    "losses": item.losses,
                    "stakes": str(item.stakes),
                    "effective_net_payout": str(item.effective_net_payout),
                    "break_even": str(item.break_even),
                    "estimated_probability": (
                        None
                        if item.estimated_probability is None
                        else str(item.estimated_probability)
                    ),
                    "estimated_value": (
                        None if item.estimated_value is None else str(item.estimated_value)
                    ),
                    "gross_profit": str(item.gross_profit),
                    "gross_loss": str(item.gross_loss),
                    "net_profit": str(item.net_profit),
                    "profit_factor": (
                        None if item.profit_factor is None else str(item.profit_factor)
                    ),
                    "roi_on_stakes": str(item.roi_on_stakes),
                }
                for item in economics.by_contract_type
            ],
        },
    }


def _run_autonomous_demo(arguments: argparse.Namespace, destination: TextIO) -> int:
    token = os.getenv("DEVSOUL_QUANT_DERIV_TOKEN", "")
    app_id = os.getenv("DEVSOUL_QUANT_DERIV_APP_ID", "")
    account_id = os.getenv("DEVSOUL_QUANT_DERIV_ACCOUNT") or None
    if not token or not app_id:
        destination.write("error: demo credentials are not configured\n")
        return 2
    if (
        arguments.stake <= 0
        or arguments.stake > Decimal("1")
        or arguments.experimental_budget <= 0
        or arguments.experimental_budget > Decimal("100")
        or arguments.maximum_contracts < 1
        or arguments.maximum_contracts > 100
        or arguments.maximum_session_loss <= 0
        or arguments.maximum_session_loss > Decimal("10")
    ):
        destination.write("error: autonomous demo limits exceed the frozen demo bounds\n")
        return 2

    from devsoul_quant.adapters.deriv.client import collect_ticks
    from devsoul_quant.adapters.deriv.demo_execution import DerivDemoExecutionGateway
    from devsoul_quant.adapters.deriv.otp import UrllibSession, resolve_demo_url
    from devsoul_quant.application.session_deadline import SessionDeadline

    session_deadline: SessionDeadline | None = None

    def resolve_url() -> str:
        return resolve_demo_url(UrllibSession(), token=token, app_id=app_id, account_id=account_id)

    def collect(symbol: str, count: int) -> object:
        return asyncio.run(
            collect_ticks(
                resolve_url(),
                symbol,
                count=count,
                heartbeat_seconds=10,
                deadline_remaining=session_deadline.remaining() if session_deadline else None,
            )
        )

    latest_snapshot: AutonomousDemoSnapshot | None = None

    def emit(snapshot: AutonomousDemoSnapshot) -> None:
        nonlocal latest_snapshot
        latest_snapshot = snapshot
        destination.write(
            json.dumps(
                {"type": "status", **_autonomous_snapshot_payload(snapshot)},
                sort_keys=True,
            )
            + "\n"
        )

    try:
        config = AutonomousDemoConfig(
            mode=parse_execution_mode(arguments.mode),
            symbol=arguments.symbol,
            strategy=DemoStrategy(arguments.strategy),
            session_seconds=arguments.session_seconds,
            ticks_per_cycle=arguments.ticks_per_cycle,
            contract_duration=arguments.contract_duration,
            maximum_cycles=arguments.maximum_cycles,
            experimental_budget=arguments.experimental_budget,
            seed=arguments.seed,
            armed=arguments.arm_demo,
        )
        limits = DemoExecutionLimits(
            fixed_stake=arguments.stake,
            minimum_net_payout_ratio=arguments.minimum_net_payout_ratio,
            maximum_contracts=arguments.maximum_contracts,
            maximum_session_loss=arguments.maximum_session_loss,
            kill_switch_enabled=False,
        )
        session_deadline = SessionDeadline(
            session_seconds=arguments.session_seconds, monotonic=time.monotonic
        )
        result = run_autonomous_demo(
            config=config,
            limits=limits,
            collect_ticks=collect,  # type: ignore[arg-type]
            resolve_url=resolve_url,
            gateway_factory=lambda url: DerivDemoExecutionGateway(url),
            emit=emit,
        )
    except Exception:
        if latest_snapshot is not None:
            destination.write(
                json.dumps(
                    {
                        "type": "error",
                        "reason": "SAFE_AUTONOMOUS_DEMO_STOP",
                        **_autonomous_snapshot_payload(latest_snapshot),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        else:
            destination.write("error: autonomous demo stopped safely; inspect demo account state\n")
        return 2
    destination.write(
        json.dumps(
            {
                "type": "final",
                "classification": result.classification,
                **_autonomous_snapshot_payload(result.final),
            },
            sort_keys=True,
        )
        + "\n"
    )
    return 0


def _run_paper_session(arguments: argparse.Namespace, destination: TextIO) -> int:
    if not arguments.confirm_paper_only:
        destination.write("error: pass --confirm-paper-only to run one ephemeral paper session\n")
        return 2
    token = os.getenv("DEVSOUL_QUANT_DERIV_TOKEN", "")
    app_id = os.getenv("DEVSOUL_QUANT_DERIV_APP_ID", "")
    account_id = os.getenv("DEVSOUL_QUANT_DERIV_ACCOUNT") or None
    if not token or not app_id:
        destination.write("error: demo credentials are not configured\n")
        return 2
    if arguments.strategy == "even-odd" and not arguments.symbol:
        destination.write("error: --symbol is required for the even-odd strategy\n")
        return 2

    from devsoul_quant.adapters.deriv.client import collect_ticks_resilient
    from devsoul_quant.adapters.deriv.demo_execution import DerivDemoExecutionGateway
    from devsoul_quant.adapters.deriv.otp import UrllibSession, resolve_demo_url

    def resolve_url() -> str:
        return resolve_demo_url(UrllibSession(), token=token, app_id=app_id, account_id=account_id)

    def collect(url: str, symbol: str, count: int) -> object:
        return asyncio.run(collect_ticks_resilient(resolve_url, symbol, count=count))

    def clock() -> int:
        return int(time.time())

    try:
        if arguments.strategy == "even-odd":
            even_odd_policy = DigitDecisionPolicy(
                min_samples=arguments.warmup_ticks,
                z_score=Decimal("2.576"),
                min_edge_probability=Decimal("0.01"),
            )
            release = even_odd_release(even_odd_policy, code_version="0.1.0", ttl_seconds=82_800)
            result = run_even_odd_session(
                release=release,
                symbol=arguments.symbol,
                warmup_ticks=arguments.warmup_ticks,
                tick_count=arguments.tick_count,
                policy=even_odd_policy,
                amount_requested=Decimal("1.00"),
                resolve_url=resolve_url,
                collect_ticks=collect,  # type: ignore[arg-type]
                gateway_factory=lambda url: DerivDemoExecutionGateway(url),
                clock=clock,
            )
        else:
            multiplier_policy = MultiplierPolicy(
                lookback_ticks=5,
                minimum_absolute_return=Decimal("0.01"),
                minimum_directional_consistency=Decimal("0.75"),
                multiplier=arguments.multiplier,
                stake=Decimal("1"),
                stop_loss=Decimal("0.50"),
                take_profit=Decimal("1.00"),
                maximum_holding_ticks=5,
            )
            release = multiplier_release(
                multiplier_policy, code_version="0.1.0", ttl_seconds=82_800
            )
            result = run_multiplier_session(
                release=release,
                fallback_symbol=arguments.fallback_symbol,
                tick_count=arguments.tick_count,
                policy=multiplier_policy,
                resolve_url=resolve_url,
                collect_ticks=collect,  # type: ignore[arg-type]
                gateway_factory=lambda url: DerivDemoExecutionGateway(url),
                clock=clock,
            )
    except Exception:
        destination.write("error: paper session failed safely; no provider state retained\n")
        return 2

    destination.write(
        json.dumps(
            {
                "strategy": result.family.value,
                "conclusion": result.conclusion.value,
                "release_id": result.release_id,
                "forward_iterations": result.forward_iterations,
                "entries": result.entries,
                "no_trade": result.no_trade,
            },
            sort_keys=True,
        )
        + "\n"
    )
    return 0


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
