"""One frozen confirmatory EURGBP experiment over Federal Reserve H.10."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import partial

from devsoul_quant.adapters.federal_reserve.ingest import load_fed_h10_eurgbp_batch
from devsoul_quant.application.evaluate import evaluate_split
from devsoul_quant.application.ports.market_data import MarketDataBatch
from devsoul_quant.domain.costs import ExecutionCostModel
from devsoul_quant.domain.data_rights import (
    DataRightsManifest,
    PersistentUseDecision,
    decide_persistent_use,
)
from devsoul_quant.domain.metrics import EvaluationReport, EvidenceMode
from devsoul_quant.domain.replay import EconomyProvenance
from devsoul_quant.domain.strategy import mean_reversion_decision
from devsoul_quant.domain.validation import TemporalSplit, TemporalSplitSpec, split_ticks

CONFIRMATORY_LOOKBACK = 10
CONFIRMATORY_DURATION = 5
CONFIRMATORY_SPREAD = Decimal("0.0001")
CONFIRMATORY_SEED = 42
CONFIRMATORY_RUN_ID = "fed-h10-eurgbp-confirmatory-v1"
CONFIRMATORY_SPLIT = TemporalSplitSpec(
    lookback_ticks=20,
    purge_ticks=20,
    embargo_ticks=5,
    test_ticks=252,
    fold_count=5,
    holdout_ticks=252,
)
CONFIRMATORY_SPREADS = (
    Decimal("0"),
    Decimal("0.0001"),
    Decimal("0.0002"),
    Decimal("0.0005"),
    Decimal("0.001"),
)


class UnapprovedFedH10Source(ValueError):
    """Raised when the H.10 manifest does not permit derived persistence."""


@dataclass(frozen=True, slots=True)
class FedH10ConfirmationResult:
    """Frozen confirmation evidence; the final holdout remains sealed."""

    data_source: str
    symbol: str
    tick_count: int
    lookback: int
    duration: int
    spread_fraction: Decimal
    holdout_hash: str
    holdout_tick_count: int
    holdout_opened: bool
    evaluation: EvaluationReport

    @property
    def confirms_directional_signal(self) -> bool:
        """Whether the pre-registered 95% lower bound exceeds coin-flip."""
        interval = self.evaluation.bootstrap_interval
        return interval is not None and interval.lower > Decimal("0.50")


@dataclass(frozen=True, slots=True)
class CostSensitivityPoint:
    """One net-of-friction score along the frozen friction ladder."""

    spread_fraction: Decimal
    hit_rate: Decimal | None
    bootstrap_lower: Decimal | None
    bootstrap_upper: Decimal | None

    @property
    def confirms(self) -> bool:
        """Whether the 95% lower bound exceeds coin-flip at this friction level."""
        return self.bootstrap_lower is not None and self.bootstrap_lower > Decimal("0.50")


def _frozen_setup(
    *,
    usd_per_eur_html: str,
    usd_per_gbp_html: str,
    manifest: DataRightsManifest,
) -> tuple[MarketDataBatch, TemporalSplit]:
    decision = decide_persistent_use(manifest, require_derived_artifacts=True)
    if decision.decision is not PersistentUseDecision.ALLOW:
        raise UnapprovedFedH10Source(
            "Federal Reserve H.10 source is not approved for persistence: "
            + ", ".join(decision.reasons)
        )
    batch = load_fed_h10_eurgbp_batch(
        usd_per_eur_html=usd_per_eur_html,
        usd_per_gbp_html=usd_per_gbp_html,
        manifest=manifest,
    )
    split = split_ticks(spec=CONFIRMATORY_SPLIT, ticks=batch.ticks, run_id=CONFIRMATORY_RUN_ID)
    return batch, split


def _evaluate_at_spread(split: TemporalSplit, *, spread: Decimal) -> EvaluationReport:
    return evaluate_split(
        split=split,
        evidence_mode=EvidenceMode.QUOTE_REPLAY_BACKTEST,
        seed=CONFIRMATORY_SEED,
        duration=CONFIRMATORY_DURATION,
        economy=EconomyProvenance.OBSERVED,
        strategy=partial(mean_reversion_decision, lookback=CONFIRMATORY_LOOKBACK),
        decision_history=CONFIRMATORY_LOOKBACK + 1,
        cost=ExecutionCostModel(spread_fraction=spread),
        symbol="EURGBP",
    )


def run_fed_h10_eurgbp_confirmation(
    *,
    usd_per_eur_html: str,
    usd_per_gbp_html: str,
    manifest: DataRightsManifest,
) -> FedH10ConfirmationResult:
    """Run the single pre-registered EURGBP hypothesis without opening holdout."""
    batch, split = _frozen_setup(
        usd_per_eur_html=usd_per_eur_html,
        usd_per_gbp_html=usd_per_gbp_html,
        manifest=manifest,
    )
    evaluation = _evaluate_at_spread(split, spread=CONFIRMATORY_SPREAD)
    return FedH10ConfirmationResult(
        data_source=batch.source,
        symbol="EURGBP",
        tick_count=len(batch.ticks),
        lookback=CONFIRMATORY_LOOKBACK,
        duration=CONFIRMATORY_DURATION,
        spread_fraction=CONFIRMATORY_SPREAD,
        holdout_hash=split.holdout.holdout_hash,
        holdout_tick_count=split.holdout.tick_count,
        holdout_opened=split.holdout.is_open,
        evaluation=evaluation,
    )


def run_fed_h10_eurgbp_sensitivity(
    *,
    usd_per_eur_html: str,
    usd_per_gbp_html: str,
    manifest: DataRightsManifest,
) -> tuple[CostSensitivityPoint, ...]:
    """Score the frozen hypothesis across the frozen friction ladder without opening holdout."""
    _, split = _frozen_setup(
        usd_per_eur_html=usd_per_eur_html,
        usd_per_gbp_html=usd_per_gbp_html,
        manifest=manifest,
    )
    points: list[CostSensitivityPoint] = []
    for spread in CONFIRMATORY_SPREADS:
        report = _evaluate_at_spread(split, spread=spread)
        interval = report.bootstrap_interval
        points.append(
            CostSensitivityPoint(
                spread_fraction=spread,
                hit_rate=report.directional_hit_rate,
                bootstrap_lower=interval.lower if interval else None,
                bootstrap_upper=interval.upper if interval else None,
            )
        )
    return tuple(points)
