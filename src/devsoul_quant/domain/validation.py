"""Temporal split, purge, embargo, and sealed holdout."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from itertools import pairwise

from devsoul_quant.domain.datasets import hash_ticks
from devsoul_quant.domain.experiments import StrategyRelease
from devsoul_quant.domain.ledger import LedgerScalar
from devsoul_quant.domain.replay import Tick


class InvalidSplit(ValueError):
    """Raised when a temporal split violates ordering or gap invariants."""


class SealedHoldoutLocked(ValueError):
    """Raised when a sealed holdout is opened before freeze or a second time."""


def _require_ordered(ticks: Sequence[Tick], field: str) -> None:
    for previous, current in pairwise(ticks):
        if current.epoch <= previous.epoch:
            raise InvalidSplit(f"{field} must be strictly increasing")


@dataclass(frozen=True, slots=True)
class TemporalSplitSpec:
    """Frozen recipe for a walk-forward split with purge, embargo, and holdout."""

    lookback_ticks: int
    purge_ticks: int
    embargo_ticks: int
    test_ticks: int
    fold_count: int
    holdout_ticks: int

    def __post_init__(self) -> None:
        for name in (
            "lookback_ticks",
            "purge_ticks",
            "embargo_ticks",
            "test_ticks",
            "fold_count",
            "holdout_ticks",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise InvalidSplit(f"{name} must be a positive integer")
        if self.purge_ticks < self.lookback_ticks:
            raise InvalidSplit("purge must cover the maximum lookback")

    def spec_hash(self) -> str:
        canonical = json.dumps(
            {
                "embargo_ticks": self.embargo_ticks,
                "fold_count": self.fold_count,
                "holdout_ticks": self.holdout_ticks,
                "lookback_ticks": self.lookback_ticks,
                "purge_ticks": self.purge_ticks,
                "test_ticks": self.test_ticks,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    """One non-overlapping, temporally ordered train/test pair."""

    index: int
    train_ticks: tuple[Tick, ...]
    test_ticks: tuple[Tick, ...]

    def __post_init__(self) -> None:
        if type(self.index) is not int or self.index < 0:
            raise InvalidSplit("fold index must be a non-negative integer")
        _require_ordered(self.train_ticks, "train ticks")
        _require_ordered(self.test_ticks, "test ticks")
        if (
            self.train_ticks
            and self.test_ticks
            and self.test_ticks[0].epoch <= self.train_ticks[-1].epoch
        ):
            raise InvalidSplit("test ticks must come strictly after train ticks")


class SealedHoldout:
    """Commitment opened only after freeze; the object never retains holdout ticks."""

    def __init__(self, tick_count: int, *, run_id: str, holdout_hash: str) -> None:
        self._tick_count = tick_count
        self._run_id = run_id
        self._holdout_hash = holdout_hash
        self._opened = False

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def holdout_hash(self) -> str:
        return self._holdout_hash

    @property
    def is_open(self) -> bool:
        return self._opened

    def open(
        self,
        release: StrategyRelease,
        *,
        ticks: Sequence[Tick],
        record: Callable[[str, Mapping[str, LedgerScalar]], None] | None = None,
    ) -> tuple[Tick, ...]:
        """Validate and reveal supplied ticks once after the release is frozen."""
        if release.frozen_at is None:
            raise SealedHoldoutLocked("holdout requires a frozen strategy release")
        if self._opened:
            raise SealedHoldoutLocked("holdout has already been opened")
        revealed = tuple(ticks)
        if len(revealed) != self._tick_count or hash_ticks(revealed) != self._holdout_hash:
            raise SealedHoldoutLocked("holdout ticks do not match the sealed commitment")
        if record is not None:
            record(
                "HOLDOUT_OPENED",
                {
                    "release_id": release.release_id,
                    "release_hash": release.strategy_hash,
                    "run_id": self._run_id,
                    "holdout_hash": self._holdout_hash,
                },
            )
        self._opened = True
        return revealed


@dataclass(frozen=True, slots=True)
class TemporalSplit:
    """A validated walk-forward split plus its sealed holdout."""

    spec: TemporalSplitSpec
    folds: tuple[WalkForwardFold, ...]
    holdout: SealedHoldout


def split_ticks(*, spec: TemporalSplitSpec, ticks: Sequence[Tick], run_id: str) -> TemporalSplit:
    """Split an ordered tick sequence into folds and a sealed holdout."""
    if not isinstance(run_id, str) or not run_id.strip():
        raise InvalidSplit("run_id must be a non-blank string")
    ordered = tuple(ticks)
    _require_ordered(ordered, "ticks")
    total = len(ordered)
    holdout_size = spec.holdout_ticks
    embargo_size = spec.embargo_ticks
    region_size = total - holdout_size - embargo_size
    test_total = spec.test_ticks * spec.fold_count
    if region_size < test_total + spec.purge_ticks + 1:
        raise InvalidSplit("not enough ticks for the requested walk-forward split")
    test_region_start = region_size - test_total
    folds: list[WalkForwardFold] = []
    for fold_index in range(spec.fold_count):
        test_start = test_region_start + fold_index * spec.test_ticks
        train_end = test_start - spec.purge_ticks
        folds.append(
            WalkForwardFold(
                index=fold_index,
                train_ticks=ordered[0:train_end],
                test_ticks=ordered[test_start : test_start + spec.test_ticks],
            )
        )
    holdout_start = region_size + embargo_size
    holdout_ticks = ordered[holdout_start : holdout_start + holdout_size]
    holdout = SealedHoldout(
        len(holdout_ticks),
        run_id=run_id,
        holdout_hash=hash_ticks(tuple(holdout_ticks)),
    )
    return TemporalSplit(spec=spec, folds=tuple(folds), holdout=holdout)
