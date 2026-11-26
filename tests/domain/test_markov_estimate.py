"""S3.10/B4 synthetic evaluation of the 10x10 Markov estimation risk (H2).

These tests quantify the under-estimation risk of a naive 10x10 transition
matrix on a 120-observation warm-up and demonstrate that Dirichlet smoothing
(alpha=1) is the parsimonious alternative that avoids zero probabilities.
H2 remains DEFERRED; these tests characterise the estimator, not Deriv.
"""

from decimal import Decimal

import pytest

from devsoul_quant.domain.markov_estimate import (
    CategoricalTransitionEstimator,
    InvalidMarkovConfig,
    mean_log_loss,
)


def _warmup_sequence(count: int = 120) -> list[int]:
    """A 10-symbol sequence where 0->9 never occurs within the warm-up."""
    sequence: list[int] = []
    previous = 0
    for index in range(count):
        current = (previous + (index % 3)) % 9  # never transitions into 9
        sequence.append(current)
        previous = current
    return sequence


def test_mle_assigns_zero_probability_to_unseen_transition() -> None:
    estimator = CategoricalTransitionEstimator(alphabet_size=10, alpha=Decimal("0"))
    for symbol in _warmup_sequence():
        estimator.observe(symbol)

    probabilities = estimator.transition_probabilities(0)
    assert probabilities[9] == Decimal("0")  # the estimation gap


def test_dirichlet_smoothing_never_assigns_zero_probability() -> None:
    estimator = CategoricalTransitionEstimator(alphabet_size=10, alpha=Decimal("1"))
    for symbol in _warmup_sequence():
        estimator.observe(symbol)

    probabilities = estimator.transition_probabilities(0)
    assert all(probability > 0 for probability in probabilities)
    assert probabilities[9] > Decimal("0")


def test_smoothed_log_loss_is_finite_where_mle_diverges() -> None:
    mle = CategoricalTransitionEstimator(alphabet_size=10, alpha=Decimal("0"))
    smoothed = CategoricalTransitionEstimator(alphabet_size=10, alpha=Decimal("1"))
    sequence = _warmup_sequence()
    for symbol in sequence:
        mle.observe(symbol)
        smoothed.observe(symbol)

    # Out-of-sample: the next symbol is 9 (never seen after 0 in the warm-up).
    next_symbols = [9]
    mle_probs = [mle.transition_probabilities(sequence[-1])]
    smoothed_probs = [smoothed.transition_probabilities(sequence[-1])]

    assert mean_log_loss(mle_probs, next_symbols) == Decimal("Infinity")
    assert mean_log_loss(smoothed_probs, next_symbols).is_finite()


def test_marginal_frequencies_are_a_valid_shrinkage_reference() -> None:
    estimator = CategoricalTransitionEstimator(alphabet_size=10, alpha=Decimal("1"))
    for symbol in _warmup_sequence():
        estimator.observe(symbol)

    marginal = estimator.marginal_probabilities()
    assert sum(marginal) == Decimal("1")
    assert all(probability > 0 for probability in marginal)


def test_larger_warmup_narrows_the_estimation_gap() -> None:
    def unseen_probability(count: int) -> Decimal:
        estimator = CategoricalTransitionEstimator(alphabet_size=10, alpha=Decimal("1"))
        for symbol in _warmup_sequence(count):
            estimator.observe(symbol)
        return estimator.transition_probabilities(0)[9]

    # With more data the smoothed estimate of the unseen cell stays positive
    # and approaches the true (zero) value, but never reaches zero.
    assert unseen_probability(120) > unseen_probability(1200)


def test_estimator_is_incremental_and_deterministic() -> None:
    first = CategoricalTransitionEstimator(alphabet_size=10, alpha=Decimal("1"))
    second = CategoricalTransitionEstimator(alphabet_size=10, alpha=Decimal("1"))
    for symbol in _warmup_sequence():
        first.observe(symbol)
    for symbol in _warmup_sequence():
        second.observe(symbol)
    assert first.marginal_probabilities() == second.marginal_probabilities()
    assert first.transition_probabilities(0) == second.transition_probabilities(0)


def test_estimator_rejects_invalid_configuration() -> None:
    with pytest.raises(InvalidMarkovConfig):
        CategoricalTransitionEstimator(alphabet_size=1)
    with pytest.raises(InvalidMarkovConfig):
        CategoricalTransitionEstimator(alphabet_size=10, alpha=Decimal("-1"))
    estimator = CategoricalTransitionEstimator(alphabet_size=10)
    with pytest.raises(InvalidMarkovConfig):
        estimator.observe(10)
