"""Tests for deterministic range and mean-reversion measures."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.range_regime import (
    InvalidRangeRegime,
    RangePolicy,
    ReferenceMode,
    amplitude,
    analyze_range,
    autocorrelation,
    crossing_count,
    deceleration,
    displacement,
    local_extrema,
    momentum,
    moving_average,
    reference_price,
    returns,
    volatility,
    z_score,
)


def _q(*values: object) -> tuple[Decimal, ...]:
    return tuple(Decimal(str(value)) for value in values)


def test_returns_are_per_tick_simple_returns() -> None:
    result = returns(_q(100, 101, 99))
    quantum = Decimal("1.00000000000000000000")
    assert result[0] == Decimal("0.01")
    assert result[1].quantize(quantum) == ((Decimal(99) - Decimal(101)) / Decimal(101)).quantize(
        quantum
    )


def test_moving_average_of_last_window() -> None:
    assert moving_average(_q(100, 102, 104), 2) == Decimal("103")


def test_reference_price_modes() -> None:
    quotes = _q(100, 102, 104)
    assert reference_price(
        quotes, RangePolicy(window=2, reference_mode=ReferenceMode.DISPLACEMENT)
    ) == Decimal("100")
    assert reference_price(
        quotes,
        RangePolicy(window=2, reference_mode=ReferenceMode.PRICE, fixed_reference=Decimal("98")),
    ) == Decimal("98")
    assert reference_price(
        quotes, RangePolicy(window=2, reference_mode=ReferenceMode.MOVING_AVERAGE)
    ) == Decimal("103")


def test_displacement_is_normalized() -> None:
    assert displacement(Decimal("105"), Decimal("100")) == Decimal("0.05")


def test_volatility_is_population_std() -> None:
    assert volatility(_q(100, 100, 102), 2) == Decimal("0.01")


def test_z_score_measures_units_of_volatility() -> None:
    assert z_score(Decimal("0.05"), Decimal("0.01")) == Decimal(5)


def test_local_extrema_of_last_window() -> None:
    assert local_extrema(_q(100, 105, 90, 95), 3) == (Decimal("90"), Decimal("105"))


def test_amplitude_is_normalized() -> None:
    assert amplitude(Decimal("90"), Decimal("105"), Decimal("100")) == Decimal("0.15")


def test_momentum_is_mean_recent_return() -> None:
    assert momentum(_q(100, 100, 102), 2) == Decimal("0.01")


def test_deceleration_positive_when_slowing() -> None:
    assert deceleration(_q(100, 100, 102, 102), 2) == Decimal("0.02")


def test_autocorrelation_of_persistent_returns() -> None:
    assert autocorrelation(
        (Decimal("0.01"), Decimal("0.01"), Decimal("0.02"), Decimal("0.02"))
    ) == Decimal("0.25")


def test_crossing_count_counts_reference_crossings() -> None:
    assert crossing_count(_q(100, 101, 99, 101), Decimal("100")) == 2


def test_analyze_range_builds_a_complete_profile() -> None:
    profile = analyze_range(
        _q(100, 100, 102), RangePolicy(window=2, reference_mode=ReferenceMode.DISPLACEMENT)
    )
    assert profile.reference == Decimal("100")
    assert profile.displacement == Decimal("0.02")
    assert profile.z_score == Decimal(2)
    assert profile.window_min == Decimal("100")
    assert profile.window_max == Decimal("102")
    assert profile.amplitude == Decimal("0.02")
    assert profile.moving_average == Decimal("101")
    assert profile.volatility == Decimal("0.01")
    assert profile.momentum == Decimal("0.01")
    assert profile.crossing_count == 0
    assert profile.return_frequency == Decimal(0)
    assert profile.mean_return_ticks is None


@pytest.mark.parametrize("window", [0, 1])
def test_window_must_be_at_least_two(window: int) -> None:
    with pytest.raises(InvalidRangeRegime, match="window"):
        RangePolicy(window=window, reference_mode=ReferenceMode.DISPLACEMENT)


def test_price_mode_requires_fixed_reference() -> None:
    with pytest.raises(InvalidRangeRegime, match="fixed_reference"):
        RangePolicy(window=2, reference_mode=ReferenceMode.PRICE)


def test_non_positive_quotes_are_rejected() -> None:
    with pytest.raises(InvalidRangeRegime):
        returns(_q(100, 0))


def test_z_score_rejects_non_positive_volatility() -> None:
    with pytest.raises(InvalidRangeRegime, match="volatility"):
        z_score(Decimal("0.1"), Decimal("0"))


def test_analyze_range_rejects_flat_window() -> None:
    with pytest.raises(InvalidRangeRegime):
        analyze_range(
            _q(100, 100, 100), RangePolicy(window=2, reference_mode=ReferenceMode.DISPLACEMENT)
        )


def test_reference_mode_must_be_an_enum() -> None:
    with pytest.raises(InvalidRangeRegime, match="reference_mode"):
        RangePolicy(window=2, reference_mode="DISPLACEMENT")  # type: ignore[arg-type]


def test_fixed_reference_must_be_positive() -> None:
    with pytest.raises(InvalidRangeRegime, match="fixed_reference"):
        RangePolicy(
            window=2, reference_mode=ReferenceMode.DISPLACEMENT, fixed_reference=Decimal("-5")
        )


def test_returns_rejects_too_few_quotes() -> None:
    with pytest.raises(InvalidRangeRegime, match="quotes"):
        returns(_q(100))


def test_displacement_rejects_non_positive_quote() -> None:
    with pytest.raises(InvalidRangeRegime, match="quote"):
        displacement(Decimal("0"), Decimal("100"))


def test_displacement_rejects_non_positive_reference() -> None:
    with pytest.raises(InvalidRangeRegime, match="reference"):
        displacement(Decimal("105"), Decimal("0"))


def test_deceleration_rejects_single_return_window() -> None:
    with pytest.raises(InvalidRangeRegime, match="return per half"):
        deceleration(_q(100, 101), 1)


def test_autocorrelation_rejects_short_sequence() -> None:
    with pytest.raises(InvalidRangeRegime, match="two values"):
        autocorrelation((Decimal("0.01"),))


def test_autocorrelation_rejects_constant_sequence() -> None:
    with pytest.raises(InvalidRangeRegime, match="constant"):
        autocorrelation((Decimal("1"), Decimal("1"), Decimal("1")))


def test_analyze_range_reports_mean_return_ticks_when_crossing() -> None:
    profile = analyze_range(
        _q(100, 101, 99), RangePolicy(window=2, reference_mode=ReferenceMode.DISPLACEMENT)
    )
    assert profile.crossing_count == 1
    assert profile.return_frequency == Decimal("0.5")
    assert profile.mean_return_ticks == Decimal(2)
