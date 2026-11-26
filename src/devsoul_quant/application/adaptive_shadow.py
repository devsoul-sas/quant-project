"""In-memory prequential evaluation for the S3.8 shadow pilot."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from decimal import Decimal

from devsoul_quant.domain.adaptive_intelligence import (
    FeatureVector,
    IncrementalGaussianNaiveBayes,
    IncrementalLogisticRegression,
    InvalidAdaptiveInput,
    build_adaptive_features,
)
from devsoul_quant.domain.digit_strategy import last_digit
from devsoul_quant.domain.replay import Tick

_MODEL_NAMES = (
    "CONSTANT_0_5",
    "CAUSAL_FREQUENCY",
    "CONTROLLED_RANDOM",
    "MOMENTUM",
    "LOGISTIC",
    "GAUSSIAN_NB",
)
_EPSILON = Decimal("0.000000000001")


@dataclass(frozen=True, slots=True)
class AdaptivePrediction:
    """One pending next-market-tick prediction, never a contract outcome."""

    epoch: int
    probabilities: tuple[tuple[str, Decimal], ...]

    def probability(self, model: str) -> Decimal:
        for name, probability in self.probabilities:
            if name == model:
                return probability
        raise KeyError(model)


@dataclass(frozen=True, slots=True)
class AdaptiveModelMetrics:
    """Aggregate session-local proper scores for one model."""

    model: str
    observations: int
    brier_score: Decimal | None
    log_loss: Decimal | None
    accuracy: Decimal | None
    expected_calibration_error: Decimal | None
    quoted_opportunities: int
    signals: int
    signal_coverage: Decimal | None
    mean_break_even: Decimal | None
    mean_estimated_value: Decimal | None
    brier_improvement_vs_causal: Decimal | None = None
    first_half_brier_improvement: Decimal | None = None
    second_half_brier_improvement: Decimal | None = None
    bootstrap_lower_bound: Decimal | None = None


@dataclass(frozen=True, slots=True)
class AdaptiveEvaluationSnapshot:
    """Non-reconstructive in-memory prequential state."""

    resolved_labels: int
    evaluation_labels: int
    pending_labels: int
    models: tuple[AdaptiveModelMetrics, ...]
    decision: str = "INSUFFICIENT_EVIDENCE"
    candidate_models: tuple[str, ...] = ()
    decision_reasons: tuple[str, ...] = ("INFERENCE_NOT_FINALIZED",)
    parity_resolved_labels: int = 0
    parity_constant_brier: Decimal | None = None
    parity_frequency_brier: Decimal | None = None

    def for_model(self, model: str) -> AdaptiveModelMetrics:
        for metrics in self.models:
            if metrics.model == model:
                return metrics
        raise KeyError(model)


@dataclass(slots=True)
class _PendingPrediction:
    decision_quote: Decimal
    features: FeatureVector
    probabilities: dict[str, Decimal]
    parity_constant_probability: Decimal
    parity_frequency_probability: Decimal
    evaluable: bool


@dataclass(slots=True)
class _ScoreAccumulator:
    probabilities: list[Decimal]
    labels: list[int]
    break_evens: list[Decimal]
    estimated_values: list[Decimal]
    signals: int

    @classmethod
    def empty(cls) -> _ScoreAccumulator:
        return cls([], [], [], [], 0)

    def add(self, probability: Decimal, label: int) -> None:
        self.probabilities.append(probability)
        self.labels.append(label)

    def add_opportunity(
        self, *, break_even: Decimal, estimated_value: Decimal, signal: bool
    ) -> None:
        self.break_evens.append(break_even)
        self.estimated_values.append(estimated_value)
        self.signals += int(signal)

    def metrics(self, model: str) -> AdaptiveModelMetrics:
        count = len(self.labels)
        opportunities = len(self.break_evens)
        opportunity_count = Decimal(opportunities) if opportunities else None
        signal_coverage = (
            Decimal(self.signals) / opportunity_count if opportunity_count is not None else None
        )
        mean_break_even = (
            sum(self.break_evens, start=Decimal("0")) / opportunity_count
            if opportunity_count is not None
            else None
        )
        mean_estimated_value = (
            sum(self.estimated_values, start=Decimal("0")) / opportunity_count
            if opportunity_count is not None
            else None
        )
        if not count:
            return AdaptiveModelMetrics(
                model=model,
                observations=0,
                brier_score=None,
                log_loss=None,
                accuracy=None,
                expected_calibration_error=None,
                quoted_opportunities=opportunities,
                signals=self.signals,
                signal_coverage=signal_coverage,
                mean_break_even=mean_break_even,
                mean_estimated_value=mean_estimated_value,
            )
        denominator = Decimal(count)
        brier = (
            sum(
                (
                    (probability - Decimal(label)) ** 2
                    for probability, label in zip(self.probabilities, self.labels, strict=True)
                ),
                start=Decimal("0"),
            )
            / denominator
        )
        log_loss = (
            sum(
                (
                    -(
                        Decimal(label) * max(_EPSILON, min(Decimal(1) - _EPSILON, probability)).ln()
                        + Decimal(1 - label)
                        * (Decimal(1) - max(_EPSILON, min(Decimal(1) - _EPSILON, probability))).ln()
                    )
                    for probability, label in zip(self.probabilities, self.labels, strict=True)
                ),
                start=Decimal("0"),
            )
            / denominator
        )
        correct = sum(
            (probability >= Decimal("0.5")) is bool(label)
            for probability, label in zip(self.probabilities, self.labels, strict=True)
        )
        calibration_total = Decimal("0")
        for bin_index in range(10):
            members = tuple(
                (probability, label)
                for probability, label in zip(self.probabilities, self.labels, strict=True)
                if min(9, int(probability * Decimal(10))) == bin_index
            )
            if not members:
                continue
            member_count = Decimal(len(members))
            mean_probability = sum((item[0] for item in members), start=Decimal("0")) / member_count
            mean_label = (
                sum((Decimal(item[1]) for item in members), start=Decimal("0")) / member_count
            )
            calibration_total += member_count / denominator * abs(mean_probability - mean_label)
        return AdaptiveModelMetrics(
            model=model,
            observations=count,
            brier_score=brier,
            log_loss=log_loss,
            accuracy=Decimal(correct) / denominator,
            expected_calibration_error=calibration_total,
            quoted_opportunities=opportunities,
            signals=self.signals,
            signal_coverage=signal_coverage,
            mean_break_even=mean_break_even,
            mean_estimated_value=mean_estimated_value,
        )

    def clear(self) -> None:
        self.probabilities.clear()
        self.labels.clear()
        self.break_evens.clear()
        self.estimated_values.clear()
        self.signals = 0


class AdaptivePrequentialEvaluator:
    """Predict, resolve, score, then learn with one non-overlapping pending label."""

    def __init__(self, *, warmup_labels: int = 120, seed: int = 38) -> None:
        if type(warmup_labels) is not int or warmup_labels < 0:
            raise InvalidAdaptiveInput("warmup_labels must be a non-negative integer")
        if type(seed) is not int:
            raise InvalidAdaptiveInput("seed must be an integer")
        self._warmup_labels = warmup_labels
        self._seed = seed
        self._logistic = IncrementalLogisticRegression(feature_count=6)
        self._gaussian = IncrementalGaussianNaiveBayes(feature_count=6)
        self._history: list[Tick] = []
        self._pending: _PendingPrediction | None = None
        self._resolved_labels = 0
        self._positive_labels = 0
        self._even_labels = 0
        self._prediction_index = 0
        self._scores = {name: _ScoreAccumulator.empty() for name in _MODEL_NAMES}
        self._parity_constant = _ScoreAccumulator.empty()
        self._parity_frequency = _ScoreAccumulator.empty()

    def observe(self, tick: Tick) -> AdaptivePrediction | None:
        if self._history and tick.epoch <= self._history[-1].epoch:
            raise InvalidAdaptiveInput("ticks must arrive in strictly increasing order")
        self._history.append(tick)
        if self._pending is not None:
            label = int(tick.quote > self._pending.decision_quote)
            parity_label = int(last_digit(tick) % 2 == 0)
            if self._pending.evaluable:
                for name, probability in self._pending.probabilities.items():
                    self._scores[name].add(probability, label)
                self._parity_constant.add(self._pending.parity_constant_probability, parity_label)
                self._parity_frequency.add(self._pending.parity_frequency_probability, parity_label)
            self._logistic.learn(self._pending.features, label)
            self._gaussian.learn(self._pending.features, label)
            self._resolved_labels += 1
            self._positive_labels += label
            self._even_labels += parity_label
            self._pending = None
        if len(self._history) < 6:
            return None
        features = build_adaptive_features(self._history, decision_epoch=tick.epoch)
        causal_frequency = Decimal(self._positive_labels + 1) / Decimal(self._resolved_labels + 2)
        parity_frequency = Decimal(self._even_labels + 1) / Decimal(self._resolved_labels + 2)
        if len(self._history) < 2 or tick.quote == self._history[-2].quote:
            momentum = Decimal("0.5")
        else:
            momentum = Decimal("0.55") if tick.quote > self._history[-2].quote else Decimal("0.45")
        generator = random.Random(self._seed + self._prediction_index)
        controlled_random = Decimal("0.55") if generator.randrange(2) else Decimal("0.45")
        probabilities = {
            "CONSTANT_0_5": Decimal("0.5"),
            "CAUSAL_FREQUENCY": causal_frequency,
            "CONTROLLED_RANDOM": controlled_random,
            "MOMENTUM": momentum,
            "LOGISTIC": self._logistic.predict_probability(features),
            "GAUSSIAN_NB": self._gaussian.predict_probability(features),
        }
        self._pending = _PendingPrediction(
            decision_quote=tick.quote,
            features=features,
            probabilities=probabilities,
            parity_constant_probability=Decimal("0.5"),
            parity_frequency_probability=parity_frequency,
            evaluable=self._resolved_labels >= self._warmup_labels,
        )
        self._prediction_index += 1
        return AdaptivePrediction(tick.epoch, tuple(probabilities.items()))

    def snapshot(self) -> AdaptiveEvaluationSnapshot:
        models = tuple(self._scores[name].metrics(name) for name in _MODEL_NAMES)
        observations = models[0].observations
        parity_constant = self._parity_constant.metrics("PARITY_CONSTANT_0_5")
        parity_frequency = self._parity_frequency.metrics("PARITY_CAUSAL_FREQUENCY")
        return AdaptiveEvaluationSnapshot(
            resolved_labels=self._resolved_labels,
            evaluation_labels=observations,
            pending_labels=int(self._pending is not None),
            models=models,
            parity_resolved_labels=self._resolved_labels,
            parity_constant_brier=parity_constant.brier_score,
            parity_frequency_brier=parity_frequency.brier_score,
        )

    def final_snapshot(self) -> AdaptiveEvaluationSnapshot:
        snapshot = self.snapshot()
        if snapshot.evaluation_labels < 1200:
            return AdaptiveEvaluationSnapshot(
                resolved_labels=snapshot.resolved_labels,
                evaluation_labels=snapshot.evaluation_labels,
                pending_labels=snapshot.pending_labels,
                models=snapshot.models,
                decision="INSUFFICIENT_EVIDENCE",
                decision_reasons=("EVALUATION_SAMPLE_BELOW_1200",),
                parity_resolved_labels=snapshot.parity_resolved_labels,
                parity_constant_brier=snapshot.parity_constant_brier,
                parity_frequency_brier=snapshot.parity_frequency_brier,
            )
        baseline = self._scores["CAUSAL_FREQUENCY"]
        enriched: dict[str, AdaptiveModelMetrics] = {item.model: item for item in snapshot.models}
        candidates: list[str] = []
        for offset, name in enumerate(("LOGISTIC", "GAUSSIAN_NB")):
            accumulator = self._scores[name]
            differences = tuple(
                (baseline_probability - Decimal(label)) ** 2
                - (model_probability - Decimal(label)) ** 2
                for baseline_probability, model_probability, label in zip(
                    baseline.probabilities,
                    accumulator.probabilities,
                    accumulator.labels,
                    strict=True,
                )
            )
            midpoint = len(differences) // 2
            improvement = self._mean(differences)
            first_half = self._mean(differences[:midpoint])
            second_half = self._mean(differences[midpoint:])
            lower_bound = self._moving_block_lower_bound(
                differences,
                seed=self._seed + offset,
            )
            metrics = replace(
                enriched[name],
                brier_improvement_vs_causal=improvement,
                first_half_brier_improvement=first_half,
                second_half_brier_improvement=second_half,
                bootstrap_lower_bound=lower_bound,
            )
            enriched[name] = metrics
            baseline_metrics = enriched["CAUSAL_FREQUENCY"]
            if (
                improvement >= Decimal("0.005")
                and first_half > 0
                and second_half > 0
                and lower_bound > 0
                and metrics.expected_calibration_error is not None
                and metrics.expected_calibration_error <= Decimal("0.05")
                and metrics.log_loss is not None
                and baseline_metrics.log_loss is not None
                and metrics.log_loss <= baseline_metrics.log_loss + Decimal("0.01")
                and metrics.quoted_opportunities >= 30
                and metrics.signal_coverage is not None
                and metrics.signal_coverage >= Decimal("0.05")
                and metrics.mean_estimated_value is not None
                and metrics.mean_estimated_value > 0
            ):
                candidates.append(name)
        final_models = tuple(enriched[item.model] for item in snapshot.models)
        return AdaptiveEvaluationSnapshot(
            resolved_labels=snapshot.resolved_labels,
            evaluation_labels=snapshot.evaluation_labels,
            pending_labels=snapshot.pending_labels,
            models=final_models,
            decision="GO" if candidates else "NO_GO",
            candidate_models=tuple(candidates),
            decision_reasons=(
                ("CANDIDATE_GATE_PASSED",)
                if candidates
                else ("NO_MODEL_PASSED_ALL_PREREGISTERED_GATES",)
            ),
            parity_resolved_labels=snapshot.parity_resolved_labels,
            parity_constant_brier=snapshot.parity_constant_brier,
            parity_frequency_brier=snapshot.parity_frequency_brier,
        )

    @staticmethod
    def _mean(values: tuple[Decimal, ...]) -> Decimal:
        if not values:
            raise InvalidAdaptiveInput("cannot average an empty evaluation segment")
        return sum(values, start=Decimal("0")) / Decimal(len(values))

    @staticmethod
    def _moving_block_lower_bound(differences: tuple[Decimal, ...], *, seed: int) -> Decimal:
        block_size = 60
        iterations = 2000
        if len(differences) < block_size:
            raise InvalidAdaptiveInput("moving-block bootstrap requires at least 60 labels")
        generator = random.Random(seed)
        means: list[Decimal] = []
        count = len(differences)
        for _ in range(iterations):
            sampled: list[Decimal] = []
            while len(sampled) < count:
                start = generator.randrange(count)
                take = min(block_size, count - len(sampled))
                sampled.extend(differences[(start + offset) % count] for offset in range(take))
            means.append(sum(sampled, start=Decimal("0")) / Decimal(count))
        means.sort()
        return means[49]

    def observe_quotes(
        self,
        prediction: AdaptivePrediction,
        *,
        call_break_even: Decimal,
        put_break_even: Decimal,
    ) -> None:
        if (
            self._pending is None
            or not self._history
            or prediction.epoch != self._history[-1].epoch
        ):
            raise InvalidAdaptiveInput("quotes must correspond to the current pending prediction")
        for value in (call_break_even, put_break_even):
            if not isinstance(value, Decimal) or not value.is_finite() or not 0 < value < 1:
                raise InvalidAdaptiveInput(
                    "break-even values must be finite Decimals inside (0, 1)"
                )
        for name, probability in prediction.probabilities:
            predicts_rise = probability >= Decimal("0.5")
            selected_probability = probability if predicts_rise else Decimal(1) - probability
            break_even = call_break_even if predicts_rise else put_break_even
            net_payout = Decimal(1) / break_even - Decimal(1)
            estimated_value = selected_probability * net_payout - (
                Decimal(1) - selected_probability
            )
            self._scores[name].add_opportunity(
                break_even=break_even,
                estimated_value=estimated_value,
                signal=selected_probability >= break_even + Decimal("0.01"),
            )

    def clear(self) -> None:
        self._history.clear()
        self._pending = None
        self._resolved_labels = 0
        self._positive_labels = 0
        self._even_labels = 0
        self._prediction_index = 0
        self._logistic.clear()
        self._gaussian.clear()
        for accumulator in self._scores.values():
            accumulator.clear()
        self._parity_constant.clear()
        self._parity_frequency.clear()
