"""Prospective, independent S3.6 demo gate tests."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.demo_gates import (
    GateStatus,
    InvalidDemoGate,
    evaluate_connectivity_gate,
    evaluate_data_quality_gate,
    evaluate_economic_integration_gate,
    evaluate_predictive_evidence_gate,
    evaluate_risk_gate,
    evaluate_sample_sufficiency_gate,
)


def test_connectivity_and_sample_sufficiency_are_independent() -> None:
    connectivity = evaluate_connectivity_gate(
        elapsed_seconds=Decimal("3600.1"),
        minimum_seconds=Decimal("3600"),
        disconnected=False,
    )
    sample = evaluate_sample_sufficiency_gate(observed=1800, minimum=1801)

    assert connectivity.status is GateStatus.PASS
    assert sample.status is GateStatus.INSUFFICIENT


def test_data_quality_does_not_encode_sample_size_or_duration() -> None:
    result = evaluate_data_quality_gate(
        temporal_order_valid=True,
        pip_sizes_valid=True,
        gaps_within_policy=True,
    )

    assert result.status is GateStatus.PASS


def test_economic_integration_is_independent_of_profit() -> None:
    result = evaluate_economic_integration_gate(
        authorized_contracts=2,
        executed_contracts=2,
        settled_contracts=2,
        open_contracts=0,
        realized_profit=Decimal("-2.00"),
    )

    assert result.status is GateStatus.PASS


def test_predictive_evidence_is_insufficient_without_justified_sample() -> None:
    result = evaluate_predictive_evidence_gate(
        sample_justified=False,
        beats_baseline=False,
        beats_break_even=False,
    )

    assert result.status is GateStatus.INSUFFICIENT


def test_risk_gate_fails_closed_for_real_money_or_excess_concurrency() -> None:
    result = evaluate_risk_gate(
        demo_account_confirmed=False,
        real_money_used=True,
        fixed_stake=Decimal("2"),
        maximum_stake=Decimal("1"),
        contracts_executed=3,
        maximum_contracts=2,
        open_contracts=2,
        maximum_open_contracts=1,
        realized_loss=Decimal("3"),
        maximum_loss=Decimal("2"),
    )

    assert result.status is GateStatus.FAIL
    assert result.reasons == (
        "DEMO_ACCOUNT_NOT_CONFIRMED",
        "REAL_MONEY_USED",
        "STAKE_LIMIT_EXCEEDED",
        "CONTRACT_LIMIT_EXCEEDED",
        "OPEN_CONTRACT_LIMIT_EXCEEDED",
        "LOSS_LIMIT_EXCEEDED",
    )


def test_each_gate_reports_its_own_fail_reasons() -> None:
    connectivity = evaluate_connectivity_gate(
        elapsed_seconds=Decimal("59"),
        minimum_seconds=Decimal("60"),
        disconnected=True,
    )
    quality = evaluate_data_quality_gate(
        temporal_order_valid=False,
        pip_sizes_valid=False,
        gaps_within_policy=False,
    )
    economic = evaluate_economic_integration_gate(
        authorized_contracts=1,
        executed_contracts=2,
        settled_contracts=1,
        open_contracts=1,
        realized_profit=Decimal("10"),
    )
    predictive = evaluate_predictive_evidence_gate(
        sample_justified=True,
        beats_baseline=False,
        beats_break_even=False,
    )

    assert connectivity.reasons == ("DISCONNECTED", "MINIMUM_DURATION_NOT_MET")
    assert quality.reasons == (
        "INVALID_TEMPORAL_ORDER",
        "INVALID_PIP_SIZE",
        "GAP_POLICY_VIOLATION",
    )
    assert economic.reasons == (
        "AUTHORIZED_CONTRACT_LIMIT_EXCEEDED",
        "SETTLEMENT_COUNT_MISMATCH",
        "OPEN_CONTRACTS_REMAIN",
    )
    assert predictive.reasons == ("BASELINE_NOT_BEATEN", "BREAK_EVEN_NOT_BEATEN")


def test_no_executed_contract_is_an_economic_integration_failure() -> None:
    result = evaluate_economic_integration_gate(
        authorized_contracts=2,
        executed_contracts=0,
        settled_contracts=0,
        open_contracts=0,
        realized_profit=Decimal("0"),
    )

    assert result.reasons == ("NO_CONTRACT_EXECUTED",)


def test_predictive_evidence_passes_only_when_both_economic_comparators_pass() -> None:
    result = evaluate_predictive_evidence_gate(
        sample_justified=True,
        beats_baseline=True,
        beats_break_even=True,
    )

    assert result.status is GateStatus.PASS


@pytest.mark.parametrize(
    "operation",
    (
        lambda: evaluate_connectivity_gate(
            elapsed_seconds=Decimal("0"), minimum_seconds=Decimal("0"), disconnected=False
        ),
        lambda: evaluate_connectivity_gate(
            elapsed_seconds=Decimal("NaN"), minimum_seconds=Decimal("1"), disconnected=False
        ),
        lambda: evaluate_data_quality_gate(
            temporal_order_valid=1,  # type: ignore[arg-type]
            pip_sizes_valid=True,
            gaps_within_policy=True,
        ),
        lambda: evaluate_sample_sufficiency_gate(observed=-1, minimum=1),
        lambda: evaluate_sample_sufficiency_gate(observed=1, minimum=0),
        lambda: evaluate_economic_integration_gate(
            authorized_contracts=1,
            executed_contracts=1,
            settled_contracts=1,
            open_contracts=0,
            realized_profit=Decimal("Infinity"),
        ),
    ),
)
def test_gate_inputs_fail_closed(operation: object) -> None:
    with pytest.raises(InvalidDemoGate):
        operation()  # type: ignore[operator]
