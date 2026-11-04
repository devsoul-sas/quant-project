"""Evidence-graded evaluation metrics tests."""

import json
from decimal import Decimal

import pytest

from devsoul_quant.domain.contracts import ContractAction
from devsoul_quant.domain.metrics import (
    EvaluationReport,
    EvidenceMode,
    InvalidEvaluation,
    PromotionEligibility,
    TrialOutcome,
    evaluate,
    promotion_eligibility,
)
from devsoul_quant.domain.replay import EconomyProvenance, Outcome


def _enter(outcome: Outcome) -> TrialOutcome:
    return TrialOutcome(decision=ContractAction.ENTER_CONTRACT, outcome=outcome)


def _wait() -> TrialOutcome:
    return TrialOutcome(decision=ContractAction.NO_TRADE, outcome=None)


def test_tick_proxy_cannot_produce_economic_metrics() -> None:
    report = evaluate(
        folds=((_enter(Outcome.WIN), _enter(Outcome.LOSS), _wait()),),
        evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST,
        seed=1,
    )

    for field in ("expected_value", "roi", "profit", "payout"):
        assert not hasattr(report, field)
    assert report.economic_metrics_available is False
    assert report.promotion_eligibility is PromotionEligibility.NOT_ELIGIBLE


def test_promotion_matrix_denies_tick_proxy() -> None:
    assert (
        promotion_eligibility(EvidenceMode.TICK_PROXY_BACKTEST) is PromotionEligibility.NOT_ELIGIBLE
    )


def test_rejects_empty_samples() -> None:
    with pytest.raises(InvalidEvaluation):
        evaluate(folds=(), evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST, seed=1)
    with pytest.raises(InvalidEvaluation):
        evaluate(folds=((),), evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST, seed=1)


def test_rejects_malformed_outcomes() -> None:
    with pytest.raises(InvalidEvaluation):
        TrialOutcome(decision=ContractAction.ENTER_CONTRACT, outcome=None)
    with pytest.raises(InvalidEvaluation):
        TrialOutcome(decision=ContractAction.NO_TRADE, outcome=Outcome.WIN)


def test_rejects_mixed_provenance() -> None:
    observed = TrialOutcome(
        decision=ContractAction.ENTER_CONTRACT,
        outcome=Outcome.WIN,
        provenance=EconomyProvenance.OBSERVED,
    )
    trials = (_enter(Outcome.WIN), observed)

    with pytest.raises(InvalidEvaluation, match="mixed"):
        evaluate(
            folds=(trials,),
            evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST,
            seed=1,
        )


def test_rejects_observed_economics_in_tick_proxy() -> None:
    observed = TrialOutcome(
        decision=ContractAction.ENTER_CONTRACT,
        outcome=Outcome.WIN,
        provenance=EconomyProvenance.OBSERVED,
    )

    with pytest.raises(InvalidEvaluation, match="observed"):
        evaluate(
            folds=((observed,),),
            evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST,
            seed=1,
        )


def test_quote_replay_accepts_observed_economics() -> None:
    trials = (
        TrialOutcome(
            decision=ContractAction.ENTER_CONTRACT,
            outcome=Outcome.WIN,
            provenance=EconomyProvenance.OBSERVED,
        ),
        TrialOutcome(
            decision=ContractAction.ENTER_CONTRACT,
            outcome=Outcome.LOSS,
            provenance=EconomyProvenance.OBSERVED,
        ),
    )
    report = evaluate(
        folds=(trials,),
        evidence_mode=EvidenceMode.QUOTE_REPLAY_BACKTEST,
        seed=1,
    )

    assert report.evidence_mode is EvidenceMode.QUOTE_REPLAY_BACKTEST
    assert report.promotion_eligibility is PromotionEligibility.NOT_ELIGIBLE
    assert report.economic_metrics_available is False


def test_quote_replay_rejects_unavailable_economics() -> None:
    with pytest.raises(InvalidEvaluation, match="observed"):
        evaluate(
            folds=((_enter(Outcome.WIN),),),
            evidence_mode=EvidenceMode.QUOTE_REPLAY_BACKTEST,
            seed=1,
        )


def test_promotion_matrix_denies_quote_replay() -> None:
    assert (
        promotion_eligibility(EvidenceMode.QUOTE_REPLAY_BACKTEST)
        is PromotionEligibility.NOT_ELIGIBLE
    )


def test_counts_hit_rate_and_loss_streak() -> None:
    report = evaluate(
        folds=((_enter(Outcome.WIN), _enter(Outcome.LOSS), _enter(Outcome.LOSS), _wait()),),
        evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST,
        seed=1,
    )

    assert report.decisions == 4
    assert report.enter_count == 3
    assert report.wait_count == 1
    assert report.wait_rate == Decimal("0.2500")
    assert report.directional_hit_rate == Decimal("0.3333")
    assert report.longest_loss_streak == 2


def test_block_bootstrap_is_deterministic() -> None:
    trials = (_enter(Outcome.WIN), _enter(Outcome.LOSS), _enter(Outcome.WIN), _enter(Outcome.WIN))

    first = evaluate(folds=(trials,), evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST, seed=7)
    second = evaluate(folds=(trials,), evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST, seed=7)

    assert first.bootstrap_interval == second.bootstrap_interval
    assert first.bootstrap_interval is not None
    assert first.bootstrap_interval.lower <= first.bootstrap_interval.upper


def test_bootstrap_block_size_must_be_explicitly_valid() -> None:
    trials = (_enter(Outcome.WIN), _enter(Outcome.LOSS), _enter(Outcome.WIN))

    report = evaluate(
        folds=(trials,),
        evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST,
        seed=7,
        bootstrap_block_size=3,
    )

    assert report.bootstrap_interval is not None
    with pytest.raises(InvalidEvaluation, match="bootstrap_block_size"):
        evaluate(
            folds=(trials,),
            evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST,
            seed=7,
            bootstrap_block_size=0,
        )


def test_fold_consistency_is_hit_rate_spread() -> None:
    report = evaluate(
        folds=(
            (_enter(Outcome.WIN), _enter(Outcome.WIN)),
            (_enter(Outcome.LOSS), _enter(Outcome.LOSS)),
        ),
        evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST,
        seed=1,
    )

    assert report.fold_hit_rates == (report.fold_hit_rates[0], report.fold_hit_rates[1])
    assert report.fold_consistency is not None
    assert float(report.fold_consistency) == pytest.approx(1.0)


def test_repeated_evaluation_is_byte_identical() -> None:
    trials = (_enter(Outcome.WIN), _enter(Outcome.LOSS), _enter(Outcome.WIN), _wait())

    first: EvaluationReport = evaluate(
        folds=(trials,), evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST, seed=5
    )
    second: EvaluationReport = evaluate(
        folds=(trials,), evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST, seed=5
    )

    assert first == second
    assert json.dumps(first.to_dict(), sort_keys=True) == json.dumps(
        second.to_dict(), sort_keys=True
    )
