"""Walk-forward evaluation over a temporal split."""

from collections.abc import Sequence
from decimal import Decimal

from devsoul_quant.domain.contracts import ContractAction, NoTradeIntent
from devsoul_quant.domain.metrics import (
    EvaluationReport,
    EvidenceMode,
    TrialOutcome,
    evaluate,
)
from devsoul_quant.domain.replay import EconomyProvenance, Tick, replay_rise_fall
from devsoul_quant.domain.strategy import momentum_decision
from devsoul_quant.domain.validation import TemporalSplit


def trials_from_ticks(
    *,
    ticks: Sequence[Tick],
    duration: int = 3,
    economy: EconomyProvenance = EconomyProvenance.UNAVAILABLE,
) -> tuple[TrialOutcome, ...]:
    """Produce directional trials by sliding a strategy window over ordered ticks."""
    if type(duration) is not int or duration < 1:
        raise ValueError("duration must be a positive integer")
    trials: list[TrialOutcome] = []
    for start in range(0, len(ticks) - duration - 2):
        history = ticks[start : start + 2]
        decision = momentum_decision(
            history=history,
            duration=duration,
            amount_requested=Decimal("1.00"),
        )
        if isinstance(decision, NoTradeIntent):
            trials.append(
                TrialOutcome(
                    decision=ContractAction.NO_TRADE,
                    outcome=None,
                    provenance=economy,
                )
            )
        else:
            window = ticks[start + 2 : start + duration + 3]
            result = replay_rise_fall(decision, window, economy=economy)
            trials.append(
                TrialOutcome(
                    decision=ContractAction.ENTER_CONTRACT,
                    outcome=result.outcome,
                    provenance=economy,
                )
            )
    return tuple(trials)


def evaluate_split(
    *,
    split: TemporalSplit,
    evidence_mode: EvidenceMode,
    seed: int,
    duration: int = 3,
    economy: EconomyProvenance = EconomyProvenance.UNAVAILABLE,
) -> EvaluationReport:
    """Evaluate a temporal split fold by fold and aggregate directional evidence."""
    folds = tuple(
        trials_from_ticks(ticks=fold.test_ticks, duration=duration, economy=economy)
        for fold in split.folds
    )
    return evaluate(folds=folds, evidence_mode=evidence_mode, seed=seed)
