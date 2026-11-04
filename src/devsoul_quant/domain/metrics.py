"""Evidence-graded evaluation metrics without economic overclaim."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from random import Random

from devsoul_quant.domain.contracts import ContractAction
from devsoul_quant.domain.replay import EconomyProvenance, Outcome

_DECIMAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)


class EvidenceMode(StrEnum):
    """Provenance label for the evidence being evaluated."""

    TICK_PROXY_BACKTEST = "TICK_PROXY_BACKTEST"
    QUOTE_REPLAY_BACKTEST = "QUOTE_REPLAY_BACKTEST"


class PromotionEligibility(StrEnum):
    """Whether evidence may promote a strategy toward live/demo execution."""

    NOT_ELIGIBLE = "NOT_ELIGIBLE"


_PROMOTION_MATRIX: dict[EvidenceMode, PromotionEligibility] = {
    EvidenceMode.TICK_PROXY_BACKTEST: PromotionEligibility.NOT_ELIGIBLE,
    EvidenceMode.QUOTE_REPLAY_BACKTEST: PromotionEligibility.NOT_ELIGIBLE,
}


class InvalidEvaluation(ValueError):
    """Raised when evaluation inputs are empty, malformed, or mixed."""


def promotion_eligibility(mode: EvidenceMode) -> PromotionEligibility:
    """Return the promotion path for an evidence mode, failing closed."""
    return _PROMOTION_MATRIX.get(mode, PromotionEligibility.NOT_ELIGIBLE)


def _round(value: Decimal, places: int) -> Decimal:
    quantum = Decimal(1).scaleb(-places)
    with localcontext(_DECIMAL_CONTEXT):
        return value.quantize(quantum, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class TrialOutcome:
    """One directional decision and its settlement, with economic provenance."""

    decision: ContractAction
    outcome: Outcome | None
    provenance: EconomyProvenance = EconomyProvenance.UNAVAILABLE

    def __post_init__(self) -> None:
        if self.decision is ContractAction.ENTER_CONTRACT:
            if self.outcome is None:
                raise InvalidEvaluation("entered trials must carry an outcome")
        elif self.decision is ContractAction.NO_TRADE:
            if self.outcome is not None:
                raise InvalidEvaluation("no-trade trials must not carry an outcome")
        else:
            raise InvalidEvaluation("unsupported decision action")


@dataclass(frozen=True, slots=True)
class BootstrapInterval:
    """Deterministic confidence interval for directional hit rate."""

    lower: Decimal
    upper: Decimal


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Engineering evidence only; no economic metrics are present by construction."""

    evidence_mode: EvidenceMode
    decisions: int
    enter_count: int
    wait_count: int
    wait_rate: Decimal | None
    directional_hit_rate: Decimal | None
    longest_loss_streak: int
    fold_hit_rates: tuple[Decimal, ...]
    fold_consistency: Decimal | None
    bootstrap_interval: BootstrapInterval | None
    promotion_eligibility: PromotionEligibility
    economic_metrics_available: bool

    def to_dict(self) -> dict[str, object]:
        interval: dict[str, str] | None
        if self.bootstrap_interval is None:
            interval = None
        else:
            interval = {
                "lower": format(self.bootstrap_interval.lower, "f"),
                "upper": format(self.bootstrap_interval.upper, "f"),
            }
        return {
            "evidence_mode": self.evidence_mode.value,
            "decisions": self.decisions,
            "enter_count": self.enter_count,
            "wait_count": self.wait_count,
            "wait_rate": None if self.wait_rate is None else format(self.wait_rate, "f"),
            "directional_hit_rate": (
                None
                if self.directional_hit_rate is None
                else format(self.directional_hit_rate, "f")
            ),
            "longest_loss_streak": self.longest_loss_streak,
            "fold_hit_rates": [format(value, "f") for value in self.fold_hit_rates],
            "fold_consistency": (
                None if self.fold_consistency is None else format(self.fold_consistency, "f")
            ),
            "bootstrap_interval": interval,
            "promotion_eligibility": self.promotion_eligibility.value,
            "economic_metrics_available": self.economic_metrics_available,
        }


