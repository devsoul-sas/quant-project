"""Reusable in-memory S4.4 ACCU proxy research engine.

Provider ticks, barriers, feature rows, and metrics are never serialized here.
The caller supplies acquisition functions; acquired mutable tick buffers are
cleared in a ``finally`` block, including on evaluator failure.
"""

from __future__ import annotations

import random
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from devsoul_quant.application.accu_experiment_spec import (
    AccuExperimentSpec,
    AccuRuleSpec,
)
from devsoul_quant.domain.replay import Tick

_ZERO = Decimal(0)
_ONE = Decimal(1)


class AccuTerminalClassification(StrEnum):
    ACCU_PROXY_ONLY = "ACCU_PROXY_ONLY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NO_EDGE = "NO_EDGE"


@dataclass(frozen=True, slots=True)
class AccuExample:
    index: int
    segment_id: int
    streak_age: int
    previous_streak: int
    recent_volatility: Decimal
    range_width: Decimal
    range_position: Decimal
    current_move: Decimal
    survived: bool


@dataclass(frozen=True, slots=True)
class AccuRuleMetric:
    rule_id: str
    entry_count: int
    coverage: Decimal
    survival: Decimal | None
    absolute_lift: Decimal | None
    confidence_lower: Decimal | None
    confidence_upper: Decimal | None
    brier_score: Decimal | None
    calibration_error: Decimal | None
    economic_proxy: Decimal | None
    multiplicity_pass: bool


@dataclass(frozen=True, slots=True)
class AccuEvaluation:
    growth_rate: Decimal
    classification: AccuTerminalClassification
    baseline_count: int
    baseline_survival: Decimal | None
    rules: tuple[AccuRuleMetric, ...]


@dataclass(frozen=True, slots=True)
class AccuRunSummary:
    protocol_version: str
    protocol_hash: str
    classification: AccuTerminalClassification
    evaluations: tuple[AccuEvaluation, ...]


def _survives(
    ticks: Sequence[Tick], index: int, *, horizon: int, cadence_seconds: int, barrier: Decimal
) -> bool | None:
    if index + horizon >= len(ticks):
        return None
    for position in range(index + 1, index + horizon + 1):
        previous = ticks[position - 1]
        current = ticks[position]
        if current.epoch - previous.epoch != cadence_seconds or previous.quote <= _ZERO:
            return None
        move = abs((current.quote - previous.quote) / previous.quote)
        if move > barrier:
            return False
    return True


def build_accu_examples(
    ticks: Sequence[Tick],
    *,
    barrier: Decimal,
    horizon: int,
    cadence_seconds: int,
    volatility_window: int,
    range_window: int,
) -> tuple[AccuExample, ...]:
    """Build causal O(n * range_window) features and forward survival labels."""
    if barrier <= _ZERO:
        raise ValueError("barrier must be positive")
    if horizon < 1 or cadence_seconds < 1:
        raise ValueError("horizon and cadence_seconds must be positive")
    if len(ticks) < 2:
        return ()

    movements: deque[Decimal] = deque(maxlen=volatility_window)
    quotes: deque[Decimal] = deque(maxlen=range_window)
    movement_sum = _ZERO
    streak_age = 0
    previous_streak = 0
    segment_id = 0
    examples: list[AccuExample] = []
    quotes.append(ticks[0].quote)

    for index in range(1, len(ticks)):
        previous = ticks[index - 1]
        current = ticks[index]
        if current.epoch <= previous.epoch:
            raise ValueError("ticks must be strictly ordered")
        if current.epoch - previous.epoch != cadence_seconds:
            segment_id += 1
            movements.clear()
            quotes.clear()
            movement_sum = _ZERO
            streak_age = 0
            previous_streak = 0
            quotes.append(current.quote)
            continue
        if previous.quote <= _ZERO or current.quote <= _ZERO:
            raise ValueError("tick quotes must be positive")

        normalized_move = abs((current.quote - previous.quote) / previous.quote) / barrier
        if len(movements) == volatility_window:
            movement_sum -= movements[0]
        movements.append(normalized_move)
        movement_sum += normalized_move
        quotes.append(current.quote)

        if normalized_move <= _ONE:
            streak_age += 1
        else:
            previous_streak = streak_age
            streak_age = 0

        if len(movements) < volatility_window or len(quotes) < range_window:
            continue
        survived = _survives(
            ticks,
            index,
            horizon=horizon,
            cadence_seconds=cadence_seconds,
            barrier=barrier,
        )
        if survived is None:
            continue
        low = min(quotes)
        high = max(quotes)
        width = high - low
        range_position = _ZERO if width == _ZERO else (current.quote - low) / width
        examples.append(
            AccuExample(
                index=index,
                segment_id=segment_id,
                streak_age=streak_age,
                previous_streak=previous_streak,
                recent_volatility=movement_sum / Decimal(volatility_window),
                range_width=(width / current.quote) / barrier,
                range_position=range_position,
                current_move=normalized_move,
                survived=survived,
            )
        )
    return tuple(examples)


