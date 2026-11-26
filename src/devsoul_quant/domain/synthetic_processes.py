"""Deterministic multi-process synthetic scenario generators owned by DevSoul.

These generators are independent of any provider, reproducible from a seed, and
never use floating point: continuous quantities are ``Decimal`` and randomness
is drawn through integer ``random.Random`` operations so every scenario is
bit-for-bit reproducible.

Synthetic data verifies mathematical and technical correctness only. It is not,
and must never be treated as, evidence of a real statistical edge on Deriv.
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from random import Random

from devsoul_quant.domain.replay import Tick

_DECIMAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)

# A discrete standard-normal approximation: the sum of ``draws`` independent
# uniform integers in [-resolution, resolution], standardized by its exact
# standard deviation sqrt(draws * resolution * (resolution + 1) / 3).
_GAUSSIAN_RESOLUTION = 10
_GAUSSIAN_DRAWS = 12

# Parity persistence is quantized to 1e-6 for exact integer-based transitions.
_PARITY_QUANTUM = 1_000_000


class InvalidSyntheticScenario(ValueError):
    """Raised when a synthetic scenario configuration is invalid or fails closed."""


class SyntheticProcess(StrEnum):
    """Supported deterministic scenario processes."""

    RANDOM_WALK = "RANDOM_WALK"
    GBM = "GBM"
    ORNSTEIN_UHLENBECK = "ORNSTEIN_UHLENBECK"
    UNIFORM_DIGIT = "UNIFORM_DIGIT"
    MARKOV_PARITY = "MARKOV_PARITY"
    VOLATILITY_REGIME = "VOLATILITY_REGIME"


@dataclass(frozen=True, slots=True)
class SyntheticScenario:
    """Frozen recipe for one reproducible synthetic tick sequence.

    Process-specific parameters carry safe defaults; only the relevant fields are
    consumed by each generator. Digit processes require ``pip_size`` so the last
    displayed digit is well-defined.
    """

    process: SyntheticProcess
    seed: int
    count: int
    start_epoch: int = 1_700_000_000
    start_quote: Decimal = Decimal("100.0000")
    interval: int = 1
    pip_size: int | None = None
    drift: Decimal = Decimal("0")
    volatility: Decimal = Decimal("0.001")
    mean_level: Decimal = Decimal("100.0000")
    reversion_speed: Decimal = Decimal("0.05")
    parity_persistence: Decimal = Decimal("0.9")
    regimes: tuple[tuple[int, int], ...] = ((10, 50), (100, 50))

    def __post_init__(self) -> None:
        if not isinstance(self.process, SyntheticProcess):
            raise InvalidSyntheticScenario("process must be a SyntheticProcess")
        if type(self.seed) is not int:
            raise InvalidSyntheticScenario("seed must be an integer")
        if type(self.count) is not int or self.count < 2:
            raise InvalidSyntheticScenario("count must be an integer of at least two")
        if type(self.start_epoch) is not int or self.start_epoch < 0:
            raise InvalidSyntheticScenario("start_epoch must be a non-negative integer")
        if type(self.interval) is not int or self.interval < 1:
            raise InvalidSyntheticScenario("interval must be a positive integer")
        if self.pip_size is not None and (type(self.pip_size) is not int or self.pip_size < 0):
            raise InvalidSyntheticScenario("pip_size must be a non-negative integer or None")
        if (
            not isinstance(self.start_quote, Decimal)
            or not self.start_quote.is_finite()
            or self.start_quote <= 0
        ):
            raise InvalidSyntheticScenario("start_quote must be a positive finite Decimal")
        if not isinstance(self.drift, Decimal) or not self.drift.is_finite():
            raise InvalidSyntheticScenario("drift must be a finite Decimal")
        if (
            not isinstance(self.volatility, Decimal)
            or not self.volatility.is_finite()
            or self.volatility < 0
        ):
            raise InvalidSyntheticScenario("volatility must be a non-negative finite Decimal")
        if (
            not isinstance(self.mean_level, Decimal)
            or not self.mean_level.is_finite()
            or self.mean_level <= 0
        ):
            raise InvalidSyntheticScenario("mean_level must be a positive finite Decimal")
        if (
            not isinstance(self.reversion_speed, Decimal)
            or not self.reversion_speed.is_finite()
            or not (Decimal("0") < self.reversion_speed < Decimal("1"))
        ):
            raise InvalidSyntheticScenario("reversion_speed must be strictly between 0 and 1")
        if (
            not isinstance(self.parity_persistence, Decimal)
            or not self.parity_persistence.is_finite()
            or not (Decimal("0") <= self.parity_persistence <= Decimal("1"))
        ):
            raise InvalidSyntheticScenario("parity_persistence must be between 0 and 1")
        if not isinstance(self.regimes, tuple) or not self.regimes:
            raise InvalidSyntheticScenario("regimes must be a non-empty tuple")
        for regime in self.regimes:
            if (
                not isinstance(regime, tuple)
                or len(regime) != 2
                or type(regime[0]) is not int
                or type(regime[1]) is not int
                or regime[0] < 1
                or regime[1] < 1
            ):
                raise InvalidSyntheticScenario(
                    "each regime must be a (magnitude, length) pair of positive integers"
                )


def _discrete_gaussian(random: Random) -> Decimal:
    """Return a reproducible standard-normal approximation via integer draws."""
    total = sum(
        random.randrange(-_GAUSSIAN_RESOLUTION, _GAUSSIAN_RESOLUTION + 1)
        for _ in range(_GAUSSIAN_DRAWS)
    )
    variance = Decimal(_GAUSSIAN_RESOLUTION) * Decimal(_GAUSSIAN_RESOLUTION + 1) / Decimal(3)
    std = (variance * Decimal(_GAUSSIAN_DRAWS)).sqrt()
    return Decimal(total) / std


def _require_pip_size(scenario: SyntheticScenario) -> int:
    if scenario.pip_size is None:
        raise InvalidSyntheticScenario(f"{scenario.process.value} requires pip_size")
    return scenario.pip_size


def _digit_tick(scenario: SyntheticScenario, epoch: int, digit: int, pip_size: int) -> Tick:
    base = scenario.start_quote.to_integral_value(rounding=ROUND_DOWN)
    quote = base + Decimal(digit).scaleb(-pip_size)
    return Tick(epoch=epoch, quote=quote, pip_size=pip_size)


def _random_walk(scenario: SyntheticScenario, random: Random) -> tuple[Tick, ...]:
    ticks = [
        Tick(epoch=scenario.start_epoch, quote=scenario.start_quote, pip_size=scenario.pip_size)
    ]
    quote = scenario.start_quote
    with localcontext(_DECIMAL_CONTEXT):
        for index in range(1, scenario.count):
            step = Decimal(random.randrange(-20, 21)) / Decimal("10000")
            quote += step
            if quote <= 0:
                raise InvalidSyntheticScenario("generated quote must remain positive")
            ticks.append(
                Tick(
                    epoch=scenario.start_epoch + index * scenario.interval,
                    quote=quote,
                    pip_size=scenario.pip_size,
                )
            )
    return tuple(ticks)


def _gbm(scenario: SyntheticScenario, random: Random) -> tuple[Tick, ...]:
    ticks = [
        Tick(epoch=scenario.start_epoch, quote=scenario.start_quote, pip_size=scenario.pip_size)
    ]
    quote = scenario.start_quote
    with localcontext(_DECIMAL_CONTEXT):
        for index in range(1, scenario.count):
            shock = _discrete_gaussian(random)
            quote = quote * (Decimal("1") + scenario.drift + scenario.volatility * shock)
            if quote <= 0:
                raise InvalidSyntheticScenario("generated quote must remain positive")
            ticks.append(
                Tick(
                    epoch=scenario.start_epoch + index * scenario.interval,
                    quote=quote,
                    pip_size=scenario.pip_size,
                )
            )
    return tuple(ticks)


def _ornstein_uhlenbeck(scenario: SyntheticScenario, random: Random) -> tuple[Tick, ...]:
    ticks = [
        Tick(epoch=scenario.start_epoch, quote=scenario.start_quote, pip_size=scenario.pip_size)
    ]
    quote = scenario.start_quote
    with localcontext(_DECIMAL_CONTEXT):
        for index in range(1, scenario.count):
            shock = _discrete_gaussian(random)
            quote = (
                quote
                + scenario.reversion_speed * (scenario.mean_level - quote)
                + scenario.volatility * shock
            )
            if quote <= 0:
                raise InvalidSyntheticScenario("generated quote must remain positive")
            ticks.append(
                Tick(
                    epoch=scenario.start_epoch + index * scenario.interval,
                    quote=quote,
                    pip_size=scenario.pip_size,
                )
            )
    return tuple(ticks)


def _uniform_digit(scenario: SyntheticScenario, random: Random) -> tuple[Tick, ...]:
    pip_size = _require_pip_size(scenario)
    ticks: list[Tick] = []
    for index in range(scenario.count):
        ticks.append(
            _digit_tick(
                scenario,
                scenario.start_epoch + index * scenario.interval,
                random.randrange(10),
                pip_size,
            )
        )
    return tuple(ticks)


def _markov_parity(scenario: SyntheticScenario, random: Random) -> tuple[Tick, ...]:
    pip_size = _require_pip_size(scenario)
    even_digits = (0, 2, 4, 6, 8)
    odd_digits = (1, 3, 5, 7, 9)
    stay_threshold = int(scenario.parity_persistence * _PARITY_QUANTUM)
    parity_is_even = random.randrange(2) == 0
    ticks: list[Tick] = []
    for index in range(scenario.count):
        if index > 0 and random.randrange(_PARITY_QUANTUM) >= stay_threshold:
            parity_is_even = not parity_is_even
        digits = even_digits if parity_is_even else odd_digits
        ticks.append(
            _digit_tick(
                scenario,
                scenario.start_epoch + index * scenario.interval,
                digits[random.randrange(5)],
                pip_size,
            )
        )
    return tuple(ticks)


def _volatility_regime(scenario: SyntheticScenario, random: Random) -> tuple[Tick, ...]:
    magnitudes: list[int] = []
    for magnitude, length in scenario.regimes:
        magnitudes.extend([magnitude] * length)
    if len(magnitudes) < scenario.count - 1:
        raise InvalidSyntheticScenario("regime lengths must cover the requested tick count")
    ticks = [
        Tick(epoch=scenario.start_epoch, quote=scenario.start_quote, pip_size=scenario.pip_size)
    ]
    quote = scenario.start_quote
    with localcontext(_DECIMAL_CONTEXT):
        for index in range(1, scenario.count):
            step = Decimal(
                random.randrange(-magnitudes[index - 1], magnitudes[index - 1] + 1)
            ) / Decimal("10000")
            quote += step
            if quote <= 0:
                raise InvalidSyntheticScenario("generated quote must remain positive")
            ticks.append(
                Tick(
                    epoch=scenario.start_epoch + index * scenario.interval,
                    quote=quote,
                    pip_size=scenario.pip_size,
                )
            )
    return tuple(ticks)


_Generator = Callable[[SyntheticScenario, Random], tuple[Tick, ...]]

_GENERATORS: dict[SyntheticProcess, _Generator] = {
    SyntheticProcess.RANDOM_WALK: _random_walk,
    SyntheticProcess.GBM: _gbm,
    SyntheticProcess.ORNSTEIN_UHLENBECK: _ornstein_uhlenbeck,
    SyntheticProcess.UNIFORM_DIGIT: _uniform_digit,
    SyntheticProcess.MARKOV_PARITY: _markov_parity,
    SyntheticProcess.VOLATILITY_REGIME: _volatility_regime,
}


def generate_scenario(scenario: SyntheticScenario) -> tuple[Tick, ...]:
    """Generate a deterministic, provider-independent tick sequence from a scenario."""
    random = Random(scenario.seed)
    generator = _GENERATORS.get(scenario.process)
    if generator is None:
        raise InvalidSyntheticScenario(f"unsupported synthetic process {scenario.process.value}")
    return generator(scenario, random)
