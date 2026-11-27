"""S3.12/H1-V2 — Step-direction dependence, prequential evaluation.

Implements ``STEP_DIRECTION_DEPENDENCE_V2`` (S3.12 prospective amendment 002)
while preserving ``STEP_DIRECTION_DEPENDENCE_V1`` (S3.11) as a frozen secondary
reference. Pure and deterministic: it consumes owned ``Tick`` objects, keeps a
fixed-size state (O(1) amortized per tick), and returns only an in-memory result
that callers discard after use.

Four models are compared prequentially on the direction of the next step:

- ``MEMORYLESS``         — the warm-up frozen ``P(UP)`` (primary baseline).
- ``FREQUENCY_CAUSAL``   — Laplace-smoothed causal cumulative ``P(UP)`` (control).
- ``MARKOV_1``           — ``P(UP | direction_{t-1})`` from the warm-up
                           Dirichlet(alpha=1) smoothed 2x2 transition matrix
                           (frozen secondary reference).
- ``MARKOV_1_ADAPTIVE``  — ``P(UP | direction_{t-1})`` from the same
                           Dirichlet(alpha=1) estimator whose 2x2 transition
                           counters are updated causally after each prediction
                           is scored (the V2 candidate).

FLAT and discontinuous transitions are excluded causally (never imputed).
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from devsoul_quant.domain.replay import Tick

_EPSILON = Decimal("0.000000000001")
_MINIMUM_EFFECTIVE_SAMPLE = 2178
_MAXIMUM_FLAT_FRACTION = Decimal("0.05")
_BOOTSTRAP_BLOCK_SIZE = 60
_BOOTSTRAP_ITERATIONS = 2000


class StepDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


class InvalidStepDirection(ValueError):
    """Raised when the step sequence is ambiguous or non-causal."""


def classify_step(previous_quote: Decimal, quote: Decimal) -> StepDirection:
    """Classify one step between consecutive quotes without imputing FLAT."""
    if not isinstance(previous_quote, Decimal) or not isinstance(quote, Decimal):
        raise InvalidStepDirection("quotes must be Decimals")
    if not previous_quote.is_finite() or not quote.is_finite():
        raise InvalidStepDirection("quotes must be finite")
    step = quote - previous_quote
    if step > 0:
        return StepDirection.UP
    if step < 0:
        return StepDirection.DOWN
    return StepDirection.FLAT


def _modal_positive(gaps: Sequence[int]) -> int | None:
    positive = [gap for gap in gaps if gap > 0]
    if not positive:
        return None
    ((mode, _count),) = Counter(positive).most_common(1)
    return mode


@dataclass(frozen=True, slots=True)
class StepDirectionModelMetrics:
    """Aggregate proper scores for one model over the forward sample."""

    model: str
    observations: int
    brier_score: Decimal | None
    log_loss: Decimal | None
    accuracy: Decimal | None


@dataclass(frozen=True, slots=True)
class OperationalDiagnostic:
    """Sanitized, ephemeral operational diagnosis for one campaign run.

    Carries only lifecycle facts — never tokens, OTP URLs, payloads or
    restricted market data — so it can travel alongside the result without
    leaking provider credentials or feed content.
    """

    phase: str  # "collecting" | "finalizing"
    stop_reason: str  # one of the six differentiated stop reasons below
    completed_batches: int
    reconnections: int
    deadline_reached: bool


@dataclass(frozen=True, slots=True)
class StepDirectionResult:
    """Ephemeral H1 result. Quantitative fields live only in this object."""

    classification: str
    decision_reasons: tuple[str, ...]
    ticks_received: int
    warmup_transitions: int
    valid_transitions: int
    flat_transitions: int
    discontinuous_transitions: int
    nominal_cadence: int | None
    effective_sample_size: Decimal | None
    warmup_p_up: Decimal | None
    causal_p_up: Decimal | None
    transition_matrix: tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]] | None
    lag1_chi_square: Decimal | None
    models: tuple[StepDirectionModelMetrics, ...]
    improvement_memoryless_adaptive: Decimal | None
    improvement_memoryless_markov: Decimal | None
    improvement_causal_adaptive: Decimal | None
    first_half_improvement: Decimal | None
    second_half_improvement: Decimal | None
    bootstrap_lower_bound: Decimal | None
    p_marginal: Decimal | None
    p_lag1: Decimal | None
    holm_significant_marginal: bool
    holm_significant_lag1: bool
    economic_eligibility: str
    contractual_correspondence: str
    operational_diagnostic: OperationalDiagnostic | None

    def for_model(self, model: str) -> StepDirectionModelMetrics:
        for metrics in self.models:
            if metrics.model == model:
                return metrics
        raise KeyError(model)


class StepDirectionPrequentialEvaluator:
    """Predict, resolve, score and update the three direction models causally."""

    def __init__(
        self,
        *,
        warmup_transitions: int = 120,
        seed: int = 42,
        cadence: int | None = None,
        relevance_threshold: Decimal = Decimal("0"),
    ) -> None:
        if type(warmup_transitions) is not int or warmup_transitions < 2:
            raise InvalidStepDirection("warmup_transitions must be an integer >= 2")
        if type(seed) is not int:
            raise InvalidStepDirection("seed must be an integer")
        if cadence is not None and (type(cadence) is not int or cadence < 1):
            raise InvalidStepDirection("cadence must be a positive integer or None")
        self._warmup_transitions = warmup_transitions
        self._seed = seed
        self._frozen_cadence = cadence
        self._relevance_threshold = relevance_threshold
        self.clear()

    def clear(self) -> None:
        self._previous: Tick | None = None
        self._previous_direction: int | None = None
        self._pending: dict[str, Decimal] | None = None
        self._warmup_records: list[tuple[int, int]] = []
        self._warmup_gaps: list[int] = []
        self._warmup_up = 0
        self._warmup_down = 0
        self._warmup_count = 0
        self._warmup_p_up: Decimal | None = None
        self._transition: tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]] | None = None
        self._adaptive_counts: list[list[int]] = [[1, 1], [1, 1]]
        self._causal_up = 0
        self._causal_valid = 0
        self._ticks_received = 0
        self._flat = 0
        self._discontinuous = 0
        self._predictions: dict[str, list[Decimal]] = {
            "MEMORYLESS": [],
            "FREQUENCY_CAUSAL": [],
            "MARKOV_1": [],
            "MARKOV_1_ADAPTIVE": [],
        }
        self._labels: list[int] = []
        self._forward_directions: list[int] = []

    # -- warm-up --------------------------------------------------------------

    def _freeze_warmup(self) -> None:
        cadence = (
            self._frozen_cadence
            if self._frozen_cadence is not None
            else _modal_positive(self._warmup_gaps)
        )
        if cadence is None:
            raise InvalidStepDirection("cannot infer a nominal tick cadence from warm-up")
        self._frozen_cadence = cadence
        total = self._warmup_up + self._warmup_down
        self._warmup_p_up = Decimal(self._warmup_up) / Decimal(total) if total else Decimal("0.5")
        counts = [[0, 0], [0, 0]]
        for previous, current in self._warmup_records:
            counts[previous][current] += 1
        row0 = (
            (Decimal(counts[0][0]) + Decimal(1)) / Decimal(counts[0][0] + counts[0][1] + 2),
            (Decimal(counts[0][1]) + Decimal(1)) / Decimal(counts[0][0] + counts[0][1] + 2),
        )
        row1 = (
            (Decimal(counts[1][0]) + Decimal(1)) / Decimal(counts[1][0] + counts[1][1] + 2),
            (Decimal(counts[1][1]) + Decimal(1)) / Decimal(counts[1][0] + counts[1][1] + 2),
        )
        self._transition = (row0, row1)
        self._adaptive_counts = [
            [counts[0][0] + 1, counts[0][1] + 1],
            [counts[1][0] + 1, counts[1][1] + 1],
        ]
        self._warmup_records = []
        self._warmup_gaps = []

    # -- prediction -----------------------------------------------------------

    def _predictions_for(self, previous_direction: int) -> dict[str, Decimal]:
        assert self._warmup_p_up is not None
        assert self._transition is not None
        causal = Decimal(self._causal_up + 1) / Decimal(self._causal_valid + 2)
        return {
            "MEMORYLESS": self._warmup_p_up,
            "FREQUENCY_CAUSAL": causal,
            "MARKOV_1": self._transition[previous_direction][1],
            "MARKOV_1_ADAPTIVE": self._adaptive_p_up_given(previous_direction),
        }

    def _adaptive_p_up_given(self, previous_direction: int) -> Decimal:
        row = self._adaptive_counts[previous_direction]
        return Decimal(row[1]) / Decimal(row[0] + row[1])

    # -- streaming ------------------------------------------------------------

    def observe_tick(self, tick: Tick) -> None:
        if not isinstance(tick, Tick):
            raise InvalidStepDirection("tick must be a Tick")
        if self._previous is not None and tick.epoch <= self._previous.epoch:
            raise InvalidStepDirection("tick epochs must be strictly increasing")
        self._ticks_received += 1
        if self._previous is None:
            self._previous = tick
            return
        gap = tick.epoch - self._previous.epoch
        direction = classify_step(self._previous.quote, tick.quote)
        self._previous = tick

        if self._transition is None:
            self._warmup_gaps.append(gap)
            if direction is StepDirection.FLAT:
                self._flat += 1
                return
            current = 1 if direction is StepDirection.UP else 0
            self._warmup_up += current
            self._warmup_down += 1 - current
            self._warmup_count += 1
            if self._previous_direction is not None:
                self._warmup_records.append((self._previous_direction, current))
            self._previous_direction = current
            if self._warmup_count >= self._warmup_transitions:
                self._freeze_warmup()
            return

        if not (self._frozen_cadence is None or gap == self._frozen_cadence):
            self._discontinuous += 1
            self._pending = None
            self._previous_direction = None
            return
        if direction is StepDirection.FLAT:
            self._flat += 1
            self._pending = None
            self._previous_direction = None
            return

        label = 1 if direction is StepDirection.UP else 0
        if self._pending is not None:
            previous_direction = self._previous_direction
            assert previous_direction is not None
            for name, probability in self._pending.items():
                self._predictions[name].append(probability)
            self._labels.append(label)
            self._adaptive_counts[previous_direction][label] += 1
        self._forward_directions.append(label)
        self._causal_valid += 1
        self._causal_up += label
        self._previous_direction = label
        self._pending = self._predictions_for(label)

    # -- scoring helpers ------------------------------------------------------

    @staticmethod
    def _metrics(
        probabilities: Sequence[Decimal], labels: Sequence[int], model: str
    ) -> StepDirectionModelMetrics:
        count = len(probabilities)
        if not count:
            return StepDirectionModelMetrics(
                model=model, observations=0, brier_score=None, log_loss=None, accuracy=None
            )
        brier = sum(
            (p - Decimal(label)) ** 2 for p, label in zip(probabilities, labels, strict=True)
        ) / Decimal(count)
        log_loss = sum(
            -(
                Decimal(label) * _clip_probability(p).ln()
                + Decimal(1 - label) * (Decimal(1) - _clip_probability(p)).ln()
            )
            for p, label in zip(probabilities, labels, strict=True)
        ) / Decimal(count)
        correct = sum(
            (p >= Decimal("0.5")) is bool(label)
            for p, label in zip(probabilities, labels, strict=True)
        )
        return StepDirectionModelMetrics(
            model=model,
            observations=count,
            brier_score=brier,
            log_loss=log_loss,
            accuracy=Decimal(correct) / Decimal(count),
        )

    @staticmethod
    def _moving_block_bootstrap(
        differences: Sequence[Decimal], *, seed: int
    ) -> tuple[Decimal, Decimal]:
        count = len(differences)
        block_size = min(_BOOTSTRAP_BLOCK_SIZE, count)
        generator = random.Random(seed)
        means: list[Decimal] = []
        for _ in range(_BOOTSTRAP_ITERATIONS):
            sampled: list[Decimal] = []
            while len(sampled) < count:
                start = generator.randrange(count)
                take = min(block_size, count - len(sampled))
                sampled.extend(differences[(start + offset) % count] for offset in range(take))
            means.append(sum(sampled, start=Decimal("0")) / Decimal(count))
        means.sort()
        lower = means[49]
        non_positive = sum(1 for value in means if value <= 0)
        p_value = Decimal(non_positive) / Decimal(len(means))
        return lower, p_value

    @staticmethod
    def _effective_sample_size(series: Sequence[Decimal]) -> Decimal:
        count = len(series)
        if count < 2:
            return Decimal(count)
        mean = sum(series, start=Decimal("0")) / Decimal(count)
        variance = sum((value - mean) ** 2 for value in series) / Decimal(count)
        if variance == 0:
            return Decimal(count)
        scale = mean * mean if mean != 0 else Decimal("1")
        if variance <= scale * Decimal("1e-6"):
            # Effectively constant series: the mean is precisely determined and
            # the lag autocorrelation of negligible noise does not reduce the
            # effective sample size of the improvement estimate.
            return Decimal(count)
        total = Decimal("1")
        for lag in range(1, min(20, count - 1) + 1):
            covariance = sum(
                (series[i] - mean) * (series[i + lag] - mean) for i in range(count - lag)
            ) / Decimal(count)
            rho = covariance / variance
            if rho <= 0:
                break
            total += Decimal(2) * rho
        return Decimal(count) / total

    @staticmethod
    def _marginal_p_value(p_up: Decimal, n_eff: Decimal) -> Decimal:
        if n_eff <= 0:
            return Decimal("1")
        z = abs(float(p_up) - 0.5) / math.sqrt(0.25 / float(n_eff))
        return Decimal(str(2.0 * (0.5 * math.erfc(z / math.sqrt(2.0)))))

    def _lag1_chi_square(self) -> Decimal | None:
        counts = [[0, 0], [0, 0]]
        for index in range(1, len(self._forward_directions)):
            previous = self._forward_directions[index - 1]
            current = self._forward_directions[index]
            counts[previous][current] += 1
        total = sum(sum(row) for row in counts)
        if total < 1:
            return None
        marginals = [sum(row) for row in counts]
        statistic = Decimal("0")
        for row in (0, 1):
            for column in (0, 1):
                expected = Decimal(marginals[row]) * Decimal(marginals[column]) / Decimal(total)
                if expected > 0:
                    statistic += (Decimal(counts[row][column]) - expected) ** 2 / expected
        return statistic

    # -- finalize -------------------------------------------------------------

    def finalize(self) -> StepDirectionResult:
        valid = len(self._labels)
        flat_total = self._flat + valid
        flat_fraction = Decimal(self._flat) / Decimal(flat_total) if flat_total else Decimal("0")
        models = tuple(
            self._metrics(self._predictions[name], self._labels, name)
            for name in ("MEMORYLESS", "FREQUENCY_CAUSAL", "MARKOV_1", "MARKOV_1_ADAPTIVE")
        )
        causal = self._pick(models, "FREQUENCY_CAUSAL")
        adaptive = self._pick(models, "MARKOV_1_ADAPTIVE")

        if valid < 2 or causal.brier_score is None or adaptive.brier_score is None:
            return self._build(
                "H1_INSUFFICIENT_EVIDENCE",
                ("FORWARD_SAMPLE_BELOW_MINIMUM",),
                valid,
                flat_fraction,
                models,
            )

        # Primary gate: adaptive Markov candidate vs the causal frequency control
        # (which learns the marginal but not lag-1). This isolates lag-1
        # dependence from the marginal-learning advantage the causal candidate
        # would otherwise trivially hold over the frozen MEMORYLESS baseline.
        differences = tuple(
            (f - Decimal(label)) ** 2 - (a - Decimal(label)) ** 2
            for f, a, label in zip(
                self._predictions["FREQUENCY_CAUSAL"],
                self._predictions["MARKOV_1_ADAPTIVE"],
                self._labels,
                strict=True,
            )
        )
        midpoint = len(differences) // 2
        improvement = sum(differences, start=Decimal("0")) / Decimal(len(differences))
        first_half = (
            sum(differences[:midpoint], start=Decimal("0")) / Decimal(midpoint)
            if midpoint
            else Decimal("0")
        )
        second_half = (
            sum(differences[midpoint:], start=Decimal("0")) / Decimal(len(differences) - midpoint)
            if len(differences) - midpoint
            else Decimal("0")
        )
        lower_bound, p_lag1 = self._moving_block_bootstrap(differences, seed=self._seed)
        n_eff = self._effective_sample_size(differences)

        memoryless_differences = tuple(
            (m - Decimal(label)) ** 2 - (a - Decimal(label)) ** 2
            for m, a, label in zip(
                self._predictions["MEMORYLESS"],
                self._predictions["MARKOV_1_ADAPTIVE"],
                self._labels,
                strict=True,
            )
        )
        improvement_memoryless = (
            sum(memoryless_differences, start=Decimal("0")) / Decimal(len(memoryless_differences))
            if memoryless_differences
            else Decimal("0")
        )

        frozen_differences = tuple(
            (m - Decimal(label)) ** 2 - (f - Decimal(label)) ** 2
            for m, f, label in zip(
                self._predictions["MEMORYLESS"],
                self._predictions["MARKOV_1"],
                self._labels,
                strict=True,
            )
        )
        improvement_frozen = (
            sum(frozen_differences, start=Decimal("0")) / Decimal(len(frozen_differences))
            if frozen_differences
            else Decimal("0")
        )

        causal_p_up = (
            Decimal(self._causal_up) / Decimal(self._causal_valid) if self._causal_valid else None
        )
        p_marginal = self._marginal_p_value(causal_p_up, n_eff) if causal_p_up is not None else None
        lag1_chi_square = self._lag1_chi_square()
        holm_marginal, holm_lag1 = _holm(p_marginal, p_lag1)

        if flat_fraction > _MAXIMUM_FLAT_FRACTION:
            classification = "H1_INSUFFICIENT_EVIDENCE"
            reasons: tuple[str, ...] = ("EXCESSIVE_FLAT_FRACTION",)
        elif n_eff < Decimal(_MINIMUM_EFFECTIVE_SAMPLE):
            classification = "H1_INSUFFICIENT_EVIDENCE"
            reasons = ("EFFECTIVE_SAMPLE_BELOW_MINIMUM",)
        else:
            gate_passed = (
                improvement >= self._relevance_threshold
                and first_half > 0
                and second_half > 0
                and lower_bound > 0
                and holm_lag1
            )
            if gate_passed:
                classification = "H1_CANDIDATE_FOR_INDEPENDENT_VALIDATION"
                reasons = ("LAG1_DEPENDENCE_SIGNIFICANT", "PREDICTIVE_IMPROVEMENT_POSITIVE")
            else:
                classification = "H1_NO_EDGE"
                reasons = ("NO_PREDICTIVE_IMPROVEMENT_PASSED_ALL_GATES",)

        return self._build(
            classification,
            reasons,
            valid,
            flat_fraction,
            models,
            improvement=improvement,
            improvement_memoryless_adaptive=improvement_memoryless,
            improvement_memoryless_markov=improvement_frozen,
            first_half=first_half,
            second_half=second_half,
            lower_bound=lower_bound,
            p_marginal=p_marginal,
            p_lag1=p_lag1,
            n_eff=n_eff,
            holm_marginal=holm_marginal,
            holm_lag1=holm_lag1,
            causal_p_up=causal_p_up,
            lag1_chi_square=lag1_chi_square,
        )

    @staticmethod
    def _pick(models: Sequence[StepDirectionModelMetrics], model: str) -> StepDirectionModelMetrics:
        for metrics in models:
            if metrics.model == model:
                return metrics
        raise KeyError(model)

    def _build(
        self,
        classification: str,
        reasons: tuple[str, ...],
        valid: int,
        flat_fraction: Decimal,
        models: tuple[StepDirectionModelMetrics, ...],
        *,
        improvement: Decimal | None = None,
        improvement_memoryless_adaptive: Decimal | None = None,
        improvement_memoryless_markov: Decimal | None = None,
        first_half: Decimal | None = None,
        second_half: Decimal | None = None,
        lower_bound: Decimal | None = None,
        p_marginal: Decimal | None = None,
        p_lag1: Decimal | None = None,
        n_eff: Decimal | None = None,
        holm_marginal: bool = False,
        holm_lag1: bool = False,
        causal_p_up: Decimal | None = None,
        lag1_chi_square: Decimal | None = None,
    ) -> StepDirectionResult:
        return StepDirectionResult(
            classification=classification,
            decision_reasons=reasons,
            ticks_received=self._ticks_received,
            warmup_transitions=self._warmup_count,
            valid_transitions=valid,
            flat_transitions=self._flat,
            discontinuous_transitions=self._discontinuous,
            nominal_cadence=self._frozen_cadence,
            effective_sample_size=n_eff,
            warmup_p_up=self._warmup_p_up,
            causal_p_up=causal_p_up,
            transition_matrix=self._transition,
            lag1_chi_square=lag1_chi_square,
            models=models,
            improvement_memoryless_adaptive=improvement_memoryless_adaptive,
            improvement_memoryless_markov=improvement_memoryless_markov,
            improvement_causal_adaptive=improvement,
            first_half_improvement=first_half,
            second_half_improvement=second_half,
            bootstrap_lower_bound=lower_bound,
            p_marginal=p_marginal,
            p_lag1=p_lag1,
            holm_significant_marginal=holm_marginal,
            holm_significant_lag1=holm_lag1,
            economic_eligibility="UNAVAILABLE",
            contractual_correspondence="RISE_FALL_TICK_EXIT_VS_ENTRY_SHADOW_ONLY",
            operational_diagnostic=None,
        )

    def blocked_result(
        self,
        classification: str,
        reasons: tuple[str, ...],
        *,
        diagnostic: OperationalDiagnostic,
    ) -> StepDirectionResult:
        """Fail-closed result with the real counters observed so far.

        Unlike a synthetic zeroed result, this reports the actual ``ticks_received``,
        ``warmup_transitions``, ``valid_transitions``, ``flat_transitions``,
        ``discontinuous_transitions`` and ``nominal_cadence`` accumulated before the
        failure. Statistical and predictive fields that cannot be computed on partial
        state are reported as ``None`` (never fabricated).
        """
        valid = len(self._labels)
        empty_models = tuple(
            StepDirectionModelMetrics(
                model=name, observations=0, brier_score=None, log_loss=None, accuracy=None
            )
            for name in ("MEMORYLESS", "FREQUENCY_CAUSAL", "MARKOV_1", "MARKOV_1_ADAPTIVE")
        )
        return StepDirectionResult(
            classification=classification,
            decision_reasons=reasons,
            ticks_received=self._ticks_received,
            warmup_transitions=self._warmup_count,
            valid_transitions=valid,
            flat_transitions=self._flat,
            discontinuous_transitions=self._discontinuous,
            nominal_cadence=self._frozen_cadence,
            effective_sample_size=None,
            warmup_p_up=self._warmup_p_up,
            causal_p_up=None,
            transition_matrix=self._transition,
            lag1_chi_square=None,
            models=empty_models,
            improvement_memoryless_adaptive=None,
            improvement_memoryless_markov=None,
            improvement_causal_adaptive=None,
            first_half_improvement=None,
            second_half_improvement=None,
            bootstrap_lower_bound=None,
            p_marginal=None,
            p_lag1=None,
            holm_significant_marginal=False,
            holm_significant_lag1=False,
            economic_eligibility="UNAVAILABLE",
            contractual_correspondence="RISE_FALL_TICK_EXIT_VS_ENTRY_SHADOW_ONLY",
            operational_diagnostic=diagnostic,
        )


def _clip_probability(probability: Decimal) -> Decimal:
    return max(_EPSILON, min(Decimal(1) - _EPSILON, probability))


def _holm(p_marginal: Decimal | None, p_lag1: Decimal | None) -> tuple[bool, bool]:
    """Holm step-down across the two preregistered tests at FWER 0.05."""
    if p_marginal is None or p_lag1 is None:
        return False, False
    alpha = Decimal("0.05")
    p1, p2 = sorted((p_marginal, p_lag1))
    significant_smaller = p1 <= alpha / 2
    significant_larger = significant_smaller and p2 <= alpha
    if p1 == p_marginal:
        return significant_smaller, significant_larger
    return significant_larger, significant_smaller
