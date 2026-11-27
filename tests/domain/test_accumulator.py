"""Synthetic verification of ACCU streak reconstruction semantics (S4.1)."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.accumulator import (
    AccumulatorContract,
    InvalidAccumulator,
    Streak,
    in_zone,
    reconstruct_streaks,
    split_continuous_segments,
)
from devsoul_quant.domain.replay import Tick

_BARRIER = Decimal("0.0005")  # 0.05%


def _tick(epoch: int, quote: str) -> Tick:
    return Tick(epoch=epoch, quote=Decimal(quote), pip_size=2)


def _series(*quotes: str, start_epoch: int = 1000, cadence: int = 2) -> tuple[Tick, ...]:
    return tuple(_tick(start_epoch + i * cadence, q) for i, q in enumerate(quotes))


def test_in_zone_within_barrier() -> None:
    assert in_zone(Decimal("100"), Decimal("100.04"), _BARRIER) is True


def test_in_zone_exact_barrier_contact_is_within() -> None:
    assert in_zone(Decimal("100"), Decimal("100.05"), _BARRIER) is True


def test_in_zone_breach_up() -> None:
    assert in_zone(Decimal("100"), Decimal("100.06"), _BARRIER) is False


def test_in_zone_breach_down() -> None:
    assert in_zone(Decimal("100"), Decimal("99.94"), _BARRIER) is False


def test_in_zone_rejects_non_positive_quote() -> None:
    with pytest.raises(InvalidAccumulator):
        in_zone(Decimal("0"), Decimal("100"), _BARRIER)


def test_reconstruct_streaks_within_then_breach() -> None:
    # 100 -> 100.02 (in) -> 100.04 (in) -> 100.10 (breach: +0.06% > 0.05%)
    ticks = _series("100.00", "100.02", "100.04", "100.10")
    streaks = reconstruct_streaks(ticks, _BARRIER)
    assert [s.length for s in streaks] == [2, 0]
    assert streaks[0].broke is True
    assert streaks[1].broke is False  # trailing ongoing streak


def test_reconstruct_streaks_immediate_breach() -> None:
    ticks = _series("100.00", "100.06")
    streaks = reconstruct_streaks(ticks, _BARRIER)
    # one completed streak of 0 (immediate breach) plus the trailing ongoing 0
    assert [s.length for s in streaks] == [0, 0]
    assert streaks[0].broke is True


def test_reconstruct_streaks_all_in_zone_single_trailing_streak() -> None:
    ticks = _series("100.00", "100.01", "100.02", "100.03")
    streaks = reconstruct_streaks(ticks, _BARRIER)
    assert [s.length for s in streaks] == [3]
    assert streaks[0].broke is False


def test_reconstruct_streaks_exact_contact_counts_as_in() -> None:
    # exact 0.05% contact stays in
    ticks = _series("100.00", "100.05", "100.10")
    streaks = reconstruct_streaks(ticks, _BARRIER)
    assert [s.length for s in streaks] == [2]


def test_reconstruct_streaks_uncapped_by_maximum_ticks() -> None:
    # maximum_ticks is a contract auto-settle cap, not a streak-counting cap:
    # the natural streak statistic is uncapped and may exceed maximum_ticks.
    quotes = tuple(f"{100 + i * 0.01:.2f}" for i in range(60))
    ticks = _series(*quotes)
    streaks = reconstruct_streaks(ticks, _BARRIER)
    assert streaks[0].length == 59


def test_reconstruct_streaks_rejects_non_increasing_epochs() -> None:
    ticks = (_tick(1000, "100.00"), _tick(1000, "100.01"))
    with pytest.raises(InvalidAccumulator):
        reconstruct_streaks(ticks, _BARRIER)


def test_reconstruct_streaks_empty() -> None:
    assert reconstruct_streaks((), _BARRIER) == ()


def test_split_continuous_segments_splits_on_discontinuity() -> None:
    ticks = (
        _tick(1000, "100.00"),
        _tick(1002, "100.01"),
        _tick(1004, "100.02"),
        _tick(1010, "100.03"),  # gap of 6 > cadence 2
        _tick(1012, "100.04"),
    )
    segments = split_continuous_segments(ticks, cadence_seconds=2)
    assert [len(segment) for segment in segments] == [3, 2]


def test_split_continuous_segments_single_segment() -> None:
    ticks = _series("100.00", "100.01", "100.02")
    segments = split_continuous_segments(ticks, cadence_seconds=2)
    assert len(segments) == 1
    assert len(segments[0]) == 3


def test_accumulator_contract_validation() -> None:
    with pytest.raises(InvalidAccumulator):
        AccumulatorContract(
            symbol="",
            growth_rate=Decimal("0.05"),
            barrier_fraction=Decimal("0.0005"),
            maximum_ticks=50,
            stake=Decimal("1"),
        )
    with pytest.raises(InvalidAccumulator):
        AccumulatorContract(
            symbol="R_100",
            growth_rate=Decimal("0.05"),
            barrier_fraction=Decimal("0.0005"),
            maximum_ticks=0,
            stake=Decimal("1"),
        )
    with pytest.raises(InvalidAccumulator):
        AccumulatorContract(
            symbol="R_100",
            growth_rate=Decimal("1.5"),
            barrier_fraction=Decimal("0.0005"),
            maximum_ticks=50,
            stake=Decimal("1"),
        )


def test_accumulator_contract_rejects_growth_rate_ge_one() -> None:
    with pytest.raises(InvalidAccumulator):
        AccumulatorContract(
            symbol="R_100",
            growth_rate=Decimal("1.0"),
            barrier_fraction=Decimal("0.0005"),
            maximum_ticks=50,
            stake=Decimal("1"),
        )


def test_accumulator_contract_rejects_barrier_ge_one() -> None:
    with pytest.raises(InvalidAccumulator):
        AccumulatorContract(
            symbol="R_100",
            growth_rate=Decimal("0.05"),
            barrier_fraction=Decimal("1.0"),
            maximum_ticks=50,
            stake=Decimal("1"),
        )


def test_accumulator_contract_rejects_non_decimal_fields() -> None:
    with pytest.raises(InvalidAccumulator):
        AccumulatorContract(
            symbol="R_100",
            growth_rate="0.05",  # type: ignore[arg-type]
            barrier_fraction=Decimal("0.0005"),
            maximum_ticks=50,
            stake=Decimal("1"),
        )


def test_accumulator_contract_rejects_non_integer_maximum_ticks() -> None:
    with pytest.raises(InvalidAccumulator):
        AccumulatorContract(
            symbol="R_100",
            growth_rate=Decimal("0.05"),
            barrier_fraction=Decimal("0.0005"),
            maximum_ticks=50.0,  # type: ignore[arg-type]
            stake=Decimal("1"),
        )


def test_in_zone_rejects_non_decimal_quote() -> None:
    with pytest.raises(InvalidAccumulator):
        in_zone("100", Decimal("100.04"), _BARRIER)  # type: ignore[arg-type]


def test_in_zone_rejects_non_positive_barrier() -> None:
    with pytest.raises(InvalidAccumulator):
        in_zone(Decimal("100"), Decimal("100.04"), Decimal("0"))


def test_reconstruct_streaks_rejects_non_sequence() -> None:
    with pytest.raises(InvalidAccumulator):
        reconstruct_streaks(5, _BARRIER)  # type: ignore[arg-type]


def test_split_continuous_segments_rejects_non_sequence() -> None:
    with pytest.raises(InvalidAccumulator):
        split_continuous_segments(5, cadence_seconds=2)  # type: ignore[arg-type]


def test_streak_rejects_invalid_length() -> None:
    with pytest.raises(InvalidAccumulator):
        Streak(length=-1, broke=True, entry_epoch=1, exit_epoch=1)
