"""End-to-end synthetic Multiplier walk-forward validation tests."""

from decimal import Decimal

import pytest

from devsoul_quant.application.multiplier_validation import (
    InvalidMultiplierValidation,
    MultiplierMonteCarloReport,
    MultiplierValidationPolicy,
    run_multiplier_monte_carlo,
    run_multiplier_walk_forward,
)
from devsoul_quant.domain.decision import ReversionPolicy
from devsoul_quant.domain.multiplier_outcomes import DirectionalBarrierPolicy
from devsoul_quant.domain.range_regime import RangePolicy, ReferenceMode
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.session_risk import SessionRiskPolicy
from devsoul_quant.domain.synthetic_processes import SyntheticProcess, SyntheticScenario
from devsoul_quant.domain.validation import (
    SealedHoldout,
    TemporalSplit,
    TemporalSplitSpec,
    WalkForwardFold,
)


def _ticks(start_epoch: int, quotes: list[str]) -> tuple[Tick, ...]:
    return tuple(
        Tick(epoch=start_epoch + index, quote=Decimal(quote), pip_size=4)
        for index, quote in enumerate(quotes)
    )


def _split() -> TemporalSplit:
    train = _ticks(1, ["100", "98", "96", "96.5", "96.2", "96", "97"])
    test = _ticks(20, ["100", "98", "96", "96.5", "96.2", "96", "97"])
    return TemporalSplit(
        spec=TemporalSplitSpec(
            lookback_ticks=6,
            purge_ticks=6,
            embargo_ticks=1,
            test_ticks=7,
            fold_count=1,
            holdout_ticks=1,
        ),
        folds=(WalkForwardFold(index=0, train_ticks=train, test_ticks=test),),
        holdout=SealedHoldout(1, run_id="multiplier-tracer", holdout_hash="sealed"),
    )


def test_walk_forward_estimates_probability_from_train_and_settles_forward() -> None:
    report = run_multiplier_walk_forward(
        split=_split(),
        policy=MultiplierValidationPolicy(
            history_size=6,
            minimum_training_signals=1,
            calibration_bins=2,
        ),
        range_policy=RangePolicy(window=5, reference_mode=ReferenceMode.DISPLACEMENT),
        reversion_policy=ReversionPolicy(
            z_score_threshold=Decimal("1.5"),
            min_deceleration=Decimal("0"),
            min_return_frequency=Decimal("0"),
        ),
        barrier_policy=DirectionalBarrierPolicy(
            target_return=Decimal("0.005"),
            stop_return=Decimal("0.005"),
            maximum_holding_ticks=1,
        ),
        risk_policy=SessionRiskPolicy(Decimal("5"), 3, 2),
        random_seed=41,
    )

    assert report.fold_count == 1
    assert report.training_signal_counts == (1,)
    assert report.strategy.signal_opportunities == 1
    assert report.strategy.entries == 1
    assert report.strategy.targets == 1
    assert report.strategy.probability_score is not None
    assert report.strategy.probability_score.brier_score == Decimal(0)
    assert report.random_baseline.probability_score is not None
    assert report.random_baseline.probability_score.forecast_count == 1
    assert report.random_baseline.probability_score.brier_score == Decimal(0)
    assert report.no_trade_baseline.entries == 0
    assert report.holdout_opened is False
    assert report.profitability_claim is False
    assert report.economic_metrics_available is False


def test_multiplier_monte_carlo_is_deterministic_across_explicit_seeds() -> None:
    def run() -> MultiplierMonteCarloReport:
        return run_multiplier_monte_carlo(
            scenario=SyntheticScenario(
                process=SyntheticProcess.ORNSTEIN_UHLENBECK,
                seed=0,
                count=260,
                volatility=Decimal("0.01"),
                reversion_speed=Decimal("0.15"),
            ),
            seeds=(3, 5, 7),
            split_spec=TemporalSplitSpec(12, 12, 3, 40, 2, 20),
            policy=MultiplierValidationPolicy(12, 2, 5),
            range_policy=RangePolicy(11, ReferenceMode.DISPLACEMENT),
            reversion_policy=ReversionPolicy(Decimal("1"), Decimal("0"), Decimal("0")),
            barrier_policy=DirectionalBarrierPolicy(Decimal("0.00005"), Decimal("0.00005"), 3),
            risk_policy=SessionRiskPolicy(Decimal("10"), 5, 2),
        )

    first = run()
    second = run()

    assert first == second
    assert first.run_count == 3
    assert first.scored_run_count == 3
    assert first.random_mean_brier is not None
    assert Decimal(0) <= first.random_mean_brier <= Decimal(1)
    assert 0 <= first.strategy_better_brier_runs <= 3
    assert first.holdouts_opened == 0
    assert first.profitability_claim is False


def test_walk_forward_rejects_test_fold_that_cannot_complete_warmup() -> None:
    with pytest.raises(InvalidMultiplierValidation, match="warm-up"):
        run_multiplier_walk_forward(
            split=_split(),
            policy=MultiplierValidationPolicy(8, 1, 2),
            range_policy=RangePolicy(5, ReferenceMode.DISPLACEMENT),
            reversion_policy=ReversionPolicy(Decimal("1.5"), Decimal("0"), Decimal("0")),
            barrier_policy=DirectionalBarrierPolicy(Decimal("0.005"), Decimal("0.005"), 1),
            risk_policy=SessionRiskPolicy(Decimal("5"), 3, 2),
            random_seed=41,
        )


def test_walk_forward_abstains_when_training_signal_count_is_insufficient() -> None:
    report = run_multiplier_walk_forward(
        split=_split(),
        policy=MultiplierValidationPolicy(6, 2, 2),
        range_policy=RangePolicy(5, ReferenceMode.DISPLACEMENT),
        reversion_policy=ReversionPolicy(Decimal("1.5"), Decimal("0"), Decimal("0")),
        barrier_policy=DirectionalBarrierPolicy(Decimal("0.005"), Decimal("0.005"), 1),
        risk_policy=SessionRiskPolicy(Decimal("5"), 3, 2),
        random_seed=41,
    )

    assert report.training_signal_counts == (1,)
    assert report.strategy.signal_opportunities == 1
    assert report.strategy.entries == 0
    assert report.strategy.probability_score is None
    assert report.random_baseline.entries == 0
    assert report.random_baseline.probability_score is None
