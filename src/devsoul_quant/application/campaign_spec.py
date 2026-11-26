"""Declarative, credential-free local campaign specification (S3.10/F, S3.11).

A campaign spec captures every bound a pre-authorised local run needs — protocol
and its hash, the prospective amendment and its hash, instrument, hypothesis,
execution mode, duration, warm-up, minimum effective sample, seed, baselines,
metrics, gates, risk limits, data policy and stop conditions — without embedding
any credential or market datum. ``load_campaign_spec`` coerces JSON scalars
(lists to tuples, floats to ``Decimal``) and rejects keys that carry credentials
or market data so a spec file can never become a persistence surface for
restricted state.

Quantitative execution never invokes an LLM: the spec is consumed by the
deterministic runner only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

_FORBIDDEN_KEYS = frozenset(
    {
        "token",
        "app_id",
        "account_id",
        "api_key",
        "apikey",
        "password",
        "secret",
        "credential",
        "otp",
        "authorization",
        "bearer",
        "ticks",
        "quotes",
        "market_data",
        "feed",
    }
)

_ALLOWED_MODES = frozenset(
    {"OBSERVE_ONLY", "SHADOW_TRADING", "DEMO_INTEGRATION", "DEMO_EXPLORATORY"}
)

_ALLOWED_HYPOTHESES = frozenset({"STEP_DIRECTION_DEPENDENCE_V1", "STEP_DIRECTION_DEPENDENCE_V2"})


class InvalidCampaignSpec(ValueError):
    """Raised when a campaign spec is ambiguous, incomplete or non-fail-closed."""


@dataclass(frozen=True, slots=True)
class CampaignSpec:
    campaign_id: str
    protocol: str
    protocol_hash: str
    amendment: str
    amendment_hash: str
    instrument: str
    hypothesis: str
    mode: str
    maximum_duration_seconds: int
    warmup_labels: int
    minimum_sample_size: int
    tick_cadence_seconds: int | None
    seed: int
    baselines: tuple[str, ...]
    metrics: tuple[str, ...]
    gates: tuple[str, ...]
    fixed_stake: Decimal
    maximum_contracts: int
    maximum_session_loss: Decimal
    data_policy: str
    stop_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "campaign_id",
            "protocol",
            "protocol_hash",
            "amendment",
            "amendment_hash",
            "instrument",
            "hypothesis",
            "data_policy",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidCampaignSpec(f"{name} must be a non-blank string")
        if self.mode not in _ALLOWED_MODES:
            raise InvalidCampaignSpec(f"mode must be one of {sorted(_ALLOWED_MODES)}")
        if self.hypothesis not in _ALLOWED_HYPOTHESES:
            raise InvalidCampaignSpec(f"hypothesis must be one of {sorted(_ALLOWED_HYPOTHESES)}")
        for name in (
            "maximum_duration_seconds",
            "warmup_labels",
            "minimum_sample_size",
            "seed",
            "maximum_contracts",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise InvalidCampaignSpec(f"{name} must be a non-negative integer")
        if self.tick_cadence_seconds is not None and (
            type(self.tick_cadence_seconds) is not int or self.tick_cadence_seconds < 1
        ):
            raise InvalidCampaignSpec("tick_cadence_seconds must be a positive integer or null")
        if not 1 <= self.maximum_duration_seconds < 24 * 60 * 60:
            raise InvalidCampaignSpec("maximum_duration_seconds must be within [1, 86400)")
        for name in ("fixed_stake", "maximum_session_loss"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise InvalidCampaignSpec(f"{name} must be a finite non-negative Decimal")
        for name in ("baselines", "metrics", "gates", "stop_conditions"):
            value = getattr(self, name)
            if (
                not isinstance(value, tuple)
                or not value
                or any(not isinstance(item, str) or not item for item in value)
            ):
                raise InvalidCampaignSpec(f"{name} must be a non-empty tuple of non-blank strings")


def _to_decimal(value: object, name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise InvalidCampaignSpec(f"{name} must be numeric")
    if isinstance(value, (int, float, str)):
        from decimal import InvalidOperation

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise InvalidCampaignSpec(f"{name} must be numeric") from None
    raise InvalidCampaignSpec(f"{name} must be numeric")


def _to_int(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise InvalidCampaignSpec(f"{name} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise InvalidCampaignSpec(f"{name} must be an integer")


def _to_tuple_of_strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise InvalidCampaignSpec(f"{name} must be a non-empty list of strings")
    items = tuple(value)
    if not items or any(not isinstance(item, str) or not item for item in items):
        raise InvalidCampaignSpec(f"{name} must be a non-empty list of strings")
    return items


def load_campaign_spec(raw: Mapping[str, Any]) -> CampaignSpec:
    """Build a ``CampaignSpec`` from a plain mapping, rejecting restricted keys."""
    if not isinstance(raw, Mapping):
        raise InvalidCampaignSpec("campaign spec must be a mapping")
    for key in raw:
        if key in _FORBIDDEN_KEYS:
            raise InvalidCampaignSpec(f"campaign spec must not contain restricted key {key!r}")
    return CampaignSpec(
        campaign_id=raw["campaign_id"],
        protocol=raw["protocol"],
        protocol_hash=raw["protocol_hash"],
        amendment=raw["amendment"],
        amendment_hash=raw["amendment_hash"],
        instrument=raw["instrument"],
        hypothesis=raw["hypothesis"],
        mode=raw["mode"],
        maximum_duration_seconds=_to_int(
            raw["maximum_duration_seconds"], "maximum_duration_seconds"
        ),
        warmup_labels=_to_int(raw["warmup_labels"], "warmup_labels"),
        minimum_sample_size=_to_int(raw["minimum_sample_size"], "minimum_sample_size"),
        tick_cadence_seconds=(
            None
            if raw.get("tick_cadence_seconds") is None
            else _to_int(raw["tick_cadence_seconds"], "tick_cadence_seconds")
        ),
        seed=_to_int(raw["seed"], "seed"),
        baselines=_to_tuple_of_strings(raw["baselines"], "baselines"),
        metrics=_to_tuple_of_strings(raw["metrics"], "metrics"),
        gates=_to_tuple_of_strings(raw["gates"], "gates"),
        fixed_stake=_to_decimal(raw["fixed_stake"], "fixed_stake"),
        maximum_contracts=_to_int(raw["maximum_contracts"], "maximum_contracts"),
        maximum_session_loss=_to_decimal(raw["maximum_session_loss"], "maximum_session_loss"),
        data_policy=raw["data_policy"],
        stop_conditions=_to_tuple_of_strings(raw["stop_conditions"], "stop_conditions"),
    )
