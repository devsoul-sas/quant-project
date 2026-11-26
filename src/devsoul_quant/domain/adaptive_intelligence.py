"""Ephemeral causal features and incremental models for S3.8."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from itertools import pairwise

from devsoul_quant.domain.replay import Tick


class InvalidAdaptiveInput(ValueError):
    """Raised when adaptive research input is ambiguous or non-causal."""


type FeatureVector = tuple[Decimal, ...]


def _validate_features(features: Sequence[Decimal], feature_count: int) -> FeatureVector:
    if len(features) != feature_count:
        raise InvalidAdaptiveInput("feature vector has the wrong length")
    if any(not isinstance(value, Decimal) or not value.is_finite() for value in features):
        raise InvalidAdaptiveInput("features must be finite Decimals")
    return tuple(features)


def _validate_label(label: object) -> int:
    if type(label) is not int or label not in (0, 1):
        raise InvalidAdaptiveInput("label must be the integer 0 or 1")
    return label


class IncrementalLogisticRegression:
    """Minimal deterministic Decimal SGD model with no persistence surface."""

    def __init__(self, *, feature_count: int) -> None:
        if type(feature_count) is not int or feature_count < 1:
            raise InvalidAdaptiveInput("feature_count must be a positive integer")
        self._feature_count = feature_count
        self._weights = [Decimal("0")] * feature_count
        self._bias = Decimal("0")
        self._learning_rate = Decimal("0.05")
        self._l2 = Decimal("0.001")

    @staticmethod
    def _sigmoid(value: Decimal) -> Decimal:
        bounded = _clip(value, Decimal("-50"), Decimal("50"))
        if bounded >= 0:
            return Decimal(1) / (Decimal(1) + (-bounded).exp())
        exponential = bounded.exp()
        return exponential / (Decimal(1) + exponential)

    def predict_probability(self, features: Sequence[Decimal]) -> Decimal:
        values = _validate_features(features, self._feature_count)
        score = self._bias + sum(
            (weight * value for weight, value in zip(self._weights, values, strict=True)),
            start=Decimal("0"),
        )
        return self._sigmoid(score)

    def learn(self, features: Sequence[Decimal], label: object) -> None:
        values = _validate_features(features, self._feature_count)
        target = Decimal(_validate_label(label))
        error = target - self.predict_probability(values)
        for index, value in enumerate(values):
            gradient = error * value - self._l2 * self._weights[index]
            self._weights[index] += self._learning_rate * gradient
        self._bias += self._learning_rate * error

    def clear(self) -> None:
        self._weights = [Decimal("0")] * self._feature_count
        self._bias = Decimal("0")


class IncrementalGaussianNaiveBayes:
    """Two-class online Gaussian model using Decimal Welford moments."""

    def __init__(self, *, feature_count: int) -> None:
        if type(feature_count) is not int or feature_count < 1:
            raise InvalidAdaptiveInput("feature_count must be a positive integer")
        self._feature_count = feature_count
        self._variance_floor = Decimal("0.000001")
        self.clear()

    def predict_probability(self, features: Sequence[Decimal]) -> Decimal:
        values = _validate_features(features, self._feature_count)
        total = sum(self._counts)
        if total == 0:
            return Decimal("0.5")
        scores: list[Decimal] = []
        for label in (0, 1):
            prior = Decimal(self._counts[label] + 1) / Decimal(total + 2)
            score = prior.ln()
            for index, value in enumerate(values):
                variance = (
                    self._m2[label][index] / Decimal(self._counts[label] - 1)
                    if self._counts[label] > 1
                    else self._variance_floor
                )
                variance = max(self._variance_floor, variance)
                distance = value - self._means[label][index]
                score -= (variance.ln() + distance * distance / variance) / Decimal(2)
            scores.append(score)
        return IncrementalLogisticRegression._sigmoid(scores[1] - scores[0])

    def learn(self, features: Sequence[Decimal], label: object) -> None:
        values = _validate_features(features, self._feature_count)
        target = _validate_label(label)
        self._counts[target] += 1
        count = Decimal(self._counts[target])
        for index, value in enumerate(values):
            delta = value - self._means[target][index]
            self._means[target][index] += delta / count
            delta_after = value - self._means[target][index]
            self._m2[target][index] += delta * delta_after

    def clear(self) -> None:
        self._counts = [0, 0]
        self._means = [
            [Decimal("0")] * self._feature_count,
            [Decimal("0")] * self._feature_count,
        ]
        self._m2 = [
            [Decimal("0")] * self._feature_count,
            [Decimal("0")] * self._feature_count,
        ]


def _clip(value: Decimal, lower: Decimal, upper: Decimal) -> Decimal:
    return min(upper, max(lower, value))


def build_adaptive_features(history: Sequence[Tick], *, decision_epoch: int) -> FeatureVector:
    """Build the frozen six S3.8 features using no tick after ``decision_epoch``."""
    if type(decision_epoch) is not int:
        raise InvalidAdaptiveInput("decision_epoch must be an integer")
    if any(current.epoch <= previous.epoch for previous, current in pairwise(history)):
        raise InvalidAdaptiveInput("tick epochs must be strictly increasing")
    available = tuple(tick for tick in history if tick.epoch <= decision_epoch)
    if not available or available[-1].epoch != decision_epoch:
        raise InvalidAdaptiveInput("decision_epoch must identify an observed tick")
    if len(available) < 6:
        raise InvalidAdaptiveInput("six causal ticks are required")
    window = available[-6:]
    pip_sizes = {tick.pip_size for tick in window}
    if None in pip_sizes or len(pip_sizes) != 1:
        raise InvalidAdaptiveInput("pip_size must be present and constant")
    pip_size = window[0].pip_size
    assert pip_size is not None
    pip = Decimal(1).scaleb(-pip_size)
    movements = tuple(
        (current.quote - previous.quote) / pip for previous, current in pairwise(window)
    )
    lower = Decimal("-5")
    upper = Decimal("5")
    delta_one = _clip(movements[-1], lower, upper)
    delta_three = _clip((window[-1].quote - window[-4].quote) / pip / Decimal(3), lower, upper)
    mean_absolute = _clip(
        sum((abs(value) for value in movements), start=Decimal("0")) / Decimal(5),
        Decimal("0"),
        upper,
    )
    sma = sum((tick.quote for tick in window[-5:]), start=Decimal("0")) / Decimal(5)
    distance_sma = _clip((window[-1].quote - sma) / pip, lower, upper)
    directions = tuple(
        Decimal(1) if value > 0 else Decimal(-1) if value < 0 else Decimal(0) for value in movements
    )
    direction_balance = sum(directions, start=Decimal("0")) / Decimal(5)
    latest_direction = directions[-1]
    streak = 0
    if latest_direction:
        for direction in reversed(directions):
            if direction != latest_direction:
                break
            streak += 1
    signed_streak = latest_direction * Decimal(streak) / Decimal(5)
    return (
        delta_one,
        delta_three,
        mean_absolute,
        distance_sma,
        direction_balance,
        signed_streak,
    )
