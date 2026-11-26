"""S3.12/H1-V2 prospective power verification (adaptive Markov candidate).

Reproducible, deterministic, network-free. Part 1 derives the analytical
minimum sample for each preregistered contrast at 80% power. Part 2 runs a small
empirical simulation of the full H1-V2 gate (``MARKOV_1_ADAPTIVE`` candidate) on
synthetic Markov(delta=0.03) sequences and reports the observed gate-pass rate
by transition count, a null i.i.d. control for false-positive rate, and an
observation-loss sensitivity. Run with:

    uv run python scripts/power_simulation.py [--replications N]

The V2 candidate updates its 2x2 transition counters causally after each scored
prediction, so its estimation error decays with sample size instead of staying
frozen at the warm-up level (the S3.11 limitation).
"""

from __future__ import annotations

import argparse
import math
import random
from decimal import Decimal

from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.step_direction import StepDirectionPrequentialEvaluator

DELTA = 0.03
ALPHA = 0.05

# Transitions for 2h, 3h, 4h, 6h at a 1-second cadence (the power boundary region
# for the adaptive candidate). 8h/12h/22h are reported analytically (>=80% once
# the 4-6h window crosses the threshold).
SWEEP_TRANSITIONS = (7200, 10800, 14400, 21600)


def _normal_quantile(p: float) -> float:
    return math.sqrt(2.0) * _erfinv(2.0 * p - 1.0)


def _erfinv(x: float) -> float:
    a = 0.147
    ln = math.log(1.0 - x * x)
    part1 = 2.0 / (math.pi * a) + ln / 2.0
    part2 = ln / a
    return math.copysign(math.sqrt(math.sqrt(part1 * part1 - part2) - part1), x)


def analytical() -> dict[str, float]:
    z_two = _normal_quantile(1.0 - ALPHA / 2.0)
    z_hol = _normal_quantile(1.0 - ALPHA / 4.0)
    z_80 = _normal_quantile(0.80)
    return {
        "marginal": (z_two + z_80) ** 2 * 0.25 / DELTA**2,
        "marginal_holm": (z_hol + z_80) ** 2 * 0.25 / DELTA**2,
        "chi_square": (z_two + z_80) ** 2 / (2 * DELTA) ** 2,
        "chi_square_holm": (z_hol + z_80) ** 2 / (2 * DELTA) ** 2,
        "brier_gate": (z_two + z_80) ** 2 / DELTA**2,
        "brier_gate_holm": (z_hol + z_80) ** 2 / DELTA**2,
    }


def _markov_directions(count: int, delta: float, seed: int) -> list[int]:
    """Symmetric two-state Markov chain, P(UP|UP)=0.5+delta, P(UP|DOWN)=0.5-delta."""
    generator = random.Random(seed)
    current = generator.randrange(2)
    directions: list[int] = [current]
    for _ in range(count):
        p_up = 0.5 + delta if current == 1 else 0.5 - delta
        current = 1 if generator.random() < p_up else 0
        directions.append(current)
    return directions


def _iid_directions(count: int, seed: int) -> list[int]:
    generator = random.Random(seed)
    return [generator.randrange(2) for _ in range(count)]


def _ticks_from_directions(
    directions: list[int],
    *,
    cadence: int = 2,
    flat_fraction: float = 0.0,
    seed: int = 0,
) -> tuple[Tick, ...]:
    """Build ticks from a direction sequence, optionally injecting FLAT repeats."""
    generator = random.Random(seed)
    ticks = [Tick(1, Decimal("100.00"), pip_size=1)]
    quote = Decimal("100.00")
    epoch = 1
    for direction in directions[1:]:
        if flat_fraction and generator.random() < flat_fraction:
            ticks.append(Tick(epoch + cadence, quote, pip_size=1))  # FLAT (no move)
            epoch += cadence
            continue
        epoch += cadence
        quote += Decimal("0.10") if direction == 1 else -Decimal("0.10")
        ticks.append(Tick(epoch, quote, pip_size=1))
    return tuple(ticks)


def _run(directions: list[int], *, flat_fraction: float = 0.0, seed: int = 0) -> str:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=120, seed=42, cadence=2)
    for tick in _ticks_from_directions(directions, flat_fraction=flat_fraction, seed=seed):
        evaluator.observe_tick(tick)
    result = evaluator.finalize()
    evaluator.clear()
    return result.classification


def empirical(replications: int) -> tuple[list[tuple[int, float]], float, float]:
    rows: list[tuple[int, float]] = []
    for count in SWEEP_TRANSITIONS:
        passed = 0
        for replication in range(replications):
            directions = _markov_directions(count, DELTA, seed=1000 + replication)
            if _run(directions) == "H1_CANDIDATE_FOR_INDEPENDENT_VALIDATION":
                passed += 1
        rows.append((count, passed / replications))

    null_false_positives = 0
    null_replications = max(replications, 20)
    for replication in range(null_replications):
        directions = _iid_directions(14400, seed=5000 + replication)
        if _run(directions) == "H1_CANDIDATE_FOR_INDEPENDENT_VALIDATION":
            null_false_positives += 1

    loss_passed = 0
    for replication in range(replications):
        directions = _markov_directions(14400, DELTA, seed=2000 + replication)
        if (
            _run(directions, flat_fraction=0.05, seed=3000 + replication)
            == "H1_CANDIDATE_FOR_INDEPENDENT_VALIDATION"
        ):
            loss_passed += 1

    return rows, null_false_positives / null_replications, loss_passed / replications


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replications", type=int, default=10)
    arguments = parser.parse_args()

    power = analytical()
    print("Analytical minimum sample at 80% power, delta = 0.03:")
    for name, value in power.items():
        print(f"  {name:<18} n >= {value:,.0f}")

    rows, null_fpr, loss_power = empirical(arguments.replications)
    print("\nEmpirical H1-V2 gate pass rate on Markov(delta=0.03), MARKOV_1_ADAPTIVE:")
    print("  (transitions -> 1s-cadence hours, 2s-cadence hours) -> pass rate")
    for count, rate in rows:
        hours_1s = count / 3600
        hours_2s = count / 1800
        print(f"  n = {count:>6} -> {hours_1s:>5.1f}h (1s), {hours_2s:>5.1f}h (2s) -> {rate:.2f}")
    print(f"\nNull i.i.d. control (n=14400): false-positive rate {null_fpr:.3f}")
    print(f"Observation-loss sensitivity (n=14400, 5% FLAT): pass rate {loss_power:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