def _matches(example: AccuExample, rule: AccuRuleSpec) -> bool:
    return (
        rule.minimum_streak_age <= example.streak_age <= rule.maximum_streak_age
        and example.previous_streak >= rule.minimum_previous_streak
        and example.recent_volatility <= rule.maximum_recent_volatility
        and example.range_width <= rule.maximum_range_width
        and rule.minimum_range_position <= example.range_position <= rule.maximum_range_position
        and example.current_move <= rule.maximum_current_move
    )


def _mean_boolean(values: Sequence[bool]) -> Decimal | None:
    if not values:
        return None
    return Decimal(sum(values)) / Decimal(len(values))


def _brier(values: Sequence[bool], probability: Decimal) -> Decimal | None:
    if not values:
        return None
    return sum(
        ((probability - (_ONE if value else _ZERO)) ** 2 for value in values),
        start=_ZERO,
    ) / Decimal(len(values))


def _moving_block_lifts(
    holdout: Sequence[AccuExample],
    selected: Sequence[bool],
    *,
    block_length: int,
    resamples: int,
    seed: int,
) -> tuple[Decimal, ...]:
    if not holdout or not any(selected):
        return ()
    block = min(block_length, len(holdout))
    starts = range(0, len(holdout) - block + 1)
    aggregates: list[tuple[int, int, int, int]] = []
    for start in starts:
        total_success = sum(item.survived for item in holdout[start : start + block])
        selected_count = sum(selected[start : start + block])
        selected_success = sum(
            item.survived
            for item, is_selected in zip(
                holdout[start : start + block], selected[start : start + block], strict=True
            )
            if is_selected
        )
        aggregates.append((selected_success, selected_count, total_success, block))
    rng = random.Random(seed)
    draws = (len(holdout) + block - 1) // block
    lifts: list[Decimal] = []
    for _ in range(resamples):
        chosen = [aggregates[rng.randrange(len(aggregates))] for _ in range(draws)]
        selected_success = sum(item[0] for item in chosen)
        selected_count = sum(item[1] for item in chosen)
        if selected_count == 0:
            continue
        total_success = sum(item[2] for item in chosen)
        total_count = sum(item[3] for item in chosen)
        lifts.append(
            Decimal(selected_success) / Decimal(selected_count)
            - Decimal(total_success) / Decimal(total_count)
        )
    return tuple(sorted(lifts))


def _percentile(values: Sequence[Decimal], probability: Decimal) -> Decimal | None:
    if not values:
        return None
    index = int((Decimal(len(values) - 1) * probability).to_integral_value(rounding="ROUND_FLOOR"))
    return values[index]


