"""Causal temporal feature tests."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.features import (
    FeatureSetSpec,
    InvalidFeatureInput,
    InvalidFeatureSpec,
    compute_features,
)
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.synthetic import generate_ticks

_HASH = "a" * 64


def _spec(**overrides: object) -> FeatureSetSpec:
    fields: dict[str, object] = {
        "name": "momentum-baseline",
        "version": "1",
        "lag_windows": (1, 3),
        "rolling_window": 3,
    }
    fields.update(overrides)
    return FeatureSetSpec(**fields)  # type: ignore[arg-type]


def _ticks() -> tuple[Tick, ...]:
    return generate_ticks(seed=42, count=8)


def test_spec_hash_is_deterministic_and_canonical() -> None:
    first = _spec().spec_hash()
    second = _spec().spec_hash()
    changed = _spec(version="2").spec_hash()

    assert first == second
    assert len(first) == 64
    assert changed != first


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "   "},
        {"version": ""},
        {"lag_windows": ()},
        {"lag_windows": (0, 3)},
        {"lag_windows": (1, 1)},
        {"rolling_window": 1},
        {"return_places": 0},
        {"mean_places": 0},
    ],
)
def test_spec_rejects_invalid_fields(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidFeatureSpec):
        _spec(**overrides)


def test_features_use_only_past_and_present_rows() -> None:
    spec = _spec()
    ticks = _ticks()

    full = compute_features(spec=spec, ticks=ticks, dataset_hash=_HASH)
    truncated = compute_features(spec=spec, ticks=ticks[:5], dataset_hash=_HASH)

    assert truncated.rows == full.rows[:5]


def test_modifying_a_later_tick_does_not_change_earlier_features() -> None:
    spec = _spec()
    ticks = _ticks()

    frame_a = compute_features(spec=spec, ticks=ticks, dataset_hash=_HASH)
    mutated = (*ticks[:-1], Tick(epoch=ticks[-1].epoch, quote=ticks[-1].quote + Decimal("1.0000")))
    frame_b = compute_features(spec=spec, ticks=mutated, dataset_hash=_HASH)

    assert frame_a.rows[:-1] == frame_b.rows[:-1]
    assert frame_a.rows[-1] != frame_b.rows[-1]


def test_warmup_rows_preserve_unavailable_instead_of_imputing() -> None:
    spec = _spec()
    ticks = _ticks()

    frame = compute_features(spec=spec, ticks=ticks, dataset_hash=_HASH)

    first = frame.rows[0]
    assert first.lag_returns == (None, None)
    assert first.rolling_mean is None
    assert first.rolling_abs_move is None
    assert first.warmup is True

    third = frame.rows[3]
    assert all(value is not None for value in third.lag_returns)
    assert third.rolling_mean is not None
    assert third.rolling_abs_move is not None
    assert third.warmup is False


def test_feature_values_are_explicitly_rounded() -> None:
    spec = _spec(return_places=6, mean_places=2)
    ticks = _ticks()

    frame = compute_features(spec=spec, ticks=ticks, dataset_hash=_HASH)

    for row in frame.rows[3:]:
        for value in row.lag_returns:
            assert value is not None
            assert value.as_tuple().exponent == -6
        assert row.rolling_mean is not None
        assert row.rolling_mean.as_tuple().exponent == -2
        assert row.rolling_abs_move is not None
        assert row.rolling_abs_move.as_tuple().exponent == -2


def test_feature_hash_binds_dataset_hash() -> None:
    spec = _spec()
    ticks = _ticks()

    a = compute_features(spec=spec, ticks=ticks, dataset_hash="a" * 64)
    b = compute_features(spec=spec, ticks=ticks, dataset_hash="b" * 64)
    c = compute_features(spec=spec, ticks=ticks, dataset_hash="a" * 64)

    assert a.feature_hash != b.feature_hash
    assert a.feature_hash == c.feature_hash


def test_compute_features_is_deterministic() -> None:
    spec = _spec()
    ticks = _ticks()

    first = compute_features(spec=spec, ticks=ticks, dataset_hash=_HASH)
    second = compute_features(spec=spec, ticks=ticks, dataset_hash=_HASH)

    assert first == second


def test_rejects_unordered_ticks() -> None:
    spec = _spec()
    ticks = _ticks()
    unordered = (ticks[1], ticks[0], *ticks[2:])

    with pytest.raises(InvalidFeatureInput, match="increasing"):
        compute_features(spec=spec, ticks=unordered, dataset_hash=_HASH)
