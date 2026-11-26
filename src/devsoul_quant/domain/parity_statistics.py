"""Exact, deterministic parity statistics for Even/Odd hypothesis research.

Every quantity is computed with ``Decimal`` at 50 digits of precision (never
floating point), so a given tick history always yields the same numbers. The
module separates tick-level extraction (which needs ``pip_size``) from pure
sequence-level statistics over a binary parity sequence (0 = even, 1 = odd).

These statistics are descriptive and testing primitives only. They do not
recommend trades; interpretation into EVEN / ODD / HOLD belongs to the decision
engine.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from itertools import pairwise

from devsoul_quant.domain.digit_strategy import last_digit
from devsoul_quant.domain.replay import Tick

_DECIMAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)


class InvalidParityStatistics(ValueError):
    """Raised for empty, short, or degenerate parity samples."""


@dataclass(frozen=True, slots=True)
class ParityTransitions:
    """Adjacent-pair transition counts over a binary parity sequence."""

    even_to_even: int
    even_to_odd: int
    odd_to_even: int
    odd_to_odd: int

    def __post_init__(self) -> None:
        for field in (
            "even_to_even",
            "even_to_odd",
            "odd_to_even",
            "odd_to_odd",
        ):
            value = getattr(self, field)
            if type(value) is not int or value < 0:
                raise InvalidParityStatistics(f"{field} must be a non-negative integer")

    @property
    def total(self) -> int:
        """Return the total number of observed adjacent-pair transitions."""
        return self.even_to_even + self.even_to_odd + self.odd_to_even + self.odd_to_odd


def _require_binary(sequence: Sequence[int], *, minimum_length: int) -> tuple[int, ...]:
    if len(sequence) < minimum_length:
        raise InvalidParityStatistics(f"parity sequence requires at least {minimum_length} values")
    normalized = tuple(sequence)
    if any(type(value) is not int or value not in (0, 1) for value in normalized):
        raise InvalidParityStatistics("parity sequence values must be 0 or 1")
    return normalized


def parity_sequence(history: Sequence[Tick]) -> tuple[int, ...]:
    """Return the binary parity sequence (0 = even, 1 = odd) from a tick history."""
    if not history:
        raise InvalidParityStatistics("history must not be empty")
    return tuple(last_digit(tick) % 2 for tick in history)


def digit_frequencies(history: Sequence[Tick]) -> tuple[int, ...]:
    """Return per-digit counts 0..9 from a tick history."""
    if not history:
        raise InvalidParityStatistics("history must not be empty")
    counts = [0] * 10
    for tick in history:
        counts[last_digit(tick)] += 1
    return tuple(counts)


def parity_counts(history: Sequence[Tick]) -> tuple[int, int]:
    """Return (even, odd) tick counts from a tick history."""
    sequence = parity_sequence(history)
    return (sequence.count(0), sequence.count(1))


def run_lengths(sequence: Sequence[int]) -> tuple[int, ...]:
    """Return the lengths of consecutive same-parity runs."""
    normalized = _require_binary(sequence, minimum_length=1)
    runs: list[int] = []
    current = 1
    for previous, current_value in pairwise(normalized):
        if previous == current_value:
            current += 1
        else:
            runs.append(current)
            current = 1
    runs.append(current)
    return tuple(runs)


def transition_counts(sequence: Sequence[int]) -> ParityTransitions:
    """Count the four adjacent-parity transitions."""
    normalized = _require_binary(sequence, minimum_length=2)
    even_to_even = even_to_odd = odd_to_even = odd_to_odd = 0
    for previous, current in pairwise(normalized):
        if previous == 0:
            if current == 0:
                even_to_even += 1
            else:
                even_to_odd += 1
        elif current == 0:
            odd_to_even += 1
        else:
            odd_to_odd += 1
    return ParityTransitions(even_to_even, even_to_odd, odd_to_even, odd_to_odd)


def stay_rate(transitions: ParityTransitions) -> Decimal:
    """Return the fraction of adjacent pairs that kept the same parity."""
    if transitions.total == 0:
        raise InvalidParityStatistics("stay rate requires at least one transition")
    with localcontext(_DECIMAL_CONTEXT):
        return Decimal(transitions.even_to_even + transitions.odd_to_odd) / Decimal(
            transitions.total
        )


def switch_rate(transitions: ParityTransitions) -> Decimal:
    """Return the fraction of adjacent pairs that switched parity."""
    return Decimal(1) - stay_rate(transitions)


def shannon_entropy_bits(counts: Sequence[int]) -> Decimal:
    """Return the Shannon entropy (bits) of a categorical count vector."""
    normalized = tuple(counts)
    if not normalized or any(type(value) is not int or value < 0 for value in normalized):
        raise InvalidParityStatistics("counts must be non-negative integers")
    total = sum(normalized)
    if total == 0:
        raise InvalidParityStatistics("entropy requires at least one observation")
    with localcontext(_DECIMAL_CONTEXT):
        ln2 = Decimal(2).ln()
        entropy = Decimal(0)
        for value in normalized:
            if value == 0:
                continue
            probability = Decimal(value) / Decimal(total)
            entropy -= probability * (probability.ln() / ln2)
        return entropy


def chi_square_uniform(counts: Sequence[int]) -> Decimal:
    """Return the chi-square goodness-of-fit statistic against a uniform model."""
    normalized = tuple(counts)
    if not normalized or any(type(value) is not int or value < 0 for value in normalized):
        raise InvalidParityStatistics("counts must be non-negative integers")
    total = sum(normalized)
    if total == 0:
        raise InvalidParityStatistics("chi-square requires at least one observation")
    with localcontext(_DECIMAL_CONTEXT):
        expected = Decimal(total) / Decimal(len(normalized))
        return sum(
            ((Decimal(value) - expected) ** 2 / expected for value in normalized),
            Decimal(0),
        )


def chi_square_transition(transitions: ParityTransitions) -> Decimal:
    """Return the chi-square independence statistic for the 2x2 transition table."""
    if transitions.total == 0:
        raise InvalidParityStatistics("transition chi-square requires at least one transition")
    row_even = transitions.even_to_even + transitions.even_to_odd
    row_odd = transitions.odd_to_even + transitions.odd_to_odd
    column_even = transitions.even_to_even + transitions.odd_to_even
    column_odd = transitions.even_to_odd + transitions.odd_to_odd
    cells = (
        (transitions.even_to_even, row_even, column_even),
        (transitions.even_to_odd, row_even, column_odd),
        (transitions.odd_to_even, row_odd, column_even),
        (transitions.odd_to_odd, row_odd, column_odd),
    )
    with localcontext(_DECIMAL_CONTEXT):
        total = Decimal(transitions.total)
        return sum(
            (
                (Decimal(observed) - Decimal(row) * Decimal(column) / total) ** 2
                / (Decimal(row) * Decimal(column) / total)
                for observed, row, column in cells
                if row != 0 and column != 0
            ),
            Decimal(0),
        )


def runs_count(sequence: Sequence[int]) -> int:
    """Return the number of same-parity runs in a binary sequence."""
    normalized = _require_binary(sequence, minimum_length=1)
    count = 1
    for previous, current in pairwise(normalized):
        if previous != current:
            count += 1
    return count


def runs_test_z(sequence: Sequence[int]) -> Decimal:
    """Return the Wald-Wolfowitz runs test z-statistic for randomness."""
    normalized = _require_binary(sequence, minimum_length=3)
    ones = sum(normalized)
    zeros = len(normalized) - ones
    if ones == 0 or zeros == 0:
        raise InvalidParityStatistics("runs test requires both parities")
    count = runs_count(normalized)
    with localcontext(_DECIMAL_CONTEXT):
        n = Decimal(len(normalized))
        n0 = Decimal(zeros)
        n1 = Decimal(ones)
        expected = Decimal(1) + Decimal(2) * n0 * n1 / n
        variance = Decimal(2) * n0 * n1 * (Decimal(2) * n0 * n1 - n) / (n * n * (n - Decimal(1)))
        if variance <= 0:
            raise InvalidParityStatistics("runs test variance is not positive")
        return (Decimal(count) - expected) / variance.sqrt()


def lag_one_autocorrelation(sequence: Sequence[int]) -> Decimal:
    """Return the exact lag-1 autocorrelation of a binary sequence."""
    normalized = _require_binary(sequence, minimum_length=2)
    with localcontext(_DECIMAL_CONTEXT):
        mean = Decimal(sum(normalized)) / Decimal(len(normalized))
        numerator = sum(
            (Decimal(left) - mean) * (Decimal(right) - mean) for left, right in pairwise(normalized)
        )
        denominator = sum((Decimal(value) - mean) ** 2 for value in normalized)
        if denominator == 0:
            raise InvalidParityStatistics("autocorrelation is undefined for a constant sequence")
        return numerator / denominator
