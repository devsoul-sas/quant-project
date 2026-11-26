"""Causal feature engineering for ephemeral adaptive intelligence."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.adaptive_intelligence import (
    IncrementalGaussianNaiveBayes,
    IncrementalLogisticRegression,
    InvalidAdaptiveInput,
    build_adaptive_features,
)
from devsoul_quant.domain.replay import Tick


def _ticks() -> tuple[Tick, ...]:
    return tuple(
        Tick(index, quote, pip_size=2)
        for index, quote in enumerate(
            (
                Decimal("100.00"),
                Decimal("100.01"),
                Decimal("100.03"),
                Decimal("100.02"),
                Decimal("100.04"),
                Decimal("100.05"),
                Decimal("999.99"),
            ),
            start=1,
        )
    )


def test_adaptive_features_use_only_ticks_available_at_decision_time() -> None:
    ticks = _ticks()

    at_decision = build_adaptive_features(ticks[:6], decision_epoch=6)
    with_future_hidden = build_adaptive_features(ticks, decision_epoch=6)

    assert at_decision == with_future_hidden
    assert at_decision == (
        Decimal("1"),
        Decimal("0.6666666666666666666666666667"),
        Decimal("1.4"),
        Decimal("2"),
        Decimal("0.6"),
        Decimal("0.4"),
    )


@pytest.mark.parametrize(
    "ticks",
    (
        tuple(Tick(index, Decimal(index), pip_size=None) for index in range(1, 7)),
        tuple(Tick(index, Decimal(index), pip_size=index % 2 + 1) for index in range(1, 7)),
        (
            Tick(1, Decimal("1"), pip_size=2),
            Tick(2, Decimal("2"), pip_size=2),
            Tick(3, Decimal("3"), pip_size=2),
            Tick(4, Decimal("4"), pip_size=2),
            Tick(5, Decimal("5"), pip_size=2),
            Tick(5, Decimal("6"), pip_size=2),
        ),
    ),
)
def test_adaptive_features_reject_ambiguous_market_inputs(ticks: tuple[Tick, ...]) -> None:
    with pytest.raises(InvalidAdaptiveInput):
        build_adaptive_features(ticks, decision_epoch=ticks[-1].epoch)


def test_incremental_logistic_learns_only_after_label_and_can_be_zeroized() -> None:
    model = IncrementalLogisticRegression(feature_count=2)
    features = (Decimal("1"), Decimal("-1"))

    prediction = model.predict_probability(features)
    assert prediction == Decimal("0.5")
    for _ in range(20):
        prediction = model.predict_probability(features)
        model.learn(features, 1)

    assert prediction > Decimal("0.5")
    assert model.predict_probability(features) > prediction

    model.clear()

    assert model.predict_probability(features) == Decimal("0.5")


def test_incremental_gaussian_naive_bayes_separates_classes_and_can_be_zeroized() -> None:
    model = IncrementalGaussianNaiveBayes(feature_count=1)
    for value in (Decimal("-2"), Decimal("-1"), Decimal("-0.5")):
        model.learn((value,), 0)
    for value in (Decimal("0.5"), Decimal("1"), Decimal("2")):
        model.learn((value,), 1)

    assert model.predict_probability((Decimal("1.5"),)) > Decimal("0.5")
    assert model.predict_probability((Decimal("-1.5"),)) < Decimal("0.5")

    model.clear()

    assert model.predict_probability((Decimal("1.5"),)) == Decimal("0.5")


def test_incremental_models_reject_invalid_dimensions_values_labels_and_sizes() -> None:
    with pytest.raises(InvalidAdaptiveInput):
        IncrementalLogisticRegression(feature_count=0)
    with pytest.raises(InvalidAdaptiveInput):
        IncrementalGaussianNaiveBayes(feature_count=0)

    logistic = IncrementalLogisticRegression(feature_count=1)
    with pytest.raises(InvalidAdaptiveInput):
        logistic.predict_probability(())
    with pytest.raises(InvalidAdaptiveInput):
        logistic.predict_probability((Decimal("NaN"),))
    with pytest.raises(InvalidAdaptiveInput):
        logistic.learn((Decimal("1"),), True)


def test_feature_builder_rejects_non_integer_missing_and_short_decision_boundaries() -> None:
    ticks = _ticks()
    with pytest.raises(InvalidAdaptiveInput):
        build_adaptive_features(ticks, decision_epoch=True)
    with pytest.raises(InvalidAdaptiveInput):
        build_adaptive_features(ticks, decision_epoch=999)
    with pytest.raises(InvalidAdaptiveInput):
        build_adaptive_features(ticks[:5], decision_epoch=5)
