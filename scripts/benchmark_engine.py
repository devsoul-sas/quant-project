"""Reproducible engine benchmark for S3.10 phases C1/C5.

Generates deterministic synthetic tick streams (no network, no Deriv data) and
measures the adaptive evaluator's compute cost at 5k/20k/40k/100k ticks,
separating the O(n) bounded-window path from the former full-history O(n^2)
feature build. Reports mean per-tick time, p95 per-tick latency, total time and
peak RSS. Run with:

    uv run python scripts/benchmark_engine.py
"""

from __future__ import annotations

import resource
import sys
import time
from decimal import Decimal

from devsoul_quant.application.adaptive_shadow import AdaptivePrequentialEvaluator
from devsoul_quant.domain.adaptive_intelligence import build_adaptive_features
from devsoul_quant.domain.replay import Tick

SIZES = (5_000, 20_000, 40_000, 100_000)
OLD_MAX = 20_000  # the former O(n^2) path is measured only up to this size


def synthetic_ticks(count: int) -> list[Tick]:
    return [
        Tick(index, Decimal("100.03") if index % 2 else Decimal("99.97"), pip_size=2)
        for index in range(1, count + 1)
    ]


def _peak_rss_kb() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def run_new_path(ticks: list[Tick]) -> dict[str, object]:
    evaluator = AdaptivePrequentialEvaluator(warmup_labels=0, seed=38)
    per_tick: list[float] = []
    started = time.perf_counter()
    for tick in ticks:
        tick_started = time.perf_counter()
        evaluator.observe(tick)
        per_tick.append(time.perf_counter() - tick_started)
    elapsed = time.perf_counter() - started
    evaluator.clear()
    return _summarize(elapsed, per_tick, len(ticks))


def run_old_path(ticks: list[Tick]) -> dict[str, object]:
    """Replicate the former full-history feature build to measure its O(n^2) cost."""
    history: list[Tick] = []
    per_tick: list[float] = []
    started = time.perf_counter()
    for tick in ticks:
        tick_started = time.perf_counter()
        history.append(tick)
        if len(history) >= 6:
            build_adaptive_features(history, decision_epoch=tick.epoch)
        per_tick.append(time.perf_counter() - tick_started)
    elapsed = time.perf_counter() - started
    return _summarize(elapsed, per_tick, len(ticks))


def _summarize(elapsed: float, per_tick: list[float], count: int) -> dict[str, object]:
    ordered = sorted(per_tick)
    p95 = ordered[int(len(ordered) * 0.95) - 1] if ordered else 0.0
    return {
        "ticks": count,
        "total_seconds": round(elapsed, 4),
        "mean_us_per_tick": round(sum(per_tick) / count * 1_000_000, 2) if count else 0.0,
        "p95_us_per_tick": round(p95 * 1_000_000, 2),
        "peak_rss_kb": _peak_rss_kb(),
    }


def main() -> int:
    print(f"{'path':<5} {'ticks':>7} {'total_s':>9} {'mean_us':>9} {'p95_us':>9} {'rss_kb':>9}")
    for size in SIZES:
        ticks = synthetic_ticks(size)
        new = run_new_path(ticks)
        print(
            f"{'new':<5} {new['ticks']:>7} {new['total_seconds']:>9} "
            f"{new['mean_us_per_tick']:>9} {new['p95_us_per_tick']:>9} {new['peak_rss_kb']:>9}"
        )
        if size <= OLD_MAX:
            old = run_old_path(ticks)
            print(
                f"{'old':<5} {old['ticks']:>7} {old['total_seconds']:>9} "
                f"{old['mean_us_per_tick']:>9} {old['p95_us_per_tick']:>9} {old['peak_rss_kb']:>9}"
            )
        else:
            print(f"{'old':<5} {size:>7} {'(skip)':>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
