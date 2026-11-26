"""Categorical first-order Markov estimation with Dirichlet smoothing (S3.10/B4).

The H2 (Jump digit) protocol proposes a 10x10 transition matrix estimated from a
120-observation warm-up. A naive maximum-likelihood estimate assigns zero mass
to any transition that never appeared, producing an infinite log-loss the first
time it occurs out of sample. This module provides a parsimonious
Dirichlet/Laplace-smoothed estimator whose posterior mean never assigns zero
probability, together with marginal frequencies that serve as a shrinkage
reference. It is incremental (O(1) per symbol, O(K) per prediction) and
deterministic, and is used only to evaluate the estimation risk on synthetic
data before any market observation.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal


class InvalidMarkovConfig(ValueError):
    """Raised when the alphabet size or smoothing parameter is invalid."""


class CategoricalTransitionEstimator:
    """Incremental first-order Markov estimator with Dirichlet(alpha) smoothing."""

    def __init__(self, *, alphabet_size: int, alpha: Decimal = Decimal("1")) -> None:
        if type(alphabet_size) is not int or alphabet_size < 2:
            raise InvalidMarkovConfig("alphabet_size must be an integer >= 2")
        if not isinstance(alpha, Decimal) or not alpha.is_finite() or alpha < 0:
            raise InvalidMarkovConfig("alpha must be a finite non-negative Decimal")
        self._alphabet_size = alphabet_size
        self._alpha = alpha
        self._marginal = [0] * alphabet_size
        self._transitions = [[0] * alphabet_size for _ in range(alphabet_size)]
        self._total = 0
        self._previous: int | None = None

    @property
    def alphabet_size(self) -> int:
        return self._alphabet_size

    @property
    def alpha(self) -> Decimal:
        return self._alpha

    def _check_symbol(self, symbol: int) -> None:
        if type(symbol) is not int or not 0 <= symbol < self._alphabet_size:
            raise InvalidMarkovConfig(f"symbol must be an integer in [0, {self._alphabet_size})")

    def observe(self, symbol: int) -> None:
        self._check_symbol(symbol)
        self._marginal[symbol] += 1
        self._total += 1
        if self._previous is not None:
            self._transitions[self._previous][symbol] += 1
        self._previous = symbol

    def marginal_probabilities(self) -> tuple[Decimal, ...]:
        if self._total == 0 and self._alpha == 0:
            raise InvalidMarkovConfig("cannot estimate a marginal from no data with alpha=0")
        denominator = Decimal(self._total) + self._alpha * self._alphabet_size
        return tuple((Decimal(count) + self._alpha) / denominator for count in self._marginal)

    def transition_probabilities(self, previous: int) -> tuple[Decimal, ...]:
        self._check_symbol(previous)
        row = self._transitions[previous]
        row_total = sum(row)
        if row_total == 0 and self._alpha == 0:
            raise InvalidMarkovConfig(
                "cannot estimate transitions from an unseen previous symbol with alpha=0"
            )
        denominator = Decimal(row_total) + self._alpha * self._alphabet_size
        return tuple((Decimal(count) + self._alpha) / denominator for count in row)

    def clear(self) -> None:
        self._marginal = [0] * self._alphabet_size
        self._transitions = [[0] * self._alphabet_size for _ in range(self._alphabet_size)]
        self._total = 0
        self._previous = None


def mean_log_loss(
    probabilities_by_step: Sequence[Sequence[Decimal]], symbols: Sequence[int]
) -> Decimal:
    """Mean negative log-probability; a zero probability yields an infinite loss."""
    if len(probabilities_by_step) != len(symbols):
        raise InvalidMarkovConfig("probabilities and symbols must have the same length")
    total = Decimal("0")
    for distribution, symbol in zip(probabilities_by_step, symbols, strict=True):
        probability = distribution[symbol]
        if probability <= 0:
            return Decimal("Infinity")
        total -= probability.ln()
    return total / Decimal(len(symbols))
