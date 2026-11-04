"""Walk-forward evaluation over a temporal split."""

from collections.abc import Callable, Sequence
from decimal import Decimal

from devsoul_quant.domain.contracts import ContractAction, EnterContractIntent, NoTradeIntent
from devsoul_quant.domain.costs import ExecutionCostModel, net_outcome
from devsoul_quant.domain.metrics import (
    EvaluationReport,
    EvidenceMode,
    TrialOutcome,
    evaluate,
)
from devsoul_quant.domain.replay import EconomyProvenance, Tick, replay_rise_fall
from devsoul_quant.domain.strategy import momentum_decision
from devsoul_quant.domain.validation import TemporalSplit

StrategyDecision = Callable[..., EnterContractIntent | NoTradeIntent]
DEFAULT_SYMBOL = "SYNTH_OWNED"


def trials_from_ticks(
    *,
    ticks: Sequence[Tick],
    duration: int = 3,
    economy: EconomyProvenance = EconomyProvenance.UNAVAILABLE,
    strategy: StrategyDecision = momentum_decision,
    decision_history: int = 2,
    cost: ExecutionCostModel | None = None,
    symbol: str = DEFAULT_SYMBOL,
) -> tuple[TrialOutcome, ...]:
    """Produce directional trials by sliding a strategy window over ordered ticks."""
    if type(duration) is not int or duration < 1:
        raise ValueError("duration must be a positive integer")
    if type(decision_history) is not int or decision_history < 2:
        raise ValueError("decision_history must be an integer of at least two")
    trials: list[TrialOutcome] = []
    for start in range(0, len(ticks) - decision_history - duration):
        history = ticks[start : start + decision_history]
        decision = strategy(
            history=history,
            duration=duration,
            amount_requested=Decimal("1.00"),
            symbol=symbol,
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
            window = ticks[start + decision_history : start + decision_history + duration + 1]
            result = replay_rise_fall(decision, window, economy=economy)
            outcome = result.outcome
            if cost is not None:
                outcome = net_outcome(
                    entry=result.entry_tick.quote,
                    exit=result.exit_tick.quote,
                    contract_type=decision.contract_type,
                    spread_fraction=cost.spread_fraction,
                )
            trials.append(
                TrialOutcome(
                    decision=ContractAction.ENTER_CONTRACT,
                    outcome=outcome,
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
    strategy: StrategyDecision = momentum_decision,
    decision_history: int = 2,
    cost: ExecutionCostModel | None = None,
    symbol: str = DEFAULT_SYMBOL,
    confidence: Decimal = Decimal("0.95"),
    resamples: int = 200,
) -> EvaluationReport:
    """Evaluate a temporal split fold by fold and aggregate directional evidence."""
    folds = tuple(
        trials_from_ticks(
            ticks=fold.test_ticks,
            duration=duration,
            economy=economy,
            strategy=strategy,
            decision_history=decision_history,
            cost=cost,
            symbol=symbol,
        )
        for fold in split.folds
    )
    return evaluate(
        folds=folds,
        evidence_mode=evidence_mode,
        seed=seed,
        confidence=confidence,
        resamples=resamples,
    )
