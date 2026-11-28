"""Owned synthetic verification of the reusable S4.4 ACCU research engine."""

import json
from decimal import Decimal
from pathlib import Path

from devsoul_quant.application.accu_experiment_spec import load_accu_experiment_spec
from devsoul_quant.application.accu_research_engine import (
    AccuTerminalClassification,
    build_accu_examples,
    evaluate_accu_proxy,
    run_ephemeral_accu,
)
from devsoul_quant.domain.replay import Tick

_SPEC = Path(__file__).parents[2] / "protocols" / "s4.4-accu-primary-v1.json"


def _spec():
    raw = json.loads(_SPEC.read_text(encoding="utf-8"))
    raw["statistics"]["resamples"] = 40
    raw["statistics"]["minimum_rule_entries"] = 2
    raw["split"]["purge_ticks"] = 5
    raw["maximum_ticks"] = 500
    return load_accu_experiment_spec(raw)


def _ticks(count: int, *, shock_at: int | None = None) -> list[Tick]:
    quote = Decimal("100")
    result: list[Tick] = []
    for index in range(count):
        step = Decimal("0.01") if index % 20 < 10 else Decimal("-0.01")
        if index and index % 30 == 0:
            step = Decimal("0.06")
        if index == shock_at:
            step = Decimal("0.2")
        quote += step
        result.append(Tick(1_000 + index * 2, quote, pip_size=2))
    return result


def test_features_are_causal_and_future_mutation_does_not_change_prefix() -> None:
    original = _ticks(150)
    changed = list(original)
    changed[-1] = Tick(changed[-1].epoch, changed[-1].quote + Decimal("10"), 2)

    first = build_accu_examples(
        original,
        barrier=Decimal("0.0005"),
        horizon=3,
        cadence_seconds=2,
        volatility_window=20,
        range_window=50,
    )
    second = build_accu_examples(
        changed,
        barrier=Decimal("0.0005"),
        horizon=3,
        cadence_seconds=2,
        volatility_window=20,
        range_window=50,
    )

    assert first[:-3] == second[:-3]


def test_discontinuity_resets_warmup_and_survival_never_crosses_gap() -> None:
    ticks = _ticks(90)
    ticks[70] = Tick(ticks[69].epoch + 20, ticks[70].quote, 2)
    for index in range(71, len(ticks)):
        ticks[index] = Tick(ticks[index - 1].epoch + 2, ticks[index].quote, 2)

    examples = build_accu_examples(
        ticks,
        barrier=Decimal("0.0005"),
        horizon=3,
        cadence_seconds=2,
        volatility_window=5,
        range_window=10,
    )

    assert all(not (example.index < 70 <= example.index + 3) for example in examples)
    assert min(example.index for example in examples if example.segment_id == 1) >= 79


def test_survival_and_economic_proxy_are_computed_from_future_transitions() -> None:
    examples = build_accu_examples(
        _ticks(100, shock_at=80),
        barrier=Decimal("0.0005"),
        horizon=3,
        cadence_seconds=2,
        volatility_window=5,
        range_window=10,
    )
    before_shock = next(item for item in examples if item.index == 79)
    stable = next(item for item in examples if item.index == 60)
    assert before_shock.survived is False
    assert stable.survived is True

    result = evaluate_accu_proxy(examples, growth_rate=Decimal("0.05"), spec=_spec())
    assert result.classification is AccuTerminalClassification.ACCU_PROXY_ONLY
    assert result.baseline_count > 0
    measured = [metric for metric in result.rules if metric.entry_count > 0]
    assert measured
    assert all(metric.brier_score is not None and metric.brier_score >= 0 for metric in measured)
    assert all(metric.economic_proxy is not None for metric in measured)


def test_engine_is_deterministic_and_zeroizes_acquired_ticks() -> None:
    spec = _spec()
    acquired = _ticks(500)

    first = run_ephemeral_accu(
        spec=spec,
        acquire_ticks=lambda symbol, count: acquired,
        acquire_barriers=lambda symbol, rates: {rate: Decimal("0.0005") for rate in rates},
    )
    assert acquired == []

    second_ticks = _ticks(500)
    second = run_ephemeral_accu(
        spec=spec,
        acquire_ticks=lambda symbol, count: second_ticks,
        acquire_barriers=lambda symbol, rates: {rate: Decimal("0.0005") for rate in rates},
    )
    assert first == second
    assert second_ticks == []
    assert second.classification is AccuTerminalClassification.ACCU_PROXY_ONLY
