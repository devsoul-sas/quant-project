"""Frozen strategy and validation evidence entities."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class InvalidExperiment(ValueError):
    """Raised when experiment evidence is incomplete or mutable."""


def _require_non_blank(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidExperiment(f"{field} must be a non-blank string")


def _require_hash(value: str, field: str) -> None:
    if not isinstance(value, str) or _HASH_PATTERN.fullmatch(value) is None:
        raise InvalidExperiment(f"{field} must be a lowercase SHA-256 hash")


def _require_aware(instant: datetime, field: str) -> None:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise InvalidExperiment(f"{field} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Signal:
    """Versioned strategy evidence without stake or execution authority."""

    signal_id: str
    strategy_release_id: str
    feature_set_hash: str
    symbol: str
    reason: str

    def __post_init__(self) -> None:
        _require_non_blank(self.signal_id, "signal_id")
        _require_non_blank(self.strategy_release_id, "strategy_release_id")
        _require_hash(self.feature_set_hash, "feature_set_hash")
        _require_non_blank(self.symbol, "symbol")
        _require_non_blank(self.reason, "reason")


@dataclass(frozen=True, slots=True)
class StrategyRelease:
    """Immutable strategy configuration that can be sealed for validation."""

    release_id: str
    strategy_hash: str
    feature_set_hash: str
    risk_policy_hash: str
    frozen_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.release_id, "release_id")
        _require_hash(self.strategy_hash, "strategy_hash")
        _require_hash(self.feature_set_hash, "feature_set_hash")
        _require_hash(self.risk_policy_hash, "risk_policy_hash")
        if self.frozen_at is not None:
            _require_aware(self.frozen_at, "frozen_at")

    @classmethod
    def draft(
        cls,
        *,
        release_id: str,
        strategy_hash: str,
        feature_set_hash: str,
        risk_policy_hash: str,
    ) -> StrategyRelease:
        return cls(release_id, strategy_hash, feature_set_hash, risk_policy_hash)

    def freeze(self, instant: datetime) -> StrategyRelease:
        _require_aware(instant, "frozen_at")
        if self.frozen_at is not None and self.frozen_at != instant:
            raise InvalidExperiment("strategy release is already frozen")
        return replace(self, frozen_at=instant)


@dataclass(frozen=True, slots=True)
class ValidationRun:
    """A sealed set of evidence inputs for one validation execution."""

    run_id: str
    release_id: str
    strategy_hash: str
    feature_set_hash: str
    risk_policy_hash: str
    dataset_hash: str
    code_hash: str
    contract_spec_hash: str

    def __post_init__(self) -> None:
        _require_non_blank(self.run_id, "run_id")
        _require_non_blank(self.release_id, "release_id")
        for field in (
            "strategy_hash",
            "feature_set_hash",
            "risk_policy_hash",
            "dataset_hash",
            "code_hash",
            "contract_spec_hash",
        ):
            _require_hash(getattr(self, field), field)

    @classmethod
    def start(
        cls,
        *,
        run_id: str,
        release: StrategyRelease,
        dataset_hash: str,
        code_hash: str,
        contract_spec_hash: str,
    ) -> ValidationRun:
        if release.frozen_at is None:
            raise InvalidExperiment("strategy release must be frozen before validation")
        return cls(
            run_id=run_id,
            release_id=release.release_id,
            strategy_hash=release.strategy_hash,
            feature_set_hash=release.feature_set_hash,
            risk_policy_hash=release.risk_policy_hash,
            dataset_hash=dataset_hash,
            code_hash=code_hash,
            contract_spec_hash=contract_spec_hash,
        )
