"""Ephemeral descriptive characterization independent of confirmatory sufficiency."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from devsoul_quant.domain.demo_gates import (
    GateResult,
    GateStatus,
    evaluate_data_quality_gate,
    evaluate_sample_sufficiency_gate,
)


@dataclass(frozen=True, slots=True)
class ObservationGateReport[Profile]:
    """Transient gate results and an optional in-memory descriptive profile."""

    data_quality: GateResult
    sample_sufficiency: GateResult
    descriptive_profile: Profile | None


def characterize_valid_sample[SampleValue, Profile](
    *,
    sample: Sequence[SampleValue],
    minimum_confirmatory_sample: int,
    data_quality_valid: bool,
    characterize: Callable[[tuple[SampleValue, ...]], Profile],
) -> ObservationGateReport[Profile]:
    """Characterize valid data even when it is insufficient for confirmation."""
    values = tuple(sample)
    quality = evaluate_data_quality_gate(
        temporal_order_valid=data_quality_valid,
        pip_sizes_valid=data_quality_valid,
        gaps_within_policy=data_quality_valid,
    )
    sufficiency = evaluate_sample_sufficiency_gate(
        observed=len(values), minimum=minimum_confirmatory_sample
    )
    profile = characterize(values) if quality.status is GateStatus.PASS else None
    return ObservationGateReport(
        data_quality=quality,
        sample_sufficiency=sufficiency,
        descriptive_profile=profile,
    )
