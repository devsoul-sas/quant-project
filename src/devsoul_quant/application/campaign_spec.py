"""Declarative, credential-free local campaign specification (S3.10/F).

A campaign spec captures every bound a pre-authorised local run needs — protocol
and its hash, instrument, hypothesis, execution mode, duration, warm-up, minimum
sample, seed, baselines, metrics, gates, risk limits, data policy and stop
conditions — without embedding any credential or market datum. ``load_campaign_spec``
rejects keys that carry credentials or market data so a spec file can never become
a persistence surface for restricted state.

Quantitative execution never invokes an LLM: the spec is consumed by the
deterministic runner only.
"""

from __future__ import annotations

from collections.abc import Mapping
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


class InvalidCampaignSpec(ValueError):
    """Raised when a campaign spec is ambiguous, incomplete or non-fail-closed."""


@dataclass(frozen=True, slots=True)
class CampaignSpec:
    campaign_id: str
    protocol: str
    protocol_hash: str
    instrument: str
    hypothesis: str
    mode: str
    maximum_duration_seconds: int
    warmup_labels: int
    minimum_sample_size: int
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
            "instrument",
            "hypothesis",
            "data_policy",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidCampaignSpec(f"{name} must be a non-blank string")
        if self.mode not in _ALLOWED_MODES:
            raise InvalidCampaignSpec(f"mode must be one of {sorted(_ALLOWED_MODES)}")
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
                or any(not isinstance(item, str) for item in value)
            ):
                raise InvalidCampaignSpec(f"{name} must be a non-empty tuple of strings")


def load_campaign_spec(raw: Mapping[str, Any]) -> CampaignSpec:
    """Build a ``CampaignSpec`` from a plain mapping, rejecting restricted keys."""
    if not isinstance(raw, Mapping):
        raise InvalidCampaignSpec("campaign spec must be a mapping")
    for key in raw:
        if key in _FORBIDDEN_KEYS:
            raise InvalidCampaignSpec(f"campaign spec must not contain restricted key {key!r}")
    return CampaignSpec(**raw)
