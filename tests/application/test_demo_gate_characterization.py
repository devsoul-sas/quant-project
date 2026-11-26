"""Descriptive characterization must not depend on confirmatory sample sufficiency."""

from devsoul_quant.application.demo_gates import characterize_valid_sample
from devsoul_quant.domain.demo_gates import GateStatus


def test_valid_sample_is_characterized_even_when_confirmatory_sample_is_insufficient() -> None:
    calls: list[tuple[int, ...]] = []

    def characterize(values: tuple[int, ...]) -> str:
        calls.append(values)
        return "DESCRIPTIVE_PROFILE_AVAILABLE"

    report = characterize_valid_sample(
        sample=(1, 2, 3),
        minimum_confirmatory_sample=10,
        data_quality_valid=True,
        characterize=characterize,
    )

    assert report.sample_sufficiency.status is GateStatus.INSUFFICIENT
    assert report.descriptive_profile == "DESCRIPTIVE_PROFILE_AVAILABLE"
    assert calls == [(1, 2, 3)]


def test_invalid_data_is_not_characterized() -> None:
    called = False

    def characterize(values: tuple[int, ...]) -> str:
        nonlocal called
        called = True
        return "UNREACHABLE"

    report = characterize_valid_sample(
        sample=(1, 2, 3),
        minimum_confirmatory_sample=2,
        data_quality_valid=False,
        characterize=characterize,
    )

    assert report.data_quality.status is GateStatus.FAIL
    assert report.descriptive_profile is None
    assert called is False
