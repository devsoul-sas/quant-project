"""Causal temporal feature computation without future leakage."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from hashlib import sha256
from itertools import pairwise

from devsoul_quant.domain.replay import Tick

_HASH_CHARS = frozenset("0123456789abcdef")
_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
FEATURE_SET_NAME = "momentum-baseline"
FEATURE_SET_VERSION = "1"


class InvalidFeatureSpec(ValueError):
    """Raised when a feature spec violates invariants."""


class InvalidFeatureInput(ValueError):
    """Raised when feature inputs are unordered or malformed."""


def _require_non_blank(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidFeatureSpec(f"{field} must be a non-blank string")


def _require_positive_int(value: object, field: str) -> None:
    if type(value) is not int or value < 1:
        raise InvalidFeatureSpec(f"{field} must be a positive integer")


def _require_hash(value: object, field: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HASH_CHARS for character in value)
    ):
        raise InvalidFeatureInput(f"{field} must be a lowercase SHA-256 hash")


@dataclass(frozen=True, slots=True)
class FeatureSetSpec:
    """Frozen definition of a feature family with explicit windows and rounding."""

    name: str
    version: str
    lag_windows: tuple[int, ...]
    rolling_window: int
    return_places: int = 12
    mean_places: int = 4

    def __post_init__(self) -> None:
        _require_non_blank(self.name, "name")
        _require_non_blank(self.version, "version")
        if not isinstance(self.lag_windows, tuple) or not self.lag_windows:
            raise InvalidFeatureSpec("lag_windows must be a non-empty tuple")
        seen: set[int] = set()
        for window in self.lag_windows:
            if type(window) is not int or window < 1:
                raise InvalidFeatureSpec("lag windows must be positive integers")
            if window in seen:
                raise InvalidFeatureSpec("lag windows must be distinct")
            seen.add(window)
        if type(self.rolling_window) is not int or self.rolling_window < 2:
            raise InvalidFeatureSpec("rolling_window must be an integer of at least two")
        _require_positive_int(self.return_places, "return_places")
        _require_positive_int(self.mean_places, "mean_places")

    def spec_hash(self) -> str:
        canonical = json.dumps(
            {
                "lag_windows": sorted(self.lag_windows),
                "mean_places": self.mean_places,
                "name": self.name,
                "return_places": self.return_places,
                "rolling_window": self.rolling_window,
                "version": self.version,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class FeatureRow:
    """Features for one tick, with UNAVAILABLE represented as None."""

    epoch: int
    lag_returns: tuple[Decimal | None, ...]
    rolling_mean: Decimal | None
    rolling_abs_move: Decimal | None
    warmup: bool


@dataclass(frozen=True, slots=True)
class FeatureFrame:
    """Causal feature output bound to a dataset snapshot hash."""

    spec: FeatureSetSpec
    dataset_hash: str
    rows: tuple[FeatureRow, ...]
    feature_hash: str


def _round(value: Decimal, places: int) -> Decimal:
    quantum = Decimal(1).scaleb(-places)
    with localcontext(_CONTEXT):
        return value.quantize(quantum, rounding=ROUND_HALF_EVEN)


def _lag_return(quote: Decimal, previous: Decimal, places: int) -> Decimal:
    with localcontext(_CONTEXT):
        raw = (quote - previous) / previous
    return _round(raw, places)


def _mean(values: tuple[Decimal, ...], places: int) -> Decimal:
    with localcontext(_CONTEXT):
        raw = sum(values, Decimal(0)) / Decimal(len(values))
    return _round(raw, places)


def _row_json(row: FeatureRow) -> str:
    lag = [None if value is None else format(value, "f") for value in row.lag_returns]
    mean = None if row.rolling_mean is None else format(row.rolling_mean, "f")
    move = None if row.rolling_abs_move is None else format(row.rolling_abs_move, "f")
    return json.dumps(
        {
            "epoch": row.epoch,
            "lag_returns": lag,
            "rolling_abs_move": move,
            "rolling_mean": mean,
            "warmup": row.warmup,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _feature_hash(
    spec: FeatureSetSpec,
    dataset_hash: str,
    rows: tuple[FeatureRow, ...],
) -> str:
    body = "\n".join([spec.spec_hash(), dataset_hash, *[_row_json(row) for row in rows]])
    return sha256(body.encode()).hexdigest()


def compute_features(
    *,
    spec: FeatureSetSpec,
    ticks: Sequence[Tick],
    dataset_hash: str,
) -> FeatureFrame:
    """Compute causal features using only rows <= the current index."""
    _require_hash(dataset_hash, "dataset_hash")
    for previous, current in pairwise(ticks):
        if current.epoch <= previous.epoch:
            raise InvalidFeatureInput("ticks must be strictly increasing")
    quotes = [tick.quote for tick in ticks]
    rows: list[FeatureRow] = []
    for index, tick in enumerate(ticks):
        lag_returns: list[Decimal | None] = []
        for window in spec.lag_windows:
            if index >= window:
                lag_returns.append(
                    _lag_return(quotes[index], quotes[index - window], spec.return_places)
                )
            else:
                lag_returns.append(None)
        if index >= spec.rolling_window - 1:
            window_quotes = tuple(quotes[index - spec.rolling_window + 1 : index + 1])
            rolling_mean: Decimal | None = _mean(window_quotes, spec.mean_places)
            moves = tuple(
                abs(window_quotes[i] - window_quotes[i - 1]) for i in range(1, len(window_quotes))
            )
            rolling_abs_move: Decimal | None = _mean(moves, spec.mean_places)
        else:
            rolling_mean = None
            rolling_abs_move = None
        lag = tuple(lag_returns)
        warmup = (
            any(value is None for value in lag) or rolling_mean is None or rolling_abs_move is None
        )
        rows.append(
            FeatureRow(
                epoch=tick.epoch,
                lag_returns=lag,
                rolling_mean=rolling_mean,
                rolling_abs_move=rolling_abs_move,
                warmup=warmup,
            )
        )
    frozen_rows = tuple(rows)
    return FeatureFrame(
        spec=spec,
        dataset_hash=dataset_hash,
        rows=frozen_rows,
        feature_hash=_feature_hash(spec, dataset_hash, frozen_rows),
    )