def evaluate_accu_proxy(
    examples: Sequence[AccuExample],
    *,
    growth_rate: Decimal,
    spec: AccuExperimentSpec,
) -> AccuEvaluation:
    """Evaluate fixed rules without optimizing on validation or holdout."""
    if not examples:
        return AccuEvaluation(
            growth_rate,
            AccuTerminalClassification.INSUFFICIENT_EVIDENCE,
            0,
            None,
            (),
        )
    total_ticks = max(item.index for item in examples) + spec.primary_horizon + 1
    train_end = int(Decimal(total_ticks) * spec.split.train_fraction)
    validation_end = int(
        Decimal(total_ticks) * (spec.split.train_fraction + spec.split.validation_fraction)
    )
    train = tuple(item for item in examples if item.index + spec.primary_horizon < train_end)
    validation = tuple(
        item
        for item in examples
        if train_end + spec.split.purge_ticks <= item.index
        and item.index + spec.primary_horizon < validation_end
    )
    holdout = tuple(
        item for item in examples if validation_end + spec.split.purge_ticks <= item.index
    )
    del validation  # fixed rules: validation is intentionally not used for selection
    baseline = tuple(item.survived for item in holdout)
    baseline_rate = _mean_boolean(baseline)
    family_size = max(1, len(spec.rules) * len(spec.growth_rates) * len(spec.symbols))
    tail = spec.statistics.family_alpha / Decimal(2 * family_size)
    metrics: list[AccuRuleMetric] = []
    for rule_index, rule in enumerate(spec.rules):
        train_selected = tuple(item.survived for item in train if _matches(item, rule))
        selected_mask = tuple(_matches(item, rule) for item in holdout)
        selected_values = tuple(
            item.survived
            for item, is_selected in zip(holdout, selected_mask, strict=True)
            if is_selected
        )
        survival = _mean_boolean(selected_values)
        lift = None if survival is None or baseline_rate is None else survival - baseline_rate
        calibration = _mean_boolean(train_selected)
        brier = None if calibration is None else _brier(selected_values, calibration)
        calibration_error = (
            None if calibration is None or survival is None else abs(survival - calibration)
        )
        economic = (
            None
            if survival is None
            else survival * ((_ONE + growth_rate) ** spec.primary_horizon) - _ONE
        )
        lifts = _moving_block_lifts(
            holdout,
            selected_mask,
            block_length=spec.statistics.block_length,
            resamples=spec.statistics.resamples,
            seed=spec.statistics.seed + rule_index,
        )
        lower = _percentile(lifts, tail)
        upper = _percentile(lifts, _ONE - tail)
        pass_gate = (
            len(selected_values) >= spec.statistics.minimum_rule_entries
            and lift is not None
            and lift >= spec.statistics.minimum_absolute_lift
            and lower is not None
            and lower > _ZERO
            and economic is not None
            and economic > _ZERO
        )
        metrics.append(
            AccuRuleMetric(
                rule_id=rule.rule_id,
                entry_count=len(selected_values),
                coverage=(
                    _ZERO if not holdout else Decimal(len(selected_values)) / Decimal(len(holdout))
                ),
                survival=survival,
                absolute_lift=lift,
                confidence_lower=lower,
                confidence_upper=upper,
                brier_score=brier,
                calibration_error=calibration_error,
                economic_proxy=economic,
                multiplicity_pass=pass_gate,
            )
        )
    enough = any(item.entry_count >= spec.statistics.minimum_rule_entries for item in metrics)
    classification = (
        AccuTerminalClassification.ACCU_PROXY_ONLY
        if enough
        else AccuTerminalClassification.INSUFFICIENT_EVIDENCE
    )
    return AccuEvaluation(
        growth_rate=growth_rate,
        classification=classification,
        baseline_count=len(baseline),
        baseline_survival=baseline_rate,
        rules=tuple(metrics),
    )


def run_ephemeral_accu(
    *,
    spec: AccuExperimentSpec,
    acquire_ticks: Callable[[str, int], list[Tick]],
    acquire_barriers: Callable[[str, tuple[Decimal, ...]], Mapping[Decimal, Decimal]],
) -> AccuRunSummary:
    """Acquire each instrument once, share it across rates, then clear raw ticks."""
    evaluations: list[AccuEvaluation] = []
    for symbol in spec.symbols:
        ticks = acquire_ticks(symbol, spec.maximum_ticks)
        try:
            barriers = acquire_barriers(symbol, spec.growth_rates)
            if set(barriers) != set(spec.growth_rates):
                raise ValueError("one positive barrier is required for every growth rate")
            for rate in spec.growth_rates:
                examples = build_accu_examples(
                    ticks,
                    barrier=barriers[rate],
                    horizon=spec.primary_horizon,
                    cadence_seconds=spec.cadence_seconds,
                    volatility_window=spec.volatility_window,
                    range_window=spec.range_window,
                )
                evaluations.append(evaluate_accu_proxy(examples, growth_rate=rate, spec=spec))
        finally:
            ticks.clear()
    classification = (
        AccuTerminalClassification.ACCU_PROXY_ONLY
        if evaluations
        and all(
            item.classification is AccuTerminalClassification.ACCU_PROXY_ONLY
            for item in evaluations
        )
        else AccuTerminalClassification.INSUFFICIENT_EVIDENCE
    )
    return AccuRunSummary(
        protocol_version=spec.version,
        protocol_hash=spec.spec_hash,
        classification=classification,
        evaluations=tuple(evaluations),
    )
