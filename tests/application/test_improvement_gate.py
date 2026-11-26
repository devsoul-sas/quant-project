"""S3.10/B1 synthetic gate tests for the unified improvement convention.

``improvement = loss_baseline - loss_candidate``; a positive value means the
candidate is better. These tests demonstrate that only a fully favourable
confidence interval may pass, that an interval crossing zero never passes, and
that a statistically significant but practically irrelevant improvement is not
promoted (and implies no profitability by itself).
"""

from decimal import Decimal

from devsoul_quant.application.adaptive_shadow import passes_improvement_gate


def test_fully_favourable_interval_passes() -> None:
    assert (
        passes_improvement_gate(
            improvement=Decimal("0.010"),
            first_half=Decimal("0.008"),
            second_half=Decimal("0.008"),
            lower_bound=Decimal("0.006"),
        )
        is True
    )


def test_interval_crossing_zero_cannot_pass() -> None:
    assert (
        passes_improvement_gate(
            improvement=Decimal("0.010"),
            first_half=Decimal("0.008"),
            second_half=Decimal("0.008"),
            lower_bound=Decimal("-0.002"),
        )
        is False
    )


def test_unfavourable_interval_cannot_pass() -> None:
    assert (
        passes_improvement_gate(
            improvement=Decimal("-0.010"),
            first_half=Decimal("-0.020"),
            second_half=Decimal("-0.020"),
            lower_bound=Decimal("-0.050"),
        )
        is False
    )


def test_relevant_but_negative_lower_bound_cannot_pass() -> None:
    """A large point estimate cannot rescue an interval whose bound is negative."""
    assert (
        passes_improvement_gate(
            improvement=Decimal("0.100"),
            first_half=Decimal("0.090"),
            second_half=Decimal("0.090"),
            lower_bound=Decimal("-0.001"),
        )
        is False
    )


def test_irrelevant_improvement_cannot_pass() -> None:
    """Statistically significant but below the preregistered relevance threshold."""
    assert (
        passes_improvement_gate(
            improvement=Decimal("0.002"),
            first_half=Decimal("0.001"),
            second_half=Decimal("0.001"),
            lower_bound=Decimal("0.001"),
        )
        is False
    )


def test_statistical_improvement_is_a_bare_boolean_not_a_profit_claim() -> None:
    """The improvement gate encodes only loss improvement, never profitability.

    Profitability is a separate economic gate (``mean_estimated_value > 0``)
    enforced in ``final_snapshot``; passing this statistical gate is necessary
    but not sufficient.
    """
    result = passes_improvement_gate(
        improvement=Decimal("0.050"),
        first_half=Decimal("0.040"),
        second_half=Decimal("0.040"),
        lower_bound=Decimal("0.030"),
    )
    assert result is True
    assert isinstance(result, bool)
