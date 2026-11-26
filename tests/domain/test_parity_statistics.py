"""Tests for exact, deterministic Even/Odd parity statistics."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.parity_statistics import (
    InvalidParityStatistics,
    ParityTransitions,
    chi_square_transition,
    chi_square_uniform,
    digit_frequencies,
    lag_one_autocorrelation,
    parity_counts,
    parity_sequence,
    run_lengths,
    runs_count,
    runs_test_z,
    shannon_entropy_bits,
    stay_rate,
    switch_rate,
    transition_counts,
)
from devsoul_quant.domain.replay import Tick


def _ticks(digits: list[int]) -> tuple[Tick, ...]:
    return tuple(
        Tick(
            epoch=1_700_000_000 + index,
            quote=Decimal("100.0000") + Decimal(digit) / Decimal("10000"),
            pip_size=4,
        )
        for index, digit in enumerate(digits)
    )


def test_parity_sequence_maps_digits_to_binary() -> None:
    assert parity_sequence(_ticks([4, 5, 0, 3, 8])) == (0, 1, 0, 1, 0)


def test_digit_frequencies_counts_each_digit() -> None:
    assert digit_frequencies(_ticks([0, 0, 5, 5, 5, 9])) == (2, 0, 0, 0, 0, 3, 0, 0, 0, 1)


def test_parity_counts_splits_even_and_odd() -> None:
    assert parity_counts(_ticks([0, 2, 1, 3])) == (2, 2)


def test_run_lengths_lists_consecutive_runs() -> None:
    assert run_lengths((0, 0, 1, 1, 1, 0)) == (2, 3, 1)
    assert run_lengths((0, 1, 0, 1)) == (1, 1, 1, 1)


def test_transition_counts_counts_adjacent_pairs() -> None:
    assert transition_counts((0, 0, 1, 1, 0)) == ParityTransitions(1, 1, 1, 1)


def test_stay_and_switch_rate_are_complementary() -> None:
    transitions = ParityTransitions(1, 1, 1, 1)
    assert stay_rate(transitions) == Decimal("0.5")
    assert switch_rate(transitions) == Decimal("0.5")


def test_shannon_entropy_binary_uniform_is_one_bit() -> None:
    assert shannon_entropy_bits((1, 1)) == Decimal(1)
    assert shannon_entropy_bits((1, 0)) == Decimal(0)


def test_shannon_entropy_ten_digit_uniform_is_log2_ten() -> None:
    expected = (Decimal(10).ln() / Decimal(2).ln()).quantize(Decimal("1.0000"))
    result = shannon_entropy_bits((1,) * 10).quantize(Decimal("1.0000"))
    assert result == expected


def test_chi_square_uniform_is_zero_when_balanced() -> None:
    assert chi_square_uniform((1, 1)) == Decimal(0)


def test_chi_square_uniform_penalizes_imbalance() -> None:
    assert chi_square_uniform((2, 0)) == Decimal(2)


def test_chi_square_transition_is_zero_when_independent() -> None:
    assert chi_square_transition(ParityTransitions(1, 1, 1, 1)) == Decimal(0)


def test_chi_square_transition_penalizes_dependence() -> None:
    assert chi_square_transition(ParityTransitions(4, 0, 0, 4)) > Decimal(0)


def test_runs_count_counts_alternation_boundaries() -> None:
    assert runs_count((0, 0, 1, 1, 0)) == 3
    assert runs_count((0, 1, 0, 1, 0)) == 5


def test_runs_test_z_positive_for_excess_alternation() -> None:
    assert runs_test_z((0, 1, 0, 1, 0, 1)) > Decimal(0)


def test_runs_test_z_negative_for_persistence() -> None:
    assert runs_test_z((0, 0, 0, 1, 1, 1)) < Decimal(0)


def test_lag_one_autocorrelation_persistence_is_positive() -> None:
    assert lag_one_autocorrelation((0, 0, 1, 1)) == Decimal("0.25")


def test_lag_one_autocorrelation_alternation_is_negative() -> None:
    assert lag_one_autocorrelation((0, 1, 0, 1)) == Decimal("-0.75")


def test_empty_history_is_rejected() -> None:
    with pytest.raises(InvalidParityStatistics):
        parity_sequence(())


def test_transition_counts_requires_two_values() -> None:
    with pytest.raises(InvalidParityStatistics):
        transition_counts((0,))


def test_non_binary_values_are_rejected() -> None:
    with pytest.raises(InvalidParityStatistics):
        run_lengths((0, 2))


def test_runs_test_rejects_constant_sequence() -> None:
    with pytest.raises(InvalidParityStatistics):
        runs_test_z((0, 0, 0, 0))


def test_autocorrelation_rejects_constant_sequence() -> None:
    with pytest.raises(InvalidParityStatistics):
        lag_one_autocorrelation((1, 1, 1))


def test_transitions_validate_non_negative_counts() -> None:
    with pytest.raises(InvalidParityStatistics):
        ParityTransitions(-1, 0, 0, 0)


def test_stay_rate_rejects_empty_transitions() -> None:
    with pytest.raises(InvalidParityStatistics):
        stay_rate(ParityTransitions(0, 0, 0, 0))
