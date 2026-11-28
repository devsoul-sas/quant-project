"""Versioned, credential-free ACCU experiment specification for S4.4."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

_ALLOWED_SYMBOLS = frozenset({"R_100", "R_75", "R_50", "R_25"})
_FORBIDDEN_KEY_PARTS = (
    "tick",
    "quote",
    "proposal",
    "feature_value",
    "learned",
    "weight",
    "result",
    "metric_value",
    "token",
    "otp",
    "credential",
)


class InvalidAccuExperimentSpec(ValueError):
    """Raised when an ACCU research protocol is ambiguous or unsafe."""


@dataclass(frozen=True, slots=True)
class AccuRuleSpec:
    rule_id: str
    minimum_streak_age: int
    maximum_streak_age: int
    minimum_previous_streak: int
    maximum_recent_volatility: Decimal
    maximum_range_width: Decimal
    minimum_range_position: Decimal
    maximum_range_position: Decimal
    maximum_current_move: Decimal


@dataclass(frozen=True, slots=True)
class AccuSplitSpec:
    train_fraction: Decimal
    validation_fraction: Decimal
    holdout_fraction: Decimal
    purge_ticks: int


@dataclass(frozen=True, slots=True)
class AccuStatisticsSpec:
    resamples: int
    seed: int
    block_length: int
    family_alpha: Decimal
    minimum_rule_entries: int
    minimum_absolute_lift: Decimal


@dataclass(frozen=True, slots=True)
class AccuExperimentSpec:
    version: str
    hypothesis: str
    symbols: tuple[str, ...]
    growth_rates: tuple[Decimal, ...]
    horizons: tuple[int, ...]
    primary_horizon: int
    maximum_ticks: int
    maximum_duration_seconds: int
    cadence_seconds: int
    volatility_window: int
    range_window: int
    rules: tuple[AccuRuleSpec, ...]
    split: AccuSplitSpec
    statistics: AccuStatisticsSpec
    baseline: str
    normalization: str
    selection_method: str
    data_policy: str
    maximum_contracts: int
    spec_hash: str


def _decimal(value: object, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise InvalidAccuExperimentSpec(f"{field} must be Decimal-compatible") from None
    if not result.is_finite():
        raise InvalidAccuExperimentSpec(f"{field} must be finite")
    return result


def _integer(value: object, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise InvalidAccuExperimentSpec(f"{field} must be an integer >= {minimum}")
    return value


def _sequence(value: object, field: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise InvalidAccuExperimentSpec(f"{field} must be a non-empty sequence")
    return value


def _reject_forbidden(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise InvalidAccuExperimentSpec("protocol keys must be strings")
            folded = key.casefold()
            # Explicit protocol declarations are allowlisted; values learned
            # from provider data are not.
            if any(part in folded for part in _FORBIDDEN_KEY_PARTS) and key not in {
                "maximum_ticks",
                "purge_ticks",
                "features",
                "feature_windows",
                "persist_provider_data",
                "persist_derived_results",
                "maximum_current_move",
            }:
                raise InvalidAccuExperimentSpec(f"forbidden persistent field: {key}")
            _reject_forbidden(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            _reject_forbidden(nested)
    elif isinstance(value, float):
        raise InvalidAccuExperimentSpec("binary floats are forbidden in protocols")


def _rule(raw: Mapping[str, Any]) -> AccuRuleSpec:
    rule = AccuRuleSpec(
        rule_id=str(raw["rule_id"]),
        minimum_streak_age=_integer(raw["minimum_streak_age"], "minimum_streak_age"),
        maximum_streak_age=_integer(raw["maximum_streak_age"], "maximum_streak_age"),
        minimum_previous_streak=_integer(raw["minimum_previous_streak"], "minimum_previous_streak"),
        maximum_recent_volatility=_decimal(
            raw["maximum_recent_volatility"], "maximum_recent_volatility"
        ),
        maximum_range_width=_decimal(raw["maximum_range_width"], "maximum_range_width"),
        minimum_range_position=_decimal(raw["minimum_range_position"], "minimum_range_position"),
        maximum_range_position=_decimal(raw["maximum_range_position"], "maximum_range_position"),
        maximum_current_move=_decimal(raw["maximum_current_move"], "maximum_current_move"),
    )
    if not rule.rule_id.strip() or rule.minimum_streak_age > rule.maximum_streak_age:
        raise InvalidAccuExperimentSpec("invalid rule identity or streak bounds")
    if not Decimal(0) <= rule.minimum_range_position <= rule.maximum_range_position <= Decimal(1):
        raise InvalidAccuExperimentSpec("rule range positions must be ordered within [0, 1]")
    return rule


def load_accu_experiment_spec(raw: Mapping[str, Any]) -> AccuExperimentSpec:
    """Validate and freeze a persistent protocol that contains no learned state."""
    if not isinstance(raw, Mapping):
        raise InvalidAccuExperimentSpec("protocol must be a mapping")
    _reject_forbidden(raw)
    symbols = tuple(str(item) for item in _sequence(raw["symbols"], "symbols"))
    growth_rates = tuple(
        _decimal(item, "growth_rate") for item in _sequence(raw["growth_rates"], "growth_rates")
    )
    horizons = tuple(
        _integer(item, "horizon", minimum=1) for item in _sequence(raw["horizons"], "horizons")
    )
    if not set(symbols) <= _ALLOWED_SYMBOLS:
        raise InvalidAccuExperimentSpec("unsupported ACCU symbol")
    if any(not Decimal("0.01") <= rate <= Decimal("0.05") for rate in growth_rates):
        raise InvalidAccuExperimentSpec("growth rates must be within [0.01, 0.05]")
    if any(horizon > 5 for horizon in horizons):
        raise InvalidAccuExperimentSpec("horizons must be within [1, 5]")
    if len(symbols) * len(growth_rates) * len(horizons) > 12:
        raise InvalidAccuExperimentSpec("too many primary combinations")
    rules_raw = _sequence(raw["rules"], "rules")
    rules = tuple(_rule(item) for item in rules_raw if isinstance(item, Mapping))
    if len(rules) != len(rules_raw) or len({rule.rule_id for rule in rules}) != len(rules):
        raise InvalidAccuExperimentSpec("rules must be unique mappings")
    split_raw = raw["split"]
    stats_raw = raw["statistics"]
    if not isinstance(split_raw, Mapping) or not isinstance(stats_raw, Mapping):
        raise InvalidAccuExperimentSpec("split and statistics must be mappings")
    split = AccuSplitSpec(
        train_fraction=_decimal(split_raw["train_fraction"], "train_fraction"),
        validation_fraction=_decimal(split_raw["validation_fraction"], "validation_fraction"),
        holdout_fraction=_decimal(split_raw["holdout_fraction"], "holdout_fraction"),
        purge_ticks=_integer(split_raw["purge_ticks"], "purge_ticks", minimum=1),
    )
    if split.train_fraction + split.validation_fraction + split.holdout_fraction != Decimal(1):
        raise InvalidAccuExperimentSpec("split fractions must sum to one")
    statistics = AccuStatisticsSpec(
        resamples=_integer(stats_raw["resamples"], "resamples", minimum=1),
        seed=_integer(stats_raw["seed"], "seed"),
        block_length=_integer(stats_raw["block_length"], "block_length", minimum=1),
        family_alpha=_decimal(stats_raw["family_alpha"], "family_alpha"),
        minimum_rule_entries=_integer(
            stats_raw["minimum_rule_entries"], "minimum_rule_entries", minimum=1
        ),
        minimum_absolute_lift=_decimal(stats_raw["minimum_absolute_lift"], "minimum_absolute_lift"),
    )
    primary_horizon = _integer(raw["primary_horizon"], "primary_horizon", minimum=1)
    if primary_horizon not in horizons:
        raise InvalidAccuExperimentSpec("primary_horizon must be in horizons")
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return AccuExperimentSpec(
        version=str(raw["version"]),
        hypothesis=str(raw["hypothesis"]),
        symbols=symbols,
        growth_rates=growth_rates,
        horizons=horizons,
        primary_horizon=primary_horizon,
        maximum_ticks=_integer(raw["maximum_ticks"], "maximum_ticks", minimum=1),
        maximum_duration_seconds=_integer(
            raw["maximum_duration_seconds"], "maximum_duration_seconds", minimum=1
        ),
        cadence_seconds=_integer(raw["cadence_seconds"], "cadence_seconds", minimum=1),
        volatility_window=_integer(
            raw["feature_windows"]["volatility"], "volatility_window", minimum=2
        ),
        range_window=_integer(raw["feature_windows"]["range"], "range_window", minimum=2),
        rules=rules,
        split=split,
        statistics=statistics,
        baseline=str(raw["baseline"]),
        normalization=str(raw["normalization"]),
        selection_method=str(raw["selection_method"]),
        data_policy=str(raw["data_policy"]),
        maximum_contracts=_integer(raw["maximum_contracts"], "maximum_contracts"),
        spec_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )
