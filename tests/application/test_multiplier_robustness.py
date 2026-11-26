"""Tests for the preregistered Multiplier robustness gate."""

from decimal import Decimal

import pytest

import devsoul_quant.application.multiplier_robustness as robustness_module
from devsoul_quant.application.multiplier_robustness import (
    InvalidMultiplierRobustness,
    MultiplierRobustnessDecision,
    ProcessRobustnessSummary,
    SensitivityRobustnessSummary,
    evaluate_multiplier_robustness,
    frozen_multiplier_robustness_protocol,
    run_frozen_multiplier_robustness,
    summarize_process_robustness,
)
from devsoul_quant.application.multiplier_validation import (
    MultiplierMethodReport,
    MultiplierMonteCarloReport,
    MultiplierWalkForwardReport,
    NoTradeMultiplierReport,
)
from devsoul_quant.domain.probability_scoring import ProbabilityScore
from devsoul_quant.domain.robustness_statistics import PairedBootstrapSummary
from devsoul_quant.domain.synthetic_processes import SyntheticProcess


def _paired(
    mean: str,
    lower: str,
    upper: str,
    negative_count: int,
    *,
    sample_count: int = 40,
) -> PairedBootstrapSummary:
    return PairedBootstrapSummary(
        sample_count=sample_count,
        mean_difference=Decimal(mean),
        lower_bound=Decimal(lower),
        upper_bound=Decimal(upper),
        negative_count=negative_count,
        tie_count=0,
        positive_count=sample_count - negative_count,
    )


def _process(
    process: SyntheticProcess,
    paired: PairedBootstrapSummary,
    *,
    strategy_target_rate: str = "0.6",
    random_target_rate: str = "0.5",
) -> ProcessRobustnessSummary:
    return ProcessRobustnessSummary(
        process=process,
        paired_brier=paired,
        run_count=40,
        scored_run_count=40,
        strategy_target_rate=Decimal(strategy_target_rate),
        random_target_rate=Decimal(random_target_rate),
        holdouts_opened=0,
        profitability_claim=False,
    )


def _passing_primary() -> tuple[ProcessRobustnessSummary, ...]:
    return (
        _process(
            SyntheticProcess.ORNSTEIN_UHLENBECK,
            _paired("-0.02", "-0.03", "-0.01", 31),
        ),
        _process(
            SyntheticProcess.RANDOM_WALK,
            _paired("0.001", "-0.01", "0.01", 19),
            strategy_target_rate="0.5",
            random_target_rate="0.5",
        ),
        _process(
            SyntheticProcess.GBM,
            _paired("-0.001", "-0.01", "0.01", 22),
        ),
        _process(
            SyntheticProcess.VOLATILITY_REGIME,
            _paired("-0.002", "-0.01", "0.005", 23),
        ),
    )


def _passing_sensitivity() -> tuple[SensitivityRobustnessSummary, ...]:
    return tuple(
        SensitivityRobustnessSummary(
            name=f"cell-{index}",
            paired_brier=_paired("-0.01", "-0.02", "-0.001", 25),
            holdouts_opened=0,
        )
        for index in range(5)
    )


def _method(*, brier: str | None, target: bool, entries: int = 1) -> MultiplierMethodReport:
    score = None if brier is None else ProbabilityScore(1, Decimal(brier), Decimal(0), ())
    targets = int(target) if entries else 0
    return MultiplierMethodReport(
        signal_opportunities=1,
        entries=entries,
        targets=targets,
        stops=entries - targets,
        timeouts=0,
        risk_rejections=0,
        target_rate=None if entries == 0 else Decimal(targets) / Decimal(entries),
        probability_score=score,
    )


def _monte_carlo_report(
    *, run_count: int = 40, with_scores: bool = True, entries: int = 1
) -> MultiplierMonteCarloReport:
    runs = tuple(
        MultiplierWalkForwardReport(
            fold_count=1,
            training_signal_counts=(1,),
            strategy=_method(
                brier="0.1" if with_scores else None,
                target=True,
                entries=entries,
            ),
            random_baseline=_method(
                brier="0.2" if with_scores else None,
                target=False,
                entries=entries,
            ),
            no_trade_baseline=NoTradeMultiplierReport(1),
        )
        for _ in range(run_count)
    )
    return MultiplierMonteCarloReport(
        run_count=run_count,
        scored_run_count=run_count if with_scores else 0,
        strategy_mean_brier=Decimal("0.1") if with_scores else None,
        random_mean_brier=Decimal("0.2") if with_scores else None,
        strategy_better_brier_runs=run_count if with_scores else 0,
        strategy_entry_runs=run_count if entries else 0,
        holdouts_opened=0,
        runs=runs,
    )


def test_frozen_protocol_keeps_development_and_holdout_seed_cohorts_separate() -> None:
    protocol = frozen_multiplier_robustness_protocol()

    assert protocol.development_seeds == tuple(range(21, 61))
    assert protocol.reserved_holdout_seeds == tuple(range(61, 81))
    assert protocol.bootstrap_resamples == 5_000
    assert protocol.bootstrap_seed == 20_261_123
    assert len(protocol.sensitivity) == 5
    assert protocol.primary_barrier in tuple(cell.barrier for cell in protocol.sensitivity)


def test_gate_passes_only_when_all_preregistered_criteria_pass() -> None:
    report = evaluate_multiplier_robustness(
        primary=_passing_primary(),
        sensitivity=_passing_sensitivity(),
    )

    assert report.decision is MultiplierRobustnessDecision.ROBUSTNESS_GATE_PASSED
    assert report.passed is True
    assert all(check.passed for check in report.checks)
    assert report.holdout_opened is False


def test_gate_returns_no_edge_when_primary_ou_is_not_confirmed() -> None:
    primary = list(_passing_primary())
    primary[0] = _process(
        SyntheticProcess.ORNSTEIN_UHLENBECK,
        _paired("0.001", "-0.01", "0.02", 20),
    )

    report = evaluate_multiplier_robustness(
        primary=tuple(primary),
        sensitivity=_passing_sensitivity(),
    )

    assert report.decision is MultiplierRobustnessDecision.NO_EDGE
    assert report.passed is False
    assert report.holdout_opened is False


def test_gate_keeps_holdout_sealed_when_sensitivity_is_unstable() -> None:
    sensitivity = list(_passing_sensitivity())
    sensitivity[0] = SensitivityRobustnessSummary(
        name="fragile",
        paired_brier=_paired("0.02", "0.01", "0.03", 10),
        holdouts_opened=0,
    )
    sensitivity[1] = sensitivity[0]

    report = evaluate_multiplier_robustness(
        primary=_passing_primary(),
        sensitivity=tuple(sensitivity),
    )

    assert report.decision is MultiplierRobustnessDecision.INSUFFICIENT_SYNTHETIC_STABILITY
    assert report.passed is False
    assert report.holdout_opened is False


def test_process_summary_uses_only_paired_scores_and_aggregate_target_rates() -> None:
    summary = summarize_process_robustness(
        process=SyntheticProcess.ORNSTEIN_UHLENBECK,
        report=_monte_carlo_report(run_count=2),
        confidence=Decimal("0.95"),
        resamples=100,
        seed=7,
    )

    assert summary.paired_brier.mean_difference == Decimal("-0.1")
    assert summary.paired_brier.sample_count == 2
    assert summary.strategy_target_rate == Decimal(1)
    assert summary.random_target_rate == Decimal(0)


def test_process_summary_handles_zero_entries_and_rejects_unscored_reports() -> None:
    zero_entry = summarize_process_robustness(
        process=SyntheticProcess.RANDOM_WALK,
        report=_monte_carlo_report(run_count=2, entries=0),
        confidence=Decimal("0.95"),
        resamples=100,
        seed=7,
    )
    assert zero_entry.strategy_target_rate is None
    assert zero_entry.random_target_rate is None

    with pytest.raises(InvalidMultiplierRobustness, match="paired scored"):
        summarize_process_robustness(
            process=SyntheticProcess.RANDOM_WALK,
            report=_monte_carlo_report(run_count=2, with_scores=False),
            confidence=Decimal("0.95"),
            resamples=100,
            seed=7,
        )


def test_gate_rejects_missing_primary_process() -> None:
    with pytest.raises(InvalidMultiplierRobustness, match="each synthetic process"):
        evaluate_multiplier_robustness(
            primary=_passing_primary()[:-1],
            sensitivity=_passing_sensitivity(),
        )


def test_frozen_runner_never_generates_reserved_holdout_seeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_monte_carlo(**kwargs: object) -> MultiplierMonteCarloReport:
        calls.append(kwargs)
        return _monte_carlo_report()

    monkeypatch.setattr(
        robustness_module,
        "run_multiplier_monte_carlo",
        fake_monte_carlo,
    )

    report = run_frozen_multiplier_robustness()

    assert len(calls) == 8
    assert report.holdout_opened is False
    assert all(call["seeds"] == tuple(range(21, 61)) for call in calls)
    for call in calls:
        seeds = call["seeds"]
        assert isinstance(seeds, tuple)
        assert not set(seeds).intersection(range(61, 81))
