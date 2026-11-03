"""Aggregate non-economic evaluation over an ephemeral Deriv demo tick sample."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from devsoul_quant import __version__
from devsoul_quant.adapters.deriv.ephemeral import EphemeralTickCache
from devsoul_quant.application.evaluate import trials_from_ticks
from devsoul_quant.domain.execution_mode import ExecutionMode
from devsoul_quant.domain.metrics import EvaluationReport, EvidenceMode, TrialOutcome, evaluate
from devsoul_quant.domain.replay import EconomyProvenance, Tick


class InvalidLiveEvaluation(ValueError):
    """Raised when an ephemeral live evaluation design is invalid."""


@dataclass(frozen=True, slots=True)
class LiveEvaluationReport:
    """Public aggregate report that excludes raw ticks and monetary claims."""

    schema_version: str
    code_version: str
    execution_mode: ExecutionMode
    data_source: str
    symbol: str
    tick_count: int
    duration: int
    fold_tick_sizes: tuple[int, ...]
    fold_sizes: tuple[int, ...]
    purge_ticks: int
    bootstrap_block_size: int
    trial_alignment: str
    overlapping_windows: bool
    sample_warning: str
    economy: EconomyProvenance
    evaluation: EvaluationReport
    profitability_claim: bool
    cache_ttl_seconds: int
    cache_size: int
    cache_expired_count: int

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic representation without provider tick payloads."""
        return {
            "schema_version": self.schema_version,
            "code_version": self.code_version,
            "execution_mode": self.execution_mode.value,
            "data_source": self.data_source,
            "symbol": self.symbol,
            "tick_count": self.tick_count,
            "duration": self.duration,
            "fold_tick_sizes": list(self.fold_tick_sizes),
            "fold_sizes": list(self.fold_sizes),
            "purge_ticks": self.purge_ticks,
            "bootstrap_block_size": self.bootstrap_block_size,
            "trial_alignment": self.trial_alignment,
            "overlapping_windows": self.overlapping_windows,
            "sample_warning": self.sample_warning,
            "economy": self.economy.value,
            "evaluation": self.evaluation.to_dict(),
            "profitability_claim": self.profitability_claim,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "cache_size": self.cache_size,
            "cache_expired_count": self.cache_expired_count,
        }


def _temporal_tick_folds(
    ticks: Sequence[Tick], *, duration: int, fold_count: int
) -> tuple[tuple[Tick, ...], ...]:
    if type(fold_count) is not int or fold_count < 1:
        raise InvalidLiveEvaluation("fold_count must be a positive integer")
    minimum_fold_ticks = duration + 3
    purge_ticks = duration + 2
    usable_ticks = len(ticks) - purge_ticks * (fold_count - 1)
    if usable_ticks < minimum_fold_ticks * fold_count:
        raise InvalidLiveEvaluation("fold_count leaves insufficient ticks after temporal purge")
    base_size, remainder = divmod(usable_ticks, fold_count)
    folds: list[tuple[Tick, ...]] = []
    offset = 0
    for index in range(fold_count):
        size = base_size + int(index < remainder)
        folds.append(tuple(ticks[offset : offset + size]))
        offset += size + purge_ticks
    return tuple(folds)


def run_live_evaluation(
    *,
    ticks: Sequence[Tick],
    symbol: str,
    duration: int = 3,
    fold_count: int = 4,
    seed: int = 42,
) -> LiveEvaluationReport:
    """Evaluate rolling causal tick-proxy trials without retaining provider ticks."""
    if not isinstance(symbol, str) or not symbol.strip():
        raise InvalidLiveEvaluation("symbol must be a non-blank string")
    if type(duration) is not int or duration < 1:
        raise InvalidLiveEvaluation("duration must be a positive integer")
    if type(seed) is not int:
        raise InvalidLiveEvaluation("seed must be an integer")
    if len(ticks) < duration + 3:
        raise InvalidLiveEvaluation("live evaluation requires at least one causally settled trial")

    cache = EphemeralTickCache()
    for tick in ticks:
        cache.store(tick, now_epoch=tick.epoch)
    expired = cache.expire(now_epoch=ticks[-1].epoch)
    active_ticks = cache.ticks
    if len(active_ticks) < duration + 3:
        raise InvalidLiveEvaluation("live evaluation requires at least one causally settled trial")
    tick_folds = _temporal_tick_folds(active_ticks, duration=duration, fold_count=fold_count)
    folds: tuple[tuple[TrialOutcome, ...], ...] = tuple(
        trials_from_ticks(ticks=fold, duration=duration) for fold in tick_folds
    )
    bootstrap_block_size = duration + 2
    evaluation = evaluate(
        folds=folds,
        evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST,
        seed=seed,
        bootstrap_block_size=bootstrap_block_size,
    )

    return LiveEvaluationReport(
        schema_version="2",
        code_version=__version__,
        execution_mode=ExecutionMode.EPHEMERAL_PUBLIC_INTEGRATION,
        data_source="DERIV_DEMO_EPHEMERAL",
        symbol=symbol,
        tick_count=len(active_ticks),
        duration=duration,
        fold_tick_sizes=tuple(len(fold) for fold in tick_folds),
        fold_sizes=tuple(len(fold) for fold in folds),
        purge_ticks=duration + 2,
        bootstrap_block_size=bootstrap_block_size,
        trial_alignment="CAUSAL_ENTRY_AFTER_SIGNAL",
        overlapping_windows=True,
        sample_warning="PURGED_FOLD_TICK_PROXY_DIAGNOSTIC_ONLY",
        economy=EconomyProvenance.UNAVAILABLE,
        evaluation=evaluation,
        profitability_claim=False,
        cache_ttl_seconds=cache.ttl_seconds,
        cache_size=len(cache),
        cache_expired_count=expired,
    )
