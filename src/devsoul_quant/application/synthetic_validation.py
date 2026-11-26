"""Causal walk-forward validation over owned synthetic parity scenarios.

This application layer connects the S1 decision, risk and lifecycle components.
It evaluates only fold test regions and never opens the sealed holdout. Results
are tick-proxy diagnostics with no economic or profitability claim.
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from random import Random

from devsoul_quant.domain.decision import DecisionAction, even_odd_decision
from devsoul_quant.domain.digit_strategy import DigitDecisionPolicy, DigitEconomics, last_digit
from devsoul_quant.domain.probability_scoring import (
    ProbabilityForecast,
    ProbabilityScore,
    score_forecasts,
)
from devsoul_quant.domain.session_risk import (
    SessionRiskDisposition,
    SessionRiskPolicy,
    SessionRiskState,
    apply_settlement,
    assess_entry,
)
from devsoul_quant.domain.session_state import (
    SessionPhase,
    advance_warmup,
    new_machine,
    phase,
)
from devsoul_quant.domain.synthetic_processes import SyntheticScenario, generate_scenario
from devsoul_quant.domain.validation import TemporalSplit, TemporalSplitSpec, split_ticks


class InvalidSyntheticValidation(ValueError):
    """Raised when a synthetic validation configuration is unsafe or malformed."""


@dataclass(frozen=True, slots=True)
class MethodReport:
    """One method's out-of-sample directional and calibration diagnostics."""

    decisions: int
    entries: int
    wins: int
    no_trades: int
    risk_rejections: int
    stopped_folds: int
    hit_rate: Decimal | None
    probability_score: ProbabilityScore


@dataclass(frozen=True, slots=True)
class NoTradeBaselineReport:
    """The abstention baseline, which deliberately emits no forecast or entry."""

    decisions: int
    entries: int = 0


@dataclass(frozen=True, slots=True)
class ParityWalkForwardReport:
    """Non-economic S2 report over the unsealed walk-forward folds."""

    fold_count: int
    strategy: MethodReport
    random_baseline: MethodReport
    no_trade_baseline: NoTradeBaselineReport
    holdout_opened: bool = False
    profitability_claim: bool = False
    economic_metrics_available: bool = False
    evidence_label: str = "OWNED_SYNTHETIC_TICK_PROXY"


@dataclass(frozen=True, slots=True)
class ParityMonteCarloReport:
    """Aggregate stability diagnostics across deterministic synthetic seeds."""

    run_count: int
    strategy_mean_brier: Decimal
    random_mean_brier: Decimal
    strategy_better_brier_runs: int
    strategy_entry_runs: int
    holdouts_opened: int
    runs: tuple[ParityWalkForwardReport, ...]
    profitability_claim: bool = False


@dataclass(slots=True)
class _MethodAccumulator:
    forecasts: list[ProbabilityForecast]
    entries: int = 0
    wins: int = 0
    risk_rejections: int = 0
    stopped_folds: int = 0


def _observed(action: DecisionAction, target_digit: int) -> bool:
    target_is_even = target_digit % 2 == 0
    return target_is_even if action is DecisionAction.EVEN else not target_is_even


def _try_entry(
    *,
    observed: bool,
    state: SessionRiskState,
    policy: SessionRiskPolicy,
) -> tuple[bool, SessionRiskState]:
    verdict, assessed_state = assess_entry(state, policy)
    if verdict.disposition is SessionRiskDisposition.REJECTED:
        return False, assessed_state
    result = Decimal(1) if observed else Decimal(-1)
    return True, apply_settlement(assessed_state, policy, result)


def _method_report(
    accumulator: _MethodAccumulator, *, decisions: int, calibration_bins: int
) -> MethodReport:
    hit_rate = (
        None
        if accumulator.entries == 0
        else Decimal(accumulator.wins) / Decimal(accumulator.entries)
    )
    return MethodReport(
        decisions=decisions,
        entries=accumulator.entries,
        wins=accumulator.wins,
        no_trades=decisions - accumulator.entries,
        risk_rejections=accumulator.risk_rejections,
        stopped_folds=accumulator.stopped_folds,
        hit_rate=hit_rate,
        probability_score=score_forecasts(tuple(accumulator.forecasts), bin_count=calibration_bins),
    )


