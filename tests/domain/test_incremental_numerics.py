"""S3.10/E synthetic numerical validation of the incremental models.

These tests verify engine behaviour (stability, calibration, convergence, no
leakage, signal detection) on synthetic data. They are NOT evidence of alpha in
Deriv; they characterise the deterministic learners used by the S3.8 shadow
evaluator. No statistical behaviour is changed here.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

import pytest

from devsoul_quant.domain.adaptive_intelligence import (
    IncrementalGaussianNaiveBayes,
    IncrementalLogisticRegression,
    InvalidAdaptiveInput,
)


class _IncrementalModel(Protocol):
    def learn(self, features: Sequence[Decimal], label: object) -> None: ...

    def predict_probability(self, features: Sequence[Decimal]) -> Decimal: ...


def _features(*values: object) -> tuple[Decimal, ...]:
    return tuple(Decimal(str(value)) for value in values)


def _train_linear(model: _IncrementalModel, *, samples: int = 2000) -> None:
    """Teach the model a single-feature linear boundary: label = x > 0."""
    for index in range(samples):
        x = Decimal(index % 41 - 20) / Decimal(10)  # [-2.0, 2.0]
        label = 1 if x > 0 else 0
        model.learn(_features(x), label)


def test_iid_no_signal_stays_finite_and_bounded() -> None:
    model = IncrementalLogisticRegression(feature_count=1)
    for index in range(500):
        x = Decimal("1") if index % 2 else Decimal("-1")
        model.learn(_features(x), index % 2)
    for value in (Decimal("-2"), Decimal("0"), Decimal("2")):
        p = model.predict_probability(_features(value))
        assert p.is_finite()
        assert Decimal("0") <= p <= Decimal("1")


def test_linear_signal_is_learned_by_logistic() -> None:
    model = IncrementalLogisticRegression(feature_count=1)
    _train_linear(model)
    assert model.predict_probability(_features(2)) > Decimal("0.5")
    assert model.predict_probability(_features(-2)) < Decimal("0.5")


def test_linear_signal_is_learned_by_gaussian_nb() -> None:
    model = IncrementalGaussianNaiveBayes(feature_count=1)
    _train_linear(model)
    assert model.predict_probability(_features(2)) > Decimal("0.5")
    assert model.predict_probability(_features(-2)) < Decimal("0.5")


def test_constant_features_do_not_crash_nb() -> None:
    model = IncrementalGaussianNaiveBayes(feature_count=2)
    for index in range(100):
        model.learn(_features(3, 3), index % 2)
    p = model.predict_probability(_features(3, 3))
    assert p.is_finite()
    assert Decimal("0") <= p <= Decimal("1")


def test_features_of_different_magnitudes_stay_finite() -> None:
    model = IncrementalLogisticRegression(feature_count=2)
    for index in range(300):
        model.learn(_features(index % 2, (index % 2) * 1000), index % 2)
    p = model.predict_probability(_features(1, 1000))
    assert p.is_finite()


def test_unbalanced_classes_produce_finite_probabilities() -> None:
    model = IncrementalGaussianNaiveBayes(feature_count=1)
    for index in range(300):
        x = Decimal("1") if index < 270 else Decimal("-1")
        model.learn(_features(x), 1 if index < 270 else 0)
    p = model.predict_probability(_features(1))
    assert p.is_finite()
    assert p > Decimal("0.5")  # the majority class dominates the prior


def test_regime_change_moves_probabilities() -> None:
    model = IncrementalLogisticRegression(feature_count=1)
    for _ in range(300):
        model.learn(_features(1), 1)
    first = model.predict_probability(_features(1))
    for _ in range(300):
        model.learn(_features(1), 0)
    second = model.predict_probability(_features(1))
    assert first.is_finite() and second.is_finite()
    assert second < first  # the model adapts to the new regime


def test_probability_saturation_never_produces_nan() -> None:
    model = IncrementalLogisticRegression(feature_count=1)
    for _ in range(1000):
        model.learn(_features(1000), 1)
        model.learn(_features(-1000), 0)
    high = model.predict_probability(_features(1000))
    low = model.predict_probability(_features(-1000))
    assert high.is_finite() and low.is_finite()
    assert high > Decimal("0.999")
    assert low < Decimal("0.001")


def test_extreme_feature_values_are_clipped_and_finite() -> None:
    model = IncrementalLogisticRegression(feature_count=1)
    for index in range(100):
        value = Decimal(10) ** (index % 30)  # up to 1e29
        model.learn(_features(value), 1)
    p = model.predict_probability(_features(Decimal(10) ** 29))
    assert p.is_finite()


def test_near_zero_variance_uses_the_floor() -> None:
    model = IncrementalGaussianNaiveBayes(feature_count=1)
    for _index in range(5):
        model.learn(_features(2), 0)
    p = model.predict_probability(_features(2))
    assert p.is_finite()


def test_models_reject_invalid_feature_and_label_shapes() -> None:
    model = IncrementalLogisticRegression(feature_count=2)
    with pytest.raises(InvalidAdaptiveInput):
        model.learn(_features(1), 0)
    with pytest.raises(InvalidAdaptiveInput):
        model.learn(_features(1, 2), 2)
    with pytest.raises(InvalidAdaptiveInput):
        model.learn((Decimal("1"), Decimal("nan")), 0)
