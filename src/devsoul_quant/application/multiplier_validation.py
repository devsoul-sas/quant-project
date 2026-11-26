"""Causal, non-economic walk-forward validation for Multiplier signals.

Training folds estimate target-before-stop frequency. Test folds use their own
local warm-up, never the stale pre-purge train tail. All outcomes are relative
quote diagnostics over owned synthetic ticks; no contract P&L is inferred.
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from random import Random

from devsoul_quant.domain.decision import (
    DecisionAction,
    ReversionPolicy,
    multiplier_decision,
)
from devsoul_quant.domain.multiplier_outcomes import (
    DirectionalBarrierPolicy,
    DirectionalOutcome,
    DirectionalSettlement,
    settle_directional_outcome,
)
from devsoul_quant.domain.probability_scoring import (
    ProbabilityForecast,
    ProbabilityScore,
    score_forecasts,
)
from devsoul_quant.domain.range_regime import RangePolicy
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.session_risk import (
    SessionRiskDisposition,
    SessionRiskPolicy,
    SessionRiskState,
    apply_settlement,
    assess_entry,
)
from devsoul_quant.domain.session_state import SessionPhase, advance_warmup, new_machine, phase
from devsoul_quant.domain.synthetic_processes import SyntheticScenario, generate_scenario
from devsoul_quant.domain.validation import TemporalSplit, TemporalSplitSpec, split_ticks


class InvalidMultiplierValidation(ValueError):
    """Raised when Multiplier validation cannot preserve causal invariants."""


@dataclass(frozen=True, slots=True)
class MultiplierValidationPolicy:
    """Frozen sample requirements for one validation run."""

    history_size: int
    minimum_training_signals: int
    calibration_bins: int = 10

    def __post_init__(self) -> None:
        for field in ("history_size", "minimum_training_signals", "calibration_bins"):
            value = getattr(self, field)
            if type(value) is not int or value < 1:
                raise InvalidMultiplierValidation(f"{field} must be a positive integer")


@dataclass(frozen=True, slots=True)
class MultiplierMethodReport:
    """Directional target-before-stop diagnostics for one method."""

    signal_opportunities: int
    entries: int
    targets: int
    stops: int
    timeouts: int
    risk_rejections: int
    target_rate: Decimal | None
    probability_score: ProbabilityScore | None


@dataclass(frozen=True, slots=True)
class NoTradeMultiplierReport:
    """Abstention baseline."""

    signal_opportunities: int
    entries: int = 0


@dataclass(frozen=True, slots=True)
class MultiplierWalkForwardReport:
    """Sealed-holdout report over non-economic synthetic folds."""

    fold_count: int
    training_signal_counts: tuple[int, ...]
    strategy: MultiplierMethodReport
    random_baseline: MultiplierMethodReport
    no_trade_baseline: NoTradeMultiplierReport
    holdout_opened: bool = False
    profitability_claim: bool = False
    economic_metrics_available: bool = False
    evidence_label: str = "OWNED_SYNTHETIC_TICK_PROXY"


@dataclass(frozen=True, slots=True)
class MultiplierMonteCarloReport:
    """Aggregate stability diagnostics over explicit synthetic seeds."""

    run_count: int
    scored_run_count: int
    strategy_mean_brier: Decimal | None
    random_mean_brier: Decimal | None
    strategy_better_brier_runs: int
    strategy_entry_runs: int
    holdouts_opened: int
    runs: tuple[MultiplierWalkForwardReport, ...]
    profitability_claim: bool = False


@dataclass(slots=True)
class _Accumulator:
    forecasts: list[ProbabilityForecast]
    signals: int = 0
    entries: int = 0
    targets: int = 0
    stops: int = 0
    timeouts: int = 0
    risk_rejections: int = 0


def _training_settlements(
    ticks: tuple[Tick, ...],
    *,
    policy: MultiplierValidationPolicy,
    range_policy: RangePolicy,
    reversion_policy: ReversionPolicy,
    barrier_policy: DirectionalBarrierPolicy,
    random: Random | None = None,
) -> tuple[DirectionalSettlement, ...]:
    settlements: list[DirectionalSettlement] = []
    cursor = policy.history_size - 1
    last_entry = len(ticks) - barrier_policy.maximum_holding_ticks - 1
    while cursor <= last_entry:
        history = ticks[cursor - policy.history_size + 1 : cursor + 1]
        decision = multiplier_decision(
            history=history,
            range_policy=range_policy,
            reversion_policy=reversion_policy,
        )
        if decision.action in (DecisionAction.MULTUP, DecisionAction.MULTDOWN):
            action = decision.action
            if random is not None:
                action = (
                    DecisionAction.MULTUP if random.randrange(2) == 0 else DecisionAction.MULTDOWN
                )
            settlement = settle_directional_outcome(
                action=action,
                entry_tick=ticks[cursor],
                future_ticks=ticks[cursor + 1 :],
                policy=barrier_policy,
            )
            settlements.append(settlement)
            cursor += barrier_policy.maximum_holding_ticks
        else:
            cursor += 1
    return tuple(settlements)


def _settlement_result(outcome: DirectionalOutcome) -> Decimal:
    if outcome is DirectionalOutcome.TARGET:
        return Decimal(1)
    if outcome is DirectionalOutcome.STOP:
        return Decimal(-1)
    return Decimal(0)


def _record(
    accumulator: _Accumulator,
    settlement: DirectionalSettlement,
    probability: Decimal,
    risk_state: SessionRiskState,
    risk_policy: SessionRiskPolicy,
) -> SessionRiskState:
    observed = settlement.outcome is DirectionalOutcome.TARGET
    accumulator.forecasts.append(ProbabilityForecast(probability, observed))
    verdict, assessed = assess_entry(risk_state, risk_policy)
    if verdict.disposition is SessionRiskDisposition.REJECTED:
        accumulator.risk_rejections += 1
        return assessed
    accumulator.entries += 1
    accumulator.targets += int(settlement.outcome is DirectionalOutcome.TARGET)
    accumulator.stops += int(settlement.outcome is DirectionalOutcome.STOP)
    accumulator.timeouts += int(settlement.outcome is DirectionalOutcome.TIMEOUT)
    return apply_settlement(assessed, risk_policy, _settlement_result(settlement.outcome))


def _report(accumulator: _Accumulator, calibration_bins: int) -> MultiplierMethodReport:
    target_rate = (
        None
        if accumulator.entries == 0
        else Decimal(accumulator.targets) / Decimal(accumulator.entries)
    )
    score = (
        None
        if not accumulator.forecasts
        else score_forecasts(tuple(accumulator.forecasts), bin_count=calibration_bins)
    )
    return MultiplierMethodReport(
        signal_opportunities=accumulator.signals,
        entries=accumulator.entries,
        targets=accumulator.targets,
        stops=accumulator.stops,
        timeouts=accumulator.timeouts,
        risk_rejections=accumulator.risk_rejections,
        target_rate=target_rate,
        probability_score=score,
    )


def run_multiplier_walk_forward(
    *,
    split: TemporalSplit,
    policy: MultiplierValidationPolicy,
    range_policy: RangePolicy,
    reversion_policy: ReversionPolicy,
    barrier_policy: DirectionalBarrierPolicy,
    risk_policy: SessionRiskPolicy,
    random_seed: int,
) -> MultiplierWalkForwardReport:
    """Estimate on train and evaluate causal target-before-stop outcomes on test."""
    if policy.history_size < range_policy.window + 1:
        raise InvalidMultiplierValidation("history_size must cover range window plus one")
    if type(random_seed) is not int:
        raise InvalidMultiplierValidation("random_seed must be an integer")

    random = Random(random_seed)
    strategy = _Accumulator(forecasts=[])
    baseline = _Accumulator(forecasts=[])
    training_counts: list[int] = []

    for fold in split.folds:
        training = _training_settlements(
            fold.train_ticks,
            policy=policy,
            range_policy=range_policy,
            reversion_policy=reversion_policy,
            barrier_policy=barrier_policy,
        )
        baseline_training = _training_settlements(
            fold.train_ticks,
            policy=policy,
            range_policy=range_policy,
            reversion_policy=reversion_policy,
            barrier_policy=barrier_policy,
            random=random,
        )
        training_counts.append(len(training))
        probability = (
            None
            if len(training) < policy.minimum_training_signals
            else Decimal(sum(result.outcome is DirectionalOutcome.TARGET for result in training))
            / Decimal(len(training))
        )
        baseline_probability = (
            None
            if len(baseline_training) < policy.minimum_training_signals
            else Decimal(
                sum(result.outcome is DirectionalOutcome.TARGET for result in baseline_training)
            )
            / Decimal(len(baseline_training))
        )

        strategy_state = SessionRiskState()
        baseline_state = SessionRiskState()
        machine = new_machine(policy.history_size)
        for _ in fold.test_ticks[: policy.history_size]:
            machine = advance_warmup(machine)
        if phase(machine, strategy_state) is not SessionPhase.RUNNING:
            raise InvalidMultiplierValidation("fold test region cannot complete warm-up")

        cursor = policy.history_size - 1
        last_entry = len(fold.test_ticks) - barrier_policy.maximum_holding_ticks - 1
        while cursor <= last_entry:
            history = fold.test_ticks[cursor - policy.history_size + 1 : cursor + 1]
            decision = multiplier_decision(
                history=history,
                range_policy=range_policy,
                reversion_policy=reversion_policy,
            )
            if decision.action not in (DecisionAction.MULTUP, DecisionAction.MULTDOWN):
                cursor += 1
                continue

            strategy.signals += 1
            baseline.signals += 1
            settlement = settle_directional_outcome(
                action=decision.action,
                entry_tick=fold.test_ticks[cursor],
                future_ticks=fold.test_ticks[cursor + 1 :],
                policy=barrier_policy,
            )
            random_action = (
                DecisionAction.MULTUP if random.randrange(2) == 0 else DecisionAction.MULTDOWN
            )
            random_settlement = settle_directional_outcome(
                action=random_action,
                entry_tick=fold.test_ticks[cursor],
                future_ticks=fold.test_ticks[cursor + 1 :],
                policy=barrier_policy,
            )
            if probability is not None:
                strategy_state = _record(
                    strategy, settlement, probability, strategy_state, risk_policy
                )
            if baseline_probability is not None:
                baseline_state = _record(
                    baseline,
                    random_settlement,
                    baseline_probability,
                    baseline_state,
                    risk_policy,
                )
            cursor += barrier_policy.maximum_holding_ticks

    opportunities = strategy.signals
    return MultiplierWalkForwardReport(
        fold_count=len(split.folds),
        training_signal_counts=tuple(training_counts),
        strategy=_report(strategy, policy.calibration_bins),
        random_baseline=_report(baseline, policy.calibration_bins),
        no_trade_baseline=NoTradeMultiplierReport(opportunities),
        holdout_opened=split.holdout.is_open,
    )


def run_multiplier_monte_carlo(
    *,
    scenario: SyntheticScenario,
    seeds: tuple[int, ...],
    split_spec: TemporalSplitSpec,
    policy: MultiplierValidationPolicy,
    range_policy: RangePolicy,
    reversion_policy: ReversionPolicy,
    barrier_policy: DirectionalBarrierPolicy,
    risk_policy: SessionRiskPolicy,
) -> MultiplierMonteCarloReport:
    """Run the frozen Multiplier protocol across every explicit seed."""
    if not seeds or any(type(seed) is not int for seed in seeds):
        raise InvalidMultiplierValidation("seeds must be a non-empty tuple of integers")
    if len(set(seeds)) != len(seeds):
        raise InvalidMultiplierValidation("seeds must be unique")

    runs: list[MultiplierWalkForwardReport] = []
    for seed in seeds:
        ticks = generate_scenario(replace(scenario, seed=seed))
        split = split_ticks(
            spec=split_spec,
            ticks=ticks,
            run_id=f"synthetic-multiplier-seed-{seed}",
        )
        runs.append(
            run_multiplier_walk_forward(
                split=split,
                policy=policy,
                range_policy=range_policy,
                reversion_policy=reversion_policy,
                barrier_policy=barrier_policy,
                risk_policy=risk_policy,
                random_seed=seed,
            )
        )

    scored = tuple(
        run
        for run in runs
        if run.strategy.probability_score is not None
        and run.random_baseline.probability_score is not None
    )
    strategy_mean = (
        None
        if not scored
        else sum(
            (
                run.strategy.probability_score.brier_score
                for run in scored
                if run.strategy.probability_score is not None
            ),
            Decimal(0),
        )
        / Decimal(len(scored))
    )
    random_mean = (
        None
        if not scored
        else sum(
            (
                run.random_baseline.probability_score.brier_score
                for run in scored
                if run.random_baseline.probability_score is not None
            ),
            Decimal(0),
        )
        / Decimal(len(scored))
    )
    better_runs = 0
    for run in scored:
        strategy_score = run.strategy.probability_score
        random_score = run.random_baseline.probability_score
        assert strategy_score is not None and random_score is not None
        better_runs += int(strategy_score.brier_score < random_score.brier_score)

    return MultiplierMonteCarloReport(
        run_count=len(runs),
        scored_run_count=len(scored),
        strategy_mean_brier=strategy_mean,
        random_mean_brier=random_mean,
        strategy_better_brier_runs=better_runs,
        strategy_entry_runs=sum(run.strategy.entries > 0 for run in runs),
        holdouts_opened=sum(run.holdout_opened for run in runs),
        runs=tuple(runs),
    )
