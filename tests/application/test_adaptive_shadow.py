"""Prequential S3.8 evaluator and leakage boundaries."""

from decimal import Decimal

import pytest

from devsoul_quant.application.adaptive_shadow import AdaptivePrequentialEvaluator
from devsoul_quant.domain.adaptive_intelligence import InvalidAdaptiveInput
from devsoul_quant.domain.replay import Tick


def _rising_ticks(count: int) -> tuple[Tick, ...]:
    return tuple(
        Tick(index, Decimal("100") + Decimal(index) / Decimal("100"), pip_size=2)
        for index in range(1, count + 1)
    )


def test_prequential_evaluator_scores_before_learning_and_keeps_one_pending_label() -> None:
    evaluator = AdaptivePrequentialEvaluator(warmup_labels=0, seed=38)
    ticks = _rising_ticks(7)
    prediction = None

    for tick in ticks[:6]:
        prediction = evaluator.observe(tick)

    assert prediction is not None
    assert prediction.epoch == 6
    assert prediction.probability("LOGISTIC") == Decimal("0.5")
    assert evaluator.snapshot().evaluation_labels == 0
    assert evaluator.snapshot().pending_labels == 1

    next_prediction = evaluator.observe(ticks[6])
    snapshot = evaluator.snapshot()
    logistic = snapshot.for_model("LOGISTIC")

    assert logistic.observations == 1
    assert logistic.brier_score == Decimal("0.25")
    assert snapshot.parity_resolved_labels == 1
    assert snapshot.parity_constant_brier == Decimal("0.25")
    assert snapshot.parity_frequency_brier == Decimal("0.25")
    assert next_prediction is not None
    assert next_prediction.probability("LOGISTIC") > Decimal("0.5")
    assert snapshot.pending_labels == 1


def test_prequential_warmup_updates_models_without_scoring() -> None:
    evaluator = AdaptivePrequentialEvaluator(warmup_labels=2, seed=38)

    for tick in _rising_ticks(9):
        evaluator.observe(tick)

    snapshot = evaluator.snapshot()

    assert snapshot.resolved_labels == 3
    assert snapshot.evaluation_labels == 1
    assert snapshot.for_model("LOGISTIC").observations == 1
    final = evaluator.final_snapshot()
    assert final.decision == "INSUFFICIENT_EVIDENCE"
    assert "EVALUATION_SAMPLE_BELOW_1200" in final.decision_reasons


def test_prequential_clear_zeroizes_predictions_models_metrics_and_ticks() -> None:
    evaluator = AdaptivePrequentialEvaluator(warmup_labels=0, seed=38)
    for tick in _rising_ticks(8):
        evaluator.observe(tick)

    evaluator.clear()
    snapshot = evaluator.snapshot()

    assert snapshot.resolved_labels == 0
    assert snapshot.evaluation_labels == 0
    assert snapshot.pending_labels == 0
    assert all(model.observations == 0 for model in snapshot.models)


def test_shadow_quote_metrics_distinguish_opportunities_signals_and_no_contracts() -> None:
    evaluator = AdaptivePrequentialEvaluator(warmup_labels=0, seed=38)
    prediction = None
    for tick in _rising_ticks(7):
        prediction = evaluator.observe(tick)
    assert prediction is not None

    evaluator.observe_quotes(
        prediction,
        call_break_even=Decimal("0.40"),
        put_break_even=Decimal("0.60"),
    )
    logistic = evaluator.snapshot().for_model("LOGISTIC")

    assert logistic.quoted_opportunities == 1
    assert logistic.signals == 1
    assert logistic.signal_coverage == Decimal("1")
    assert logistic.mean_break_even == Decimal("0.40")
    assert logistic.mean_estimated_value is not None
    assert logistic.mean_estimated_value > 0


def test_final_gate_uses_temporal_halves_and_moving_block_bootstrap() -> None:
    evaluator = AdaptivePrequentialEvaluator(warmup_labels=120, seed=38)
    for index in range(1, 1327):
        quote = Decimal("100.01") if index % 2 else Decimal("99.99")
        prediction = evaluator.observe(Tick(index, quote, pip_size=2))
        if prediction is not None and index % 30 == 0:
            evaluator.observe_quotes(
                prediction,
                call_break_even=Decimal("0.51"),
                put_break_even=Decimal("0.51"),
            )

    final = evaluator.final_snapshot()

    assert final.evaluation_labels == 1200
    assert final.decision in {"GO", "NO_GO"}
    for model_name in ("LOGISTIC", "GAUSSIAN_NB"):
        metrics = final.for_model(model_name)
        assert metrics.brier_improvement_vs_causal is not None
        assert metrics.first_half_brier_improvement is not None
        assert metrics.second_half_brier_improvement is not None
        assert metrics.bootstrap_lower_bound is not None


def test_prequential_evaluator_rejects_invalid_configuration_order_and_quotes() -> None:
    with pytest.raises(InvalidAdaptiveInput):
        AdaptivePrequentialEvaluator(warmup_labels=-1)
    with pytest.raises(InvalidAdaptiveInput):
        AdaptivePrequentialEvaluator(seed=True)

    evaluator = AdaptivePrequentialEvaluator(warmup_labels=0)
    prediction = None
    for tick in _rising_ticks(6):
        prediction = evaluator.observe(tick)
    assert prediction is not None
    with pytest.raises(InvalidAdaptiveInput):
        evaluator.observe(Tick(6, Decimal("101"), pip_size=2))
    with pytest.raises(InvalidAdaptiveInput):
        evaluator.observe_quotes(
            prediction,
            call_break_even=Decimal("0"),
            put_break_even=Decimal("0.5"),
        )