def run_parity_walk_forward(
    *,
    split: TemporalSplit,
    history_size: int,
    even_economics: DigitEconomics,
    odd_economics: DigitEconomics,
    decision_policy: DigitDecisionPolicy,
    risk_policy: SessionRiskPolicy,
    random_seed: int,
    calibration_bins: int = 10,
) -> ParityWalkForwardReport:
    """Evaluate causal parity forecasts against random and abstention baselines.

    Each fold starts with fresh session risk state. Its first ``history_size``
    test ticks are consumed as warm-up; every later test tick is predicted only
    from the immediately preceding test ticks. The sealed holdout is not accessed.
    """
    if type(history_size) is not int or history_size < decision_policy.min_samples:
        raise InvalidSyntheticValidation("history_size must cover decision_policy.min_samples")
    if type(random_seed) is not int:
        raise InvalidSyntheticValidation("random_seed must be an integer")
    if type(calibration_bins) is not int or calibration_bins < 1:
        raise InvalidSyntheticValidation("calibration_bins must be a positive integer")

    random = Random(random_seed)
    strategy = _MethodAccumulator(forecasts=[])
    baseline = _MethodAccumulator(forecasts=[])
    decisions = 0

    for fold in split.folds:
        strategy_state = SessionRiskState()
        baseline_state = SessionRiskState()
        machine = new_machine(warmup_ticks=history_size)
        prefix = list(fold.test_ticks[:history_size])
        for _ in prefix:
            machine = advance_warmup(machine)
        if phase(machine, strategy_state) is not SessionPhase.RUNNING:
            raise InvalidSyntheticValidation("fold test region cannot complete warm-up")

        for target in fold.test_ticks[history_size:]:
            history = tuple(prefix[-history_size:])
            target_digit = last_digit(target)
            decision = even_odd_decision(
                history=history,
                even_economics=even_economics,
                odd_economics=odd_economics,
                policy=decision_policy,
            )
            forecast_action = decision.forecast_action
            if forecast_action is None or forecast_action not in (
                DecisionAction.EVEN,
                DecisionAction.ODD,
            ):
                raise InvalidSyntheticValidation("parity decision did not emit a forecast action")
            if decision.probability is None:
                raise InvalidSyntheticValidation("parity decision did not emit a probability")

            strategy_observed = _observed(forecast_action, target_digit)
            strategy.forecasts.append(ProbabilityForecast(decision.probability, strategy_observed))
            if decision.action in (DecisionAction.EVEN, DecisionAction.ODD):
                entered, strategy_state = _try_entry(
                    observed=strategy_observed,
                    state=strategy_state,
                    policy=risk_policy,
                )
                if entered:
                    strategy.entries += 1
                    strategy.wins += int(strategy_observed)
                else:
                    strategy.risk_rejections += 1

            random_action = DecisionAction.EVEN if random.randrange(2) == 0 else DecisionAction.ODD
            baseline_observed = _observed(random_action, target_digit)
            baseline.forecasts.append(ProbabilityForecast(Decimal("0.5"), baseline_observed))
            entered, baseline_state = _try_entry(
                observed=baseline_observed,
                state=baseline_state,
                policy=risk_policy,
            )
            if entered:
                baseline.entries += 1
                baseline.wins += int(baseline_observed)
            else:
                baseline.risk_rejections += 1

            decisions += 1
            prefix.append(target)

        strategy.stopped_folds += int(phase(machine, strategy_state) is SessionPhase.STOPPED)
        baseline.stopped_folds += int(phase(machine, baseline_state) is SessionPhase.STOPPED)

    if decisions == 0:
        raise InvalidSyntheticValidation("walk-forward split has no test targets")

    return ParityWalkForwardReport(
        fold_count=len(split.folds),
        strategy=_method_report(strategy, decisions=decisions, calibration_bins=calibration_bins),
        random_baseline=_method_report(
            baseline, decisions=decisions, calibration_bins=calibration_bins
        ),
        no_trade_baseline=NoTradeBaselineReport(decisions=decisions),
        holdout_opened=split.holdout.is_open,
    )


def run_parity_monte_carlo(
    *,
    scenario: SyntheticScenario,
    seeds: tuple[int, ...],
    split_spec: TemporalSplitSpec,
    history_size: int,
    even_economics: DigitEconomics,
    odd_economics: DigitEconomics,
    decision_policy: DigitDecisionPolicy,
    risk_policy: SessionRiskPolicy,
    calibration_bins: int = 10,
) -> ParityMonteCarloReport:
    """Repeat the sealed walk-forward protocol over explicit deterministic seeds."""
    if not seeds or any(type(seed) is not int for seed in seeds):
        raise InvalidSyntheticValidation("seeds must be a non-empty tuple of integers")
    if len(set(seeds)) != len(seeds):
        raise InvalidSyntheticValidation("seeds must be unique")

    runs: list[ParityWalkForwardReport] = []
    for seed in seeds:
        ticks = generate_scenario(replace(scenario, seed=seed))
        split = split_ticks(
            spec=split_spec,
            ticks=ticks,
            run_id=f"synthetic-parity-seed-{seed}",
        )
        runs.append(
            run_parity_walk_forward(
                split=split,
                history_size=history_size,
                even_economics=even_economics,
                odd_economics=odd_economics,
                decision_policy=decision_policy,
                risk_policy=risk_policy,
                random_seed=seed,
                calibration_bins=calibration_bins,
            )
        )

    strategy_mean = sum(
        (run.strategy.probability_score.brier_score for run in runs), Decimal(0)
    ) / Decimal(len(runs))
    random_mean = sum(
        (run.random_baseline.probability_score.brier_score for run in runs), Decimal(0)
    ) / Decimal(len(runs))
    return ParityMonteCarloReport(
        run_count=len(runs),
        strategy_mean_brier=strategy_mean,
        random_mean_brier=random_mean,
        strategy_better_brier_runs=sum(
            run.strategy.probability_score.brier_score
            < run.random_baseline.probability_score.brier_score
            for run in runs
        ),
        strategy_entry_runs=sum(run.strategy.entries > 0 for run in runs),
        holdouts_opened=sum(run.holdout_opened for run in runs),
        runs=tuple(runs),
    )
