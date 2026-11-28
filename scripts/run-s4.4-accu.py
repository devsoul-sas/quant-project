#!/usr/bin/env python3
"""Run the frozen S4.4 ACCU proxy engine without persisting provider data."""

from __future__ import annotations

import argparse
import json
import os
import time
import tracemalloc
from decimal import Decimal
from pathlib import Path

from devsoul_quant.adapters.deriv.accu_proposal import propose_accumulator
from devsoul_quant.adapters.deriv.history import fetch_ticks_history
from devsoul_quant.adapters.deriv.otp import DemoUrlResolver, UrllibSession
from devsoul_quant.application.accu_experiment_spec import load_accu_experiment_spec
from devsoul_quant.application.accu_research_engine import run_ephemeral_accu
from devsoul_quant.application.session_deadline import SessionDeadline
from devsoul_quant.domain.replay import Tick

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SPEC = _ROOT / "protocols" / "s4.4-accu-primary-v1.json"


def _synthetic_ticks(count: int) -> list[Tick]:
    quote = Decimal("100")
    ticks: list[Tick] = []
    for index in range(count):
        phase = index % 80
        step = Decimal("0.01") if phase < 40 else Decimal("-0.01")
        if index and index % 997 == 0:
            step = Decimal("0.06")
        quote += step
        ticks.append(Tick(1_800_000_000 + index * 2, quote, 2))
    return ticks


def _load(path: Path):
    return load_accu_experiment_spec(json.loads(path.read_text(encoding="utf-8")))


def _safe_envelope(summary, *, mode: str) -> dict[str, object]:
    return {
        "protocol_version": summary.protocol_version,
        "protocol_hash": summary.protocol_hash,
        "mode": mode,
        "classification": summary.classification.value,
        "fidelity": "ACCU_RECONSTRUCTION_PARTIAL",
        "provider_values_persisted": False,
        "contracts_opened": 0,
        "buy_calls": 0,
        "sell_calls": 0,
    }


def _run_synthetic(spec) -> dict[str, object]:
    summary = run_ephemeral_accu(
        spec=spec,
        acquire_ticks=lambda symbol, count: _synthetic_ticks(count),
        acquire_barriers=lambda symbol, rates: {rate: Decimal("0.0005") for rate in rates},
    )
    return _safe_envelope(summary, mode="synthetic")


def _run_live(spec) -> dict[str, object]:
    token = os.getenv("DEVSOUL_QUANT_DERIV_TOKEN", "")
    app_id = os.getenv("DEVSOUL_QUANT_DERIV_APP_ID", "")
    account_id = os.getenv("DEVSOUL_QUANT_DERIV_ACCOUNT") or None
    if not token or not app_id:
        raise RuntimeError("demo credentials are not configured")
    deadline = SessionDeadline(
        session_seconds=spec.maximum_duration_seconds,
        monotonic=time.monotonic,
    )
    resolver = DemoUrlResolver(
        UrllibSession(), token=token, app_id=app_id, account_id=account_id
    )

    def acquire_ticks(symbol: str, count: int) -> list[Tick]:
        deadline.ensure_open()
        result = fetch_ticks_history(
            resolver,
            symbol,
            total_count=count,
            cadence_seconds=spec.cadence_seconds,
            deadline_remaining=deadline.remaining(),
        )
        return list(result.ticks)

    def acquire_barriers(symbol: str, rates: tuple[Decimal, ...]):
        barriers: dict[Decimal, Decimal] = {}
        for rate in rates:
            deadline.ensure_open()
            proposal = propose_accumulator(
                resolver(),
                symbol,
                growth_rate=rate,
                stake=Decimal("1"),
                request_timeout_seconds=min(30.0, deadline.remaining()),
            )
            barriers[rate] = proposal.barrier_fraction
        return barriers

    summary = run_ephemeral_accu(
        spec=spec,
        acquire_ticks=acquire_ticks,
        acquire_barriers=acquire_barriers,
    )
    return _safe_envelope(summary, mode="live-read-only")


def _benchmark(spec) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for count in (40_000, 200_000):
        raw = json.loads(_DEFAULT_SPEC.read_text(encoding="utf-8"))
        raw["maximum_ticks"] = count
        benchmark_spec = load_accu_experiment_spec(raw)
        tracemalloc.start()
        started = time.perf_counter()
        _run_synthetic(benchmark_spec)
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rows.append(
            {
                "owned_synthetic_ticks": count,
                "elapsed_seconds": round(elapsed, 3),
                "peak_mib": round(peak / (1024 * 1024), 3),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=_DEFAULT_SPEC)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--benchmark", action="store_true")
    arguments = parser.parse_args()
    spec = _load(arguments.spec)
    if arguments.benchmark:
        print(json.dumps({"benchmark": _benchmark(spec)}, sort_keys=True))
    else:
        envelope = _run_live(spec) if arguments.live else _run_synthetic(spec)
        print(json.dumps(envelope, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
