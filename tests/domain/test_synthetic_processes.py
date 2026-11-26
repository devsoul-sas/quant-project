"""Tests for the deterministic multi-process synthetic scenario generators."""

from decimal import Decimal
from itertools import pairwise

import pytest

from devsoul_quant.domain.digit_strategy import last_digit
from devsoul_quant.domain.synthetic_processes import (
    InvalidSyntheticScenario,
    SyntheticProcess,
    SyntheticScenario,
    generate_scenario,
)

ALL_PROCESSES = tuple(process for process in SyntheticProcess)


def _scenario(process: SyntheticProcess, **overrides: object) -> SyntheticScenario:
    params: dict[str, object] = {"process": process, "seed": 7, "count": 50}
    params.update(overrides)
    return SyntheticScenario(**params)  # type: ignore[arg-type]


def _price_processes() -> tuple[SyntheticProcess, ...]:
    return (
        SyntheticProcess.RANDOM_WALK,
        SyntheticProcess.GBM,
        SyntheticProcess.ORNSTEIN_UHLENBECK,
        SyntheticProcess.VOLATILITY_REGIME,
    )


def _digit_processes() -> tuple[SyntheticProcess, ...]:
    return (SyntheticProcess.UNIFORM_DIGIT, SyntheticProcess.MARKOV_PARITY)


@pytest.mark.parametrize("process", ALL_PROCESSES)
def test_generation_is_deterministic(process: SyntheticProcess) -> None:
    scenario = _scenario(process, pip_size=4)
    assert generate_scenario(scenario) == generate_scenario(scenario)


@pytest.mark.parametrize("process", ALL_PROCESSES)
def test_generation_produces_valid_ticks(process: SyntheticProcess) -> None:
    scenario = _scenario(process, pip_size=4, count=20)
    ticks = generate_scenario(scenario)
    assert len(ticks) == 20
    for index, tick in enumerate(ticks):
        assert tick.epoch == scenario.start_epoch + index * scenario.interval
        assert tick.quote.is_finite() and tick.quote > 0


@pytest.mark.parametrize("process", _price_processes())
def test_price_processes_leave_pip_size_none(process: SyntheticProcess) -> None:
    ticks = generate_scenario(_scenario(process, count=20))
    assert all(tick.pip_size is None for tick in ticks)


@pytest.mark.parametrize("process", _digit_processes())
def test_digit_processes_set_pip_size(process: SyntheticProcess) -> None:
    ticks = generate_scenario(_scenario(process, pip_size=4, count=20))
    assert all(tick.pip_size == 4 for tick in ticks)


def test_random_walk_matches_legacy_generator() -> None:
    from devsoul_quant.domain.synthetic import generate_ticks

    scenario = _scenario(
        SyntheticProcess.RANDOM_WALK, seed=3, count=30, start_quote=Decimal("100.0000")
    )
    legacy = generate_ticks(seed=3, count=30, start_quote=Decimal("100.0000"))
    assert generate_scenario(scenario) == legacy


def test_gbm_is_geometric_when_volatility_is_zero() -> None:
    scenario = _scenario(
        SyntheticProcess.GBM,
        seed=1,
        count=6,
        start_quote=Decimal("100.0000"),
        drift=Decimal("0.01"),
        volatility=Decimal("0"),
    )
    ticks = generate_scenario(scenario)
    expected = Decimal("100.0000")
    for tick in ticks:
        assert tick.quote == expected
        expected = expected * Decimal("1.01")


def test_ornstein_uhlenbeck_converges_to_mean_without_noise() -> None:
    scenario = _scenario(
        SyntheticProcess.ORNSTEIN_UHLENBECK,
        seed=1,
        count=6,
        start_quote=Decimal("110.0000"),
        mean_level=Decimal("100.0000"),
        reversion_speed=Decimal("0.5"),
        volatility=Decimal("0"),
    )
    ticks = generate_scenario(scenario)
    expected = Decimal("110.0000")
    for tick in ticks:
        assert tick.quote == expected
        expected = expected + Decimal("0.5") * (Decimal("100.0000") - expected)


def test_uniform_digit_last_digits_are_all_valid() -> None:
    ticks = generate_scenario(
        _scenario(SyntheticProcess.UNIFORM_DIGIT, seed=11, count=200, pip_size=4)
    )
    digits = [last_digit(tick) for tick in ticks]
    assert all(0 <= digit <= 9 for digit in digits)
    assert len({digit % 2 for digit in digits}) == 2


def test_markov_parity_with_full_persistence_never_switches() -> None:
    ticks = generate_scenario(
        _scenario(
            SyntheticProcess.MARKOV_PARITY,
            seed=5,
            count=100,
            pip_size=4,
            parity_persistence=Decimal("1"),
        )
    )
    parities = {last_digit(tick) % 2 for tick in ticks}
    assert len(parities) == 1


def test_markov_parity_with_zero_persistence_alternates() -> None:
    ticks = generate_scenario(
        _scenario(
            SyntheticProcess.MARKOV_PARITY,
            seed=5,
            count=100,
            pip_size=4,
            parity_persistence=Decimal("0"),
        )
    )
    parities = [last_digit(tick) % 2 for tick in ticks]
    assert all(parities[index] != parities[index - 1] for index in range(1, len(parities)))


def test_volatility_regime_uses_distinct_step_magnitudes() -> None:
    scenario = _scenario(
        SyntheticProcess.VOLATILITY_REGIME,
        seed=9,
        count=100,
        regimes=((10, 50), (100, 50)),
    )
    ticks = generate_scenario(scenario)
    first_regime = ticks[:50]
    second_regime = ticks[50:]
    assert max(abs(b.quote - a.quote) for a, b in pairwise(first_regime)) <= Decimal("0.001")
    assert max(abs(b.quote - a.quote) for a, b in pairwise(second_regime)) <= Decimal("0.01")
    assert max(abs(b.quote - a.quote) for a, b in pairwise(second_regime)) > Decimal("0.001")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"count": 1}, "count"),
        ({"seed": "x"}, "seed"),
        ({"start_quote": Decimal("0")}, "start_quote"),
        ({"volatility": Decimal("-0.1")}, "volatility"),
        ({"reversion_speed": Decimal("1")}, "reversion_speed"),
        ({"parity_persistence": Decimal("1.5")}, "parity_persistence"),
        ({"regimes": ()}, "regimes"),
        ({"regimes": ((0, 5),)}, "regime"),
        ({"interval": 0}, "interval"),
        ({"pip_size": -1}, "pip_size"),
    ],
)
def test_invalid_scenarios_fail_closed(overrides: dict[str, object], message: str) -> None:
    params: dict[str, object] = {"process": SyntheticProcess.RANDOM_WALK, "seed": 1, "count": 10}
    params.update(overrides)
    with pytest.raises(InvalidSyntheticScenario, match=message):
        SyntheticScenario(**params)  # type: ignore[arg-type]


@pytest.mark.parametrize("process", _digit_processes())
def test_digit_processes_require_pip_size(process: SyntheticProcess) -> None:
    with pytest.raises(InvalidSyntheticScenario, match="pip_size"):
        generate_scenario(_scenario(process, count=10))


def test_volatility_regime_rejects_short_regime_coverage() -> None:
    scenario = _scenario(
        SyntheticProcess.VOLATILITY_REGIME,
        seed=1,
        count=100,
        regimes=((10, 10), (100, 10)),
    )
    with pytest.raises(InvalidSyntheticScenario, match="regime lengths"):
        generate_scenario(scenario)
