"""Independent, prospective gates for S3.6 demo operation.

Each evaluator answers one question only. In particular, connectivity never
infers sample size from an idealized message frequency, and sample sufficiency
never changes the observed connectivity result.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class InvalidDemoGate(ValueError):
    """Raised when a gate receives malformed or ambiguous inputs."""


class GateStatus(StrEnum):
    """Categorical gate outcomes without scientific reinterpretation."""

    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class GateResult:
    """One gate outcome and non-sensitive categorical reasons."""

    status: GateStatus
    reasons: tuple[str, ...] = ()


def _boolean(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise InvalidDemoGate(f"{field} must be a boolean")
    return value


def _non_negative_integer(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise InvalidDemoGate(f"{field} must be a non-negative integer")
    return value


def _positive_integer(value: object, field: str) -> int:
    result = _non_negative_integer(value, field)
    if result == 0:
        raise InvalidDemoGate(f"{field} must be positive")
    return result


def _non_negative_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise InvalidDemoGate(f"{field} must be a non-negative finite Decimal")
    return value


def _positive_decimal(value: object, field: str) -> Decimal:
    result = _non_negative_decimal(value, field)
    if result == 0:
        raise InvalidDemoGate(f"{field} must be positive")
    return result


def evaluate_connectivity_gate(
    *,
    elapsed_seconds: Decimal,
    minimum_seconds: Decimal,
    disconnected: bool,
) -> GateResult:
    """Evaluate transport duration without making a sample-size assertion."""
    elapsed = _non_negative_decimal(elapsed_seconds, "elapsed_seconds")
    minimum = _positive_decimal(minimum_seconds, "minimum_seconds")
    lost = _boolean(disconnected, "disconnected")
    reasons: list[str] = []
    if lost:
        reasons.append("DISCONNECTED")
    if elapsed < minimum:
        reasons.append("MINIMUM_DURATION_NOT_MET")
    return GateResult(GateStatus.FAIL if reasons else GateStatus.PASS, tuple(reasons))


def evaluate_data_quality_gate(
    *,
    temporal_order_valid: bool,
    pip_sizes_valid: bool,
    gaps_within_policy: bool,
) -> GateResult:
    """Evaluate validity only; duration and sample count are intentionally absent."""
    reasons: list[str] = []
    if not _boolean(temporal_order_valid, "temporal_order_valid"):
        reasons.append("INVALID_TEMPORAL_ORDER")
    if not _boolean(pip_sizes_valid, "pip_sizes_valid"):
        reasons.append("INVALID_PIP_SIZE")
    if not _boolean(gaps_within_policy, "gaps_within_policy"):
        reasons.append("GAP_POLICY_VIOLATION")
    return GateResult(GateStatus.FAIL if reasons else GateStatus.PASS, tuple(reasons))


def evaluate_sample_sufficiency_gate(*, observed: int, minimum: int) -> GateResult:
    """Evaluate count sufficiency independently of connectivity and quality."""
    count = _non_negative_integer(observed, "observed")
    required = _positive_integer(minimum, "minimum")
    if count < required:
        return GateResult(GateStatus.INSUFFICIENT, ("MINIMUM_SAMPLE_NOT_MET",))
    return GateResult(GateStatus.PASS)


def evaluate_economic_integration_gate(
    *,
    authorized_contracts: int,
    executed_contracts: int,
    settled_contracts: int,
    open_contracts: int,
    realized_profit: Decimal,
) -> GateResult:
    """Evaluate execution mechanics; profit sign never affects this gate."""
    authorized = _positive_integer(authorized_contracts, "authorized_contracts")
    executed = _non_negative_integer(executed_contracts, "executed_contracts")
    settled = _non_negative_integer(settled_contracts, "settled_contracts")
    open_count = _non_negative_integer(open_contracts, "open_contracts")
    if not isinstance(realized_profit, Decimal) or not realized_profit.is_finite():
        raise InvalidDemoGate("realized_profit must be a finite Decimal")
    reasons: list[str] = []
    if executed == 0:
        reasons.append("NO_CONTRACT_EXECUTED")
    if executed > authorized:
        reasons.append("AUTHORIZED_CONTRACT_LIMIT_EXCEEDED")
    if settled != executed:
        reasons.append("SETTLEMENT_COUNT_MISMATCH")
    if open_count != 0:
        reasons.append("OPEN_CONTRACTS_REMAIN")
    return GateResult(GateStatus.FAIL if reasons else GateStatus.PASS, tuple(reasons))


def evaluate_predictive_evidence_gate(
    *,
    sample_justified: bool,
    beats_baseline: bool,
    beats_break_even: bool,
) -> GateResult:
    """Keep scientific evidence separate from demo execution capability."""
    sufficient = _boolean(sample_justified, "sample_justified")
    baseline = _boolean(beats_baseline, "beats_baseline")
    break_even = _boolean(beats_break_even, "beats_break_even")
    if not sufficient:
        return GateResult(GateStatus.INSUFFICIENT, ("SAMPLE_NOT_JUSTIFIED",))
    reasons: list[str] = []
    if not baseline:
        reasons.append("BASELINE_NOT_BEATEN")
    if not break_even:
        reasons.append("BREAK_EVEN_NOT_BEATEN")
    return GateResult(GateStatus.FAIL if reasons else GateStatus.PASS, tuple(reasons))


def evaluate_risk_gate(
    *,
    demo_account_confirmed: bool,
    real_money_used: bool,
    fixed_stake: Decimal,
    maximum_stake: Decimal,
    contracts_executed: int,
    maximum_contracts: int,
    open_contracts: int,
    maximum_open_contracts: int,
    realized_loss: Decimal,
    maximum_loss: Decimal,
) -> GateResult:
    """Evaluate prefixed demo risk limits and fail closed on real money."""
    demo = _boolean(demo_account_confirmed, "demo_account_confirmed")
    real = _boolean(real_money_used, "real_money_used")
    stake = _positive_decimal(fixed_stake, "fixed_stake")
    stake_limit = _positive_decimal(maximum_stake, "maximum_stake")
    executed = _non_negative_integer(contracts_executed, "contracts_executed")
    contract_limit = _positive_integer(maximum_contracts, "maximum_contracts")
    open_count = _non_negative_integer(open_contracts, "open_contracts")
    open_limit = _positive_integer(maximum_open_contracts, "maximum_open_contracts")
    loss = _non_negative_decimal(realized_loss, "realized_loss")
    loss_limit = _positive_decimal(maximum_loss, "maximum_loss")
    reasons: list[str] = []
    if not demo:
        reasons.append("DEMO_ACCOUNT_NOT_CONFIRMED")
    if real:
        reasons.append("REAL_MONEY_USED")
    if stake > stake_limit:
        reasons.append("STAKE_LIMIT_EXCEEDED")
    if executed > contract_limit:
        reasons.append("CONTRACT_LIMIT_EXCEEDED")
    if open_count > open_limit:
        reasons.append("OPEN_CONTRACT_LIMIT_EXCEEDED")
    if loss > loss_limit:
        reasons.append("LOSS_LIMIT_EXCEEDED")
    return GateResult(GateStatus.FAIL if reasons else GateStatus.PASS, tuple(reasons))
