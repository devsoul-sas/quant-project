"""S3.11/H1 — step-direction evaluator tests."""

import random
from decimal import Decimal

import pytest

from devsoul_quant.domain import step_direction as sd
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.step_direction import (
    InvalidStepDirection,
    StepDirection,
    StepDirectionPrequentialEvaluator,
    classify_step,
)


def _ticks(directions: list[int], *, cadence: int = 2, pip_size: int = 1) -> tuple[Tick, ...]:
    ticks = [Tick(1, Decimal("100.00"), pip_size=pip_size)]
    epoch = 1
    quote = Decimal("100.00")
    step = Decimal(1).scaleb(-pip_size)
    for direction in directions:
        epoch += cadence
        quote = quote + step if direction == 1 else quote - step
        ticks.append(Tick(epoch, quote, pip_size=pip_size))
    return tuple(ticks)


def _alternating(count: int) -> list[int]:
    return [index % 2 for index in range(count)]


def _iid(count: int, seed: int = 7) -> list[int]:
    return [random.Random(seed + index).randrange(2) for index in range(count)]


def test_classify_step_distinguishes_up_down_and_flat() -> None:
    assert classify_step(Decimal("100.00"), Decimal("100.10")) is StepDirection.UP
    assert classify_step(Decimal("100.00"), Decimal("99.90")) is StepDirection.DOWN
    assert classify_step(Decimal("100.00"), Decimal("100.00")) is StepDirection.FLAT


def test_warmup_only_yields_insufficient_evidence() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=5, cadence=2)
    for tick in _ticks(_alternating(5), cadence=2):
        evaluator.observe_tick(tick)
    result = evaluator.finalize()
    assert result.classification == "H1_INSUFFICIENT_EVIDENCE"
    assert result.valid_transitions == 0
    assert result.warmup_transitions == 5


def test_flat_and_discontinuous_transitions_are_excluded() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=4, cadence=2)
    # Warm up with four clean UP steps, then a FLAT and a discontinuity.
    for tick in _ticks([1, 1, 1, 1], cadence=2):
        evaluator.observe_tick(tick)
    # FLAT: same quote.
    evaluator.observe_tick(Tick(11, Decimal("100.40"), pip_size=1))
    # Discontinuity: epoch gap of 5 instead of 2.
    evaluator.observe_tick(Tick(16, Decimal("100.50"), pip_size=1))
    # Two more valid transitions.
    evaluator.observe_tick(Tick(18, Decimal("100.60"), pip_size=1))
    evaluator.observe_tick(Tick(20, Decimal("100.50"), pip_size=1))
    result = evaluator.finalize()
    assert result.flat_transitions == 1
    assert result.discontinuous_transitions == 1
    assert result.valid_transitions == 1


def test_cadence_is_inferred_from_warmup_when_not_given() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=8, cadence=None)
    for tick in _ticks(_alternating(8), cadence=3):
        evaluator.observe_tick(tick)
    assert evaluator._frozen_cadence == 3


def test_iid_sequence_yields_no_edge() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=120, cadence=2, seed=42)
    for tick in _ticks(_iid(2600, seed=7), cadence=2):
        evaluator.observe_tick(tick)
    result = evaluator.finalize()
    assert result.classification in ("H1_NO_EDGE", "H1_INSUFFICIENT_EVIDENCE")
    assert result.effective_sample_size is not None
    assert result.for_model("MARKOV_1").brier_score is not None
    assert result.holm_significant_lag1 is False


def test_marginal_bias_without_lag1_dependence_does_not_promote() -> None:
    """A biased but i.i.d. sequence must not promote: the adaptive candidate's
    only edge over the causal frequency control would be marginal learning, not
    lag-1 dependence, so the lag-1 gate must stay closed."""
    generator = random.Random(11)
    directions = [1 if generator.random() < 0.7 else 0 for _ in range(2600)]
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=120, cadence=2, seed=42)
    for tick in _ticks(directions, cadence=2):
        evaluator.observe_tick(tick)
    result = evaluator.finalize()
    assert result.classification in ("H1_NO_EDGE", "H1_INSUFFICIENT_EVIDENCE")
    assert result.holm_significant_lag1 is False
    assert result.improvement_causal_adaptive is not None
    assert result.improvement_causal_adaptive < Decimal("0.0001")


def test_strong_lag1_dependence_is_detected() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=120, cadence=2, seed=42)
    for tick in _ticks(_alternating(2600), cadence=2):
        evaluator.observe_tick(tick)
    result = evaluator.finalize()
    assert result.classification == "H1_CANDIDATE_FOR_INDEPENDENT_VALIDATION"
    adaptive = result.for_model("MARKOV_1_ADAPTIVE")
    frozen = result.for_model("MARKOV_1")
    memoryless = result.for_model("MEMORYLESS")
    assert adaptive.brier_score is not None and memoryless.brier_score is not None
    assert adaptive.brier_score < memoryless.brier_score
    assert frozen.brier_score is not None and frozen.brier_score < memoryless.brier_score
    assert result.improvement_memoryless_adaptive is not None
    assert result.improvement_memoryless_adaptive > 0
    assert result.bootstrap_lower_bound is not None and result.bootstrap_lower_bound > 0
    assert result.holm_significant_lag1 is True


