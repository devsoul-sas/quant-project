"""S3.10 regression tests: O(1) window features and incremental metrics.

These tests pin the numerical equivalence guarantees required by the C2 and C3
remediations: the bounded six-tick feature window and the incremental score
accumulator must reproduce the former full-history computation bit-for-bit.
"""

from decimal import Decimal

from devsoul_quant.application.adaptive_shadow import AdaptivePrequentialEvaluator
from devsoul_quant.domain.adaptive_intelligence import build_adaptive_features
from devsoul_quant.domain.replay import Tick

_EPSILON = Decimal("0.000000000001")


def _ticks(count: int) -> tuple[Tick, ...]:
    return tuple(
        Tick(index, Decimal("100") + Decimal(index) / Decimal("100"), pip_size=2)
        for index in range(1, count + 1)
    )


def test_features_from_bounded_window_equal_full_history() -> None:
    """The six causal features are identical when built from the last six ticks."""
    ticks = _ticks(40)
    decision_epoch = ticks[-1].epoch
    from_full = build_adaptive_features(ticks, decision_epoch=decision_epoch)
    from_window = build_adaptive_features(ticks[-6:], decision_epoch=decision_epoch)
    assert from_full == from_window


def test_evaluator_keeps_a_bounded_window_only() -> None:
    """The evaluator retains at most six ticks, never the full history."""
    evaluator = AdaptivePrequentialEvaluator(warmup_labels=0, seed=38)
    for tick in _ticks(500):
        evaluator.observe(tick)
    assert len(evaluator._window) <= 6


def _naive_brier(probabilities, labels) -> Decimal:
    return sum(
        (p - Decimal(label)) ** 2 for p, label in zip(probabilities, labels, strict=True)
    ) / Decimal(len(labels))


def _naive_log_loss(probabilities, labels) -> Decimal:
    total = Decimal("0")
    for p, label in zip(probabilities, labels, strict=True):
        clipped = max(_EPSILON, min(Decimal(1) - _EPSILON, p))
        total -= Decimal(label) * clipped.ln() + Decimal(1 - label) * (Decimal(1) - clipped).ln()
    return total / Decimal(len(labels))


def _naive_accuracy(probabilities, labels) -> Decimal:
    return Decimal(
        sum(
            (p >= Decimal("0.5")) is bool(label)
            for p, label in zip(probabilities, labels, strict=True)
        )
    ) / Decimal(len(labels))


def _naive_ece(probabilities, labels) -> Decimal:
    total = Decimal("0")
    denominator = Decimal(len(labels))
    for bin_index in range(10):
        members = [
            (p, label)
            for p, label in zip(probabilities, labels, strict=True)
            if min(9, int(p * Decimal(10))) == bin_index
        ]
        if not members:
            continue
        member_count = Decimal(len(members))
        mean_probability = sum((item[0] for item in members), start=Decimal("0")) / member_count
        mean_label = sum((Decimal(item[1]) for item in members), start=Decimal("0")) / member_count
        total += member_count / denominator * abs(mean_probability - mean_label)
    return total


def test_incremental_metrics_match_naive_full_recompute() -> None:
    """Incremental Brier/log-loss/accuracy/ECE equal a full-list recomputation."""
    evaluator = AdaptivePrequentialEvaluator(warmup_labels=0, seed=38)
    for index in range(1, 200):
        quote = Decimal("100.03") if index % 2 else Decimal("99.97")
        evaluator.observe(Tick(index, quote, pip_size=2))

    accumulator = evaluator._scores["LOGISTIC"]
    metrics = evaluator.snapshot().for_model("LOGISTIC")
    probabilities = accumulator.probabilities
    labels = accumulator.labels

    assert metrics.brier_score == _naive_brier(probabilities, labels)
    assert metrics.log_loss == _naive_log_loss(probabilities, labels)
    assert metrics.accuracy == _naive_accuracy(probabilities, labels)
    assert metrics.expected_calibration_error == _naive_ece(probabilities, labels)