def _block_bootstrap(
    hits: list[bool],
    seed: int,
    *,
    block_size: int = 2,
    resamples: int = 200,
) -> BootstrapInterval:
    random = Random(seed)
    total = len(hits)
    estimates: list[Decimal] = []
    for _ in range(resamples):
        sample_hits: list[bool] = []
        drawn = 0
        while drawn < total:
            start = random.randrange(total)
            for offset in range(block_size):
                if drawn >= total:
                    break
                sample_hits.append(hits[(start + offset) % total])
                drawn += 1
        estimates.append(Decimal(sum(sample_hits)) / Decimal(total))
    sorted_estimates = sorted(estimates)
    lower = sorted_estimates[int(0.025 * (len(sorted_estimates) - 1))]
    upper = sorted_estimates[int(0.975 * (len(sorted_estimates) - 1))]
    return BootstrapInterval(lower=_round(lower, 4), upper=_round(upper, 4))


def evaluate(
    *,
    folds: Sequence[Sequence[TrialOutcome]],
    evidence_mode: EvidenceMode,
    seed: int,
    bootstrap_block_size: int = 2,
) -> EvaluationReport:
    """Evaluate directional behavior only; economic metrics are never produced."""
    if type(bootstrap_block_size) is not int or bootstrap_block_size < 1:
        raise InvalidEvaluation("bootstrap_block_size must be a positive integer")
    if not folds:
        raise InvalidEvaluation("evaluation requires at least one fold")
    all_trials = [trial for fold in folds for trial in fold]
    if not all_trials:
        raise InvalidEvaluation("evaluation requires at least one trial")

    provenances = {trial.provenance for trial in all_trials}
    if len(provenances) > 1:
        raise InvalidEvaluation("mixed economic provenance is not allowed")
    if evidence_mode is EvidenceMode.TICK_PROXY_BACKTEST and any(
        trial.provenance is not EconomyProvenance.UNAVAILABLE for trial in all_trials
    ):
        raise InvalidEvaluation("tick-proxy evaluation cannot use observed economics")
    if evidence_mode is EvidenceMode.QUOTE_REPLAY_BACKTEST and any(
        trial.provenance is not EconomyProvenance.OBSERVED for trial in all_trials
    ):
        raise InvalidEvaluation("quote-replay evaluation requires observed economics")

    decisions = len(all_trials)
    entered = [trial for trial in all_trials if trial.decision is ContractAction.ENTER_CONTRACT]
    enter_count = len(entered)
    wait_count = decisions - enter_count
    wait_rate = None if decisions == 0 else _round(Decimal(wait_count) / Decimal(decisions), 4)

    wins = sum(1 for trial in entered if trial.outcome is Outcome.WIN)
    hit_rate = None if not entered else _round(Decimal(wins) / Decimal(len(entered)), 4)

    longest = 0
    current = 0
    for trial in all_trials:
        if trial.decision is ContractAction.ENTER_CONTRACT and trial.outcome is Outcome.LOSS:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    fold_hit_rates: list[Decimal] = []
    for fold in folds:
        fold_entered = [trial for trial in fold if trial.decision is ContractAction.ENTER_CONTRACT]
        if fold_entered:
            fold_wins = sum(1 for trial in fold_entered if trial.outcome is Outcome.WIN)
            fold_hit_rates.append(_round(Decimal(fold_wins) / Decimal(len(fold_entered)), 4))
    fold_consistency = None
    if len(fold_hit_rates) >= 2:
        fold_consistency = _round(max(fold_hit_rates) - min(fold_hit_rates), 4)

    hits = [trial.outcome is Outcome.WIN for trial in entered]
    bootstrap_interval = (
        _block_bootstrap(hits, seed, block_size=bootstrap_block_size) if hits else None
    )

    return EvaluationReport(
        evidence_mode=evidence_mode,
        decisions=decisions,
        enter_count=enter_count,
        wait_count=wait_count,
        wait_rate=wait_rate,
        directional_hit_rate=hit_rate,
        longest_loss_streak=longest,
        fold_hit_rates=tuple(fold_hit_rates),
        fold_consistency=fold_consistency,
        bootstrap_interval=bootstrap_interval,
        promotion_eligibility=promotion_eligibility(evidence_mode),
        economic_metrics_available=False,
    )
