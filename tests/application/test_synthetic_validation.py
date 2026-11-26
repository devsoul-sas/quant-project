"""End-to-end synthetic walk-forward validation tests."""

from decimal import Decimal

import pytest

from devsoul_quant.application.synthetic_validation import (
    InvalidSyntheticValidation,
    ParityMonteCarloReport,
    ParityWalkForwardReport,
    run_parity_monte_carlo,
    run_parity_walk_forward,
)
from devsoul_quant.domain.digit_strategy import DigitDecisionPolicy, DigitEconomics
from devsoul_quant.domain.session_risk import SessionRiskPolicy
from devsoul_quant.domain.synthetic_processes import (
    SyntheticProcess,
    SyntheticScenario,
    generate_scenario,
)
from devsoul_quant.domain.validation import TemporalSplit, TemporalSplitSpec, split_ticks


def _split() -> TemporalSplit:
    ticks = generate_scenario(
        SyntheticScenario(
            process=SyntheticProcess.UNIFORM_DIGIT,
            seed=17,
            count=180,
            pip_size=4,
        )
    )
    return split_ticks(
        spec=TemporalSplitSpec(
            lookback_ticks=20,
            purge_ticks=20,
            embargo_ticks=5,
            test_ticks=30,
            fold_count=3,
            holdout_ticks=20,
        ),
        ticks=ticks,
        run_id="s2-uniform-17",
    )


def _run() -> ParityWalkForwardReport:
    return run_parity_walk_forward(
        split=_split(),
        history_size=20,
        even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("2")),
        odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("2")),
        decision_policy=DigitDecisionPolicy(
            min_samples=20,
            z_score=Decimal("1.96"),
            min_edge_probability=Decimal("0"),
        ),
        risk_policy=SessionRiskPolicy(
            max_drawdown=Decimal("5"),
            max_consecutive_losses=3,
            cooldown_decisions=2,
        ),
        random_seed=71,
        calibration_bins=5,
    )


def test_walk_forward_is_deterministic_and_keeps_holdout_sealed() -> None:
    split = _split()
    first = run_parity_walk_forward(
        split=split,
        history_size=20,
        even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("2")),
        odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("2")),
        decision_policy=DigitDecisionPolicy(20, Decimal("1.96"), Decimal("0")),
        risk_policy=SessionRiskPolicy(Decimal("5"), 3, 2),
        random_seed=71,
        calibration_bins=5,
    )
    second = run_parity_walk_forward(
        split=split,
        history_size=20,
        even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("2")),
        odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("2")),
        decision_policy=DigitDecisionPolicy(20, Decimal("1.96"), Decimal("0")),
        risk_policy=SessionRiskPolicy(Decimal("5"), 3, 2),
        random_seed=71,
        calibration_bins=5,
    )

    assert first == second
    assert split.holdout.is_open is False
    assert first.holdout_opened is False
    assert first.profitability_claim is False


def test_walk_forward_uses_each_test_fold_warmup_before_forward_scoring() -> None:
    report = _run()

    assert report.fold_count == 3
    assert report.strategy.decisions == 30
    assert report.strategy.probability_score.forecast_count == 30
    assert report.random_baseline.decisions == 30
    assert report.no_trade_baseline.decisions == 30


def test_random_baseline_has_exact_coin_flip_brier_score() -> None:
    report = _run()

    assert report.random_baseline.probability_score.brier_score == Decimal("0.25")
    assert report.no_trade_baseline.entries == 0


def test_report_is_explicitly_non_economic() -> None:
    report = _run()

    assert report.economic_metrics_available is False
    assert report.evidence_label == "OWNED_SYNTHETIC_TICK_PROXY"


def test_monte_carlo_is_deterministic_and_compares_brier_against_random() -> None:
    scenario = SyntheticScenario(
        process=SyntheticProcess.UNIFORM_DIGIT,
        seed=0,
        count=180,
        pip_size=4,
    )
    split_spec = TemporalSplitSpec(
        lookback_ticks=20,
        purge_ticks=20,
        embargo_ticks=5,
        test_ticks=30,
        fold_count=3,
        holdout_ticks=20,
    )

    def run() -> ParityMonteCarloReport:
        return run_parity_monte_carlo(
            scenario=scenario,
            seeds=(3, 5, 7),
            split_spec=split_spec,
            history_size=20,
            even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("2")),
            odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("2")),
            decision_policy=DigitDecisionPolicy(20, Decimal("1.96"), Decimal("0")),
            risk_policy=SessionRiskPolicy(Decimal("5"), 3, 2),
            calibration_bins=5,
        )

    first = run()
    second = run()

    assert first == second
    assert first.run_count == 3
    assert first.random_mean_brier == Decimal("0.25")
    assert 0 <= first.strategy_better_brier_runs <= 3
    assert first.holdouts_opened == 0
    assert first.profitability_claim is False


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"history_size": 19}, "history_size"),
        ({"random_seed": True}, "random_seed"),
        ({"calibration_bins": 0}, "calibration_bins"),
    ],
)
def test_walk_forward_rejects_invalid_configuration(
    overrides: dict[str, object], message: str
) -> None:
    kwargs: dict[str, object] = {
        "split": _split(),
        "history_size": 20,
        "even_economics": DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("2")),
        "odd_economics": DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("2")),
        "decision_policy": DigitDecisionPolicy(20, Decimal("1.96"), Decimal("0")),
        "risk_policy": SessionRiskPolicy(Decimal("5"), 3, 2),
        "random_seed": 71,
        "calibration_bins": 5,
    }
    kwargs.update(overrides)

    with pytest.raises(InvalidSyntheticValidation, match=message):
        run_parity_walk_forward(**kwargs)  # type: ignore[arg-type]


def test_walk_forward_rejects_fold_that_cannot_complete_warmup() -> None:
    with pytest.raises(InvalidSyntheticValidation, match="warm-up"):
        run_parity_walk_forward(
            split=_split(),
            history_size=31,
            even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("2")),
            odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("2")),
            decision_policy=DigitDecisionPolicy(20, Decimal("1.96"), Decimal("0")),
            risk_policy=SessionRiskPolicy(Decimal("5"), 3, 2),
            random_seed=71,
        )


def test_walk_forward_rejects_fold_with_warmup_but_no_forward_target() -> None:
    with pytest.raises(InvalidSyntheticValidation, match="no test targets"):
        run_parity_walk_forward(
            split=_split(),
            history_size=30,
            even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("2")),
            odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("2")),
            decision_policy=DigitDecisionPolicy(20, Decimal("1.96"), Decimal("0")),
            risk_policy=SessionRiskPolicy(Decimal("5"), 3, 2),
            random_seed=71,
        )


@pytest.mark.parametrize("seeds", [(), (1, 1), (1, "x")])
def test_monte_carlo_rejects_invalid_seed_sets(seeds: tuple[object, ...]) -> None:
    with pytest.raises(InvalidSyntheticValidation, match="seeds"):
        run_parity_monte_carlo(
            scenario=SyntheticScenario(
                process=SyntheticProcess.UNIFORM_DIGIT,
                seed=0,
                count=180,
                pip_size=4,
            ),
            seeds=seeds,  # type: ignore[arg-type]
            split_spec=TemporalSplitSpec(20, 20, 5, 30, 3, 20),
            history_size=20,
            even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("2")),
            odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("2")),
            decision_policy=DigitDecisionPolicy(20, Decimal("1.96"), Decimal("0")),
            risk_policy=SessionRiskPolicy(Decimal("5"), 3, 2),
        )
