"""Temporal split, purge, embargo, and sealed holdout tests."""

from collections.abc import Mapping
from datetime import UTC, datetime

import pytest

from devsoul_quant.domain.experiments import StrategyRelease
from devsoul_quant.domain.ledger import LedgerScalar
from devsoul_quant.domain.synthetic import generate_ticks
from devsoul_quant.domain.validation import (
    InvalidSplit,
    SealedHoldoutLocked,
    TemporalSplitSpec,
    WalkForwardFold,
    split_ticks,
)


def _spec(**overrides: object) -> TemporalSplitSpec:
    fields: dict[str, object] = {
        "lookback_ticks": 3,
        "purge_ticks": 3,
        "embargo_ticks": 2,
        "test_ticks": 3,
        "fold_count": 3,
        "holdout_ticks": 4,
    }
    fields.update(overrides)
    return TemporalSplitSpec(**fields)  # type: ignore[arg-type]


def _frozen_release() -> StrategyRelease:
    return StrategyRelease.draft(
        release_id="release-1",
        strategy_hash="a" * 64,
        feature_set_hash="b" * 64,
        risk_policy_hash="c" * 64,
    ).freeze(datetime(2026, 10, 29, tzinfo=UTC))


@pytest.mark.parametrize(
    "overrides",
    [
        {"purge_ticks": 2},  # purge < lookback
        {"embargo_ticks": 0},
        {"test_ticks": 0},
        {"fold_count": 0},
        {"holdout_ticks": 0},
        {"lookback_ticks": -1},
    ],
)
def test_spec_rejects_inadequate_gaps(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidSplit):
        _spec(**overrides)


def test_spec_is_immutable() -> None:
    spec = _spec()

    with pytest.raises(AttributeError):
        spec.purge_ticks = 99  # type: ignore[misc]


def test_fold_rejects_overlap() -> None:
    train = generate_ticks(seed=1, count=4, start_epoch=100)
    test = generate_ticks(seed=2, count=4, start_epoch=101)

    with pytest.raises(InvalidSplit, match="strictly after"):
        WalkForwardFold(index=0, train_ticks=train, test_ticks=test)


def test_fold_rejects_unordered_boundaries() -> None:
    train = generate_ticks(seed=1, count=4, start_epoch=200)
    test = generate_ticks(seed=2, count=4, start_epoch=100)

    with pytest.raises(InvalidSplit, match="strictly after"):
        WalkForwardFold(index=0, train_ticks=train, test_ticks=test)


def test_split_rejects_unordered_ticks() -> None:
    spec = _spec()
    ticks = generate_ticks(seed=42, count=30)
    unordered = (ticks[1], ticks[0], *ticks[2:])

    with pytest.raises(InvalidSplit, match="increasing"):
        split_ticks(spec=spec, ticks=unordered, run_id="run-1")


def test_split_requires_enough_ticks() -> None:
    spec = _spec()
    ticks = generate_ticks(seed=42, count=5)

    with pytest.raises(InvalidSplit, match="not enough"):
        split_ticks(spec=spec, ticks=ticks, run_id="run-1")


def test_split_produces_ordered_non_overlapping_folds() -> None:
    spec = _spec()
    ticks = generate_ticks(seed=42, count=30)

    split = split_ticks(spec=spec, ticks=ticks, run_id="run-1")

    assert len(split.folds) == 3
    assert split.holdout.tick_count == 4
    for fold in split.folds:
        assert fold.test_ticks[0].epoch > fold.train_ticks[-1].epoch


def test_holdout_exposes_only_hash_and_count_before_freeze() -> None:
    spec = _spec()
    ticks = generate_ticks(seed=42, count=30)
    split = split_ticks(spec=spec, ticks=ticks, run_id="run-1")

    holdout = split.holdout
    assert holdout.tick_count == 4
    assert len(holdout.holdout_hash) == 64
    assert not hasattr(holdout, "ticks")
    assert not hasattr(holdout, "_ticks")
    assert holdout.is_open is False

    with pytest.raises(SealedHoldoutLocked, match="frozen"):
        holdout.open(
            StrategyRelease.draft(
                release_id="r",
                strategy_hash="a" * 64,
                feature_set_hash="b" * 64,
                risk_policy_hash="c" * 64,
            ),
            ticks=tuple(ticks[-spec.holdout_ticks :]),
        )


def test_holdout_opens_once_with_a_frozen_release() -> None:
    spec = _spec()
    ticks = generate_ticks(seed=42, count=30)
    split = split_ticks(spec=spec, ticks=ticks, run_id="run-1")
    holdout = split.holdout
    release = _frozen_release()

    revealed = holdout.open(release, ticks=tuple(ticks[-spec.holdout_ticks :]))

    assert revealed == tuple(ticks[-(spec.holdout_ticks) :])
    assert holdout.is_open is True
    with pytest.raises(SealedHoldoutLocked, match="already"):
        holdout.open(release, ticks=tuple(ticks[-spec.holdout_ticks :]))


def test_holdout_rejects_ticks_that_do_not_match_commitment() -> None:
    spec = _spec()
    ticks = generate_ticks(seed=42, count=30)
    split = split_ticks(spec=spec, ticks=ticks, run_id="run-1")

    with pytest.raises(SealedHoldoutLocked, match="commitment"):
        split.holdout.open(
            _frozen_release(),
            ticks=generate_ticks(seed=99, count=spec.holdout_ticks),
        )


def test_holdout_open_records_an_event_tied_to_release_and_run() -> None:
    spec = _spec()
    ticks = generate_ticks(seed=42, count=30)
    split = split_ticks(spec=spec, ticks=ticks, run_id="run-9")
    release = _frozen_release()

    recorded: list[tuple[str, Mapping[str, LedgerScalar]]] = []

    def record(event_type: str, payload: Mapping[str, LedgerScalar]) -> None:
        recorded.append((event_type, payload))

    split.holdout.open(
        release,
        ticks=tuple(ticks[-spec.holdout_ticks :]),
        record=record,
    )

    assert recorded[0][0] == "HOLDOUT_OPENED"
    assert recorded[0][1]["release_id"] == "release-1"
    assert recorded[0][1]["release_hash"] == "a" * 64
    assert recorded[0][1]["run_id"] == "run-9"
    assert recorded[0][1]["holdout_hash"] == split.holdout.holdout_hash


def test_spec_hash_is_deterministic() -> None:
    first = _spec().spec_hash()
    second = _spec().spec_hash()
    changed = _spec(holdout_ticks=5).spec_hash()

    assert first == second
    assert changed != first
