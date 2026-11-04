"""Systematic daily-strategy scan over observed ECB data (no profitability claims)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import partial

from devsoul_quant.adapters.ecb.ingest import load_ecb_batch
from devsoul_quant.application.ecb_backtest import UnapprovedEcbSource
from devsoul_quant.application.evaluate import StrategyDecision, evaluate_split
from devsoul_quant.domain.costs import ExecutionCostModel
from devsoul_quant.domain.data_rights import (
    DataRightsManifest,
    PersistentUseDecision,
    decide_persistent_use,
)
from devsoul_quant.domain.metrics import EvidenceMode
from devsoul_quant.domain.replay import EconomyProvenance
from devsoul_quant.domain.strategy import mean_reversion_decision, momentum_window_decision
from devsoul_quant.domain.validation import TemporalSplitSpec, split_ticks


class InvalidEdgeSearch(ValueError):
    """Raised when an edge-search configuration is malformed."""


@dataclass(frozen=True, slots=True)
class EdgeCandidate:
    """One strategy configuration scored on observed data, without P/L claims."""

    strategy: str
    lookback: int
    duration: int
    spread_fraction: Decimal
    decisions: int
    hit_rate: Decimal | None
    bootstrap_lower: Decimal | None
    bootstrap_upper: Decimal | None
    holdout_hash: str
    run_id: str

    @property
    def has_edge(self) -> bool:
        """Whether the bootstrap lower bound sits strictly above coin-flip.

        This is a directional heuristic, NOT a profitability claim.
        """
        return self.bootstrap_lower is not None and self.bootstrap_lower > Decimal("0.50")


def _strategy_for(name: str, lookback: int) -> StrategyDecision:
    if name == "momentum":
        return partial(momentum_window_decision, lookback=lookback)
    if name == "mean-reversion":
        return partial(mean_reversion_decision, lookback=lookback)
    raise InvalidEdgeSearch(f"unknown strategy {name!r}")


def search_daily_edges(
    *,
    csv_text: str,
    currency: str,
    manifest: DataRightsManifest,
    split_spec: TemporalSplitSpec,
    seed: int,
    strategies: tuple[str, ...],
    lookbacks: tuple[int, ...],
    durations: tuple[int, ...],
    spread_fractions: tuple[Decimal, ...],
    run_id_prefix: str = "ecb-edge",
) -> tuple[EdgeCandidate, ...]:
    """Scan strategy configurations on observed ECB ticks and score directionality."""
    if not strategies or not lookbacks or not durations or not spread_fractions:
        raise InvalidEdgeSearch(
            "edge search requires at least one strategy, lookback, duration, and spread"
        )
    if any(type(value) is not int or value < 1 for value in lookbacks):
        raise InvalidEdgeSearch("lookbacks must be positive integers")
    if any(type(value) is not int or value < 1 for value in durations):
        raise InvalidEdgeSearch("durations must be positive integers")

    decision = decide_persistent_use(manifest, require_derived_artifacts=True)
    if decision.decision is not PersistentUseDecision.ALLOW:
        raise UnapprovedEcbSource(
            "ECB source is not approved for persistence: " + ", ".join(decision.reasons)
        )

    batch = load_ecb_batch(text=csv_text, currency=currency, manifest=manifest)
    symbol = f"EUR{currency}"
    candidates: list[EdgeCandidate] = []
    for strategy_name in strategies:
        for lookback in lookbacks:
            for duration in durations:
                for spread in spread_fractions:
                    run_id = f"{run_id_prefix}-{strategy_name}-l{lookback}-d{duration}-s{spread}"
                    split = split_ticks(spec=split_spec, ticks=batch.ticks, run_id=run_id)
                    evaluation = evaluate_split(
                        split=split,
                        evidence_mode=EvidenceMode.QUOTE_REPLAY_BACKTEST,
                        seed=seed,
                        duration=duration,
                        economy=EconomyProvenance.OBSERVED,
                        strategy=_strategy_for(strategy_name, lookback),
                        decision_history=lookback + 1,
                        cost=ExecutionCostModel(spread_fraction=spread),
                        symbol=symbol,
                    )
                    candidates.append(
                        EdgeCandidate(
                            strategy=strategy_name,
                            lookback=lookback,
                            duration=duration,
                            spread_fraction=spread,
                            decisions=evaluation.decisions,
                            hit_rate=evaluation.directional_hit_rate,
                            bootstrap_lower=(
                                None
                                if evaluation.bootstrap_interval is None
                                else evaluation.bootstrap_interval.lower
                            ),
                            bootstrap_upper=(
                                None
                                if evaluation.bootstrap_interval is None
                                else evaluation.bootstrap_interval.upper
                            ),
                            holdout_hash=split.holdout.holdout_hash,
                            run_id=run_id,
                        )
                    )
    return tuple(candidates)
