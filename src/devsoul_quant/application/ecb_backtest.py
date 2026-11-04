"""Daily QUOTE_REPLAY backtest over observed ECB euro reference rates."""

from __future__ import annotations

from dataclasses import dataclass

from devsoul_quant.adapters.ecb.ingest import load_ecb_batch
from devsoul_quant.application.evaluate import StrategyDecision, evaluate_split
from devsoul_quant.domain.costs import ExecutionCostModel
from devsoul_quant.domain.data_rights import (
    DataRightsManifest,
    PersistentUseDecision,
    decide_persistent_use,
)
from devsoul_quant.domain.metrics import EvaluationReport, EvidenceMode
from devsoul_quant.domain.replay import EconomyProvenance
from devsoul_quant.domain.strategy import momentum_decision
from devsoul_quant.domain.validation import TemporalSplitSpec, split_ticks


class UnapprovedEcbSource(ValueError):
    """Raised when the ECB manifest is not approved for persistence."""


@dataclass(frozen=True, slots=True)
class EcbDailyBacktestResult:
    """Observed-data backtest report plus the sealed holdout commitment."""

    data_source: str
    symbol: str
    tick_count: int
    holdout_hash: str
    holdout_tick_count: int
    evaluation: EvaluationReport


def run_ecb_daily_backtest(
    *,
    csv_text: str,
    currency: str,
    manifest: DataRightsManifest,
    split: TemporalSplitSpec,
    duration: int = 5,
    seed: int = 42,
    run_id: str = "ecb-daily",
    strategy: StrategyDecision = momentum_decision,
    decision_history: int = 2,
    cost: ExecutionCostModel | None = None,
) -> EcbDailyBacktestResult:
    """Run a daily quote-replay backtest over observed ECB reference rates.

    The pipeline fails closed on the ECB data-rights manifest before touching
    any data, then splits the observed ticks into walk-forward folds with a
    sealed holdout and evaluates them under QUOTE_REPLAY_BACKTEST provenance.
    """
    decision = decide_persistent_use(manifest, require_derived_artifacts=True)
    if decision.decision is not PersistentUseDecision.ALLOW:
        raise UnapprovedEcbSource(
            "ECB source is not approved for persistence: " + ", ".join(decision.reasons)
        )

    batch = load_ecb_batch(text=csv_text, currency=currency, manifest=manifest)
    symbol = f"EUR{currency}"
    split_result = split_ticks(spec=split, ticks=batch.ticks, run_id=run_id)
    evaluation = evaluate_split(
        split=split_result,
        evidence_mode=EvidenceMode.QUOTE_REPLAY_BACKTEST,
        seed=seed,
        duration=duration,
        economy=EconomyProvenance.OBSERVED,
        strategy=strategy,
        decision_history=decision_history,
        cost=cost,
        symbol=symbol,
    )
    return EcbDailyBacktestResult(
        data_source="ecb",
        symbol=symbol,
        tick_count=len(batch.ticks),
        holdout_hash=split_result.holdout.holdout_hash,
        holdout_tick_count=split_result.holdout.tick_count,
        evaluation=evaluation,
    )