def test_adaptive_markov_beats_frozen_reference() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=120, cadence=2, seed=42)
    for tick in _ticks(_alternating(2600), cadence=2):
        evaluator.observe_tick(tick)
    result = evaluator.finalize()
    adaptive = result.for_model("MARKOV_1_ADAPTIVE")
    frozen = result.for_model("MARKOV_1")
    assert adaptive.brier_score is not None and frozen.brier_score is not None
    assert adaptive.brier_score < frozen.brier_score


def test_adaptive_markov_updates_counts_causally() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=4, cadence=2)
    for tick in _ticks([1, 1, 1, 1], cadence=2):
        evaluator.observe_tick(tick)
    # Seeded from warm-up (three UP->UP records) + Dirichlet alpha=1 prior.
    assert evaluator._adaptive_counts == [[1, 1], [1, 4]]
    evaluator.observe_tick(Tick(11, Decimal("100.50"), pip_size=1))  # UP: sets pending only
    assert evaluator._adaptive_counts[1][1] == 4
    evaluator.observe_tick(Tick(13, Decimal("100.60"), pip_size=1))  # UP: resolves and updates
    assert evaluator._adaptive_counts[1][1] == 5


def test_rejects_non_monotonic_epochs() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=4, cadence=2)
    evaluator.observe_tick(Tick(1, Decimal("100.00"), pip_size=1))
    evaluator.observe_tick(Tick(3, Decimal("100.10"), pip_size=1))
    with pytest.raises(InvalidStepDirection):
        evaluator.observe_tick(Tick(3, Decimal("100.20"), pip_size=1))


def test_clear_resets_state() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=4, cadence=2)
    for tick in _ticks(_alternating(4), cadence=2):
        evaluator.observe_tick(tick)
    evaluator.clear()
    assert evaluator._ticks_received == 0
    assert evaluator._warmup_count == 0


def test_classify_step_rejects_non_finite_quotes() -> None:
    with pytest.raises(InvalidStepDirection):
        classify_step(Decimal("1"), Decimal("Infinity"))


def test_modal_positive_empty_and_mode() -> None:
    assert sd._modal_positive([]) is None
    assert sd._modal_positive([2, 2, 3]) == 2


def test_init_rejects_bad_parameters() -> None:
    with pytest.raises(InvalidStepDirection):
        StepDirectionPrequentialEvaluator(warmup_transitions=1)
    with pytest.raises(InvalidStepDirection):
        StepDirectionPrequentialEvaluator(seed="x")  # type: ignore[arg-type]
    with pytest.raises(InvalidStepDirection):
        StepDirectionPrequentialEvaluator(cadence=0)


def test_freeze_warmup_raises_without_inferable_cadence() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=2, cadence=None)
    evaluator._warmup_gaps = []
    with pytest.raises(InvalidStepDirection):
        evaluator._freeze_warmup()


def test_flat_during_warmup_is_counted() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=2, cadence=2)
    evaluator.observe_tick(Tick(1, Decimal("100.00"), pip_size=1))
    evaluator.observe_tick(Tick(3, Decimal("100.00"), pip_size=1))
    assert evaluator._flat == 1


def test_predictions_for_requires_warmup() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=2, cadence=2)
    with pytest.raises(AssertionError):
        evaluator._predictions_for(0)


def test_metrics_empty_sample() -> None:
    metrics = StepDirectionPrequentialEvaluator._metrics([], [], "X")
    assert metrics.observations == 0
    assert metrics.brier_score is None


def test_effective_sample_size_single_element() -> None:
    assert StepDirectionPrequentialEvaluator._effective_sample_size((Decimal("1"),)) == Decimal("1")


def test_marginal_p_value_zero_effective_sample() -> None:
    assert StepDirectionPrequentialEvaluator._marginal_p_value(
        Decimal("0.6"), Decimal("0")
    ) == Decimal("1")


def test_lag1_chi_square_empty() -> None:
    evaluator = StepDirectionPrequentialEvaluator(warmup_transitions=2, cadence=2)
    assert evaluator._lag1_chi_square() is None


def test_holm_with_missing_p_values() -> None:
    assert sd._holm(None, None) == (False, False)


def test_pick_missing_model_raises() -> None:
    with pytest.raises(KeyError):
        StepDirectionPrequentialEvaluator._pick((), "X")


def test_moving_block_bootstrap_short_series() -> None:
    differences = tuple(Decimal(str(index)) for index in range(30))
    lower, p_value = StepDirectionPrequentialEvaluator._moving_block_bootstrap(differences, seed=1)
    assert lower is not None
    assert p_value is not None
