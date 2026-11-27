"""ACCU reconstruction verification orchestration (S4.1).

Read-only end-to-end verification: observe ACCU proposals (barrier band and
``ticks_stayed_in`` counter statistics), fetch bounded historical ticks, and
reconstruct streaks under the moving-barrier semantics. The reconstructed streak
distribution is compared against the provider's counter statistics and a
conservative, deterministic fidelity classification is returned.

Everything is in memory; nothing is persisted and no buy/sell payload is ever
constructed.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from statistics import mean, median
from typing import Any

from devsoul_quant.adapters.deriv.accu_proposal import AccumulatorProposal
from devsoul_quant.adapters.deriv.history import HistoryResult
from devsoul_quant.domain.accumulator import reconstruct_streaks, split_continuous_segments

_CLASSIFICATIONS = frozenset(
    {
        "ACCU_RECONSTRUCTION_VERIFIED_FOR_OBSERVED_WINDOWS",
        "ACCU_RECONSTRUCTION_PARTIAL",
        "ACCU_PROXY_ONLY",
        "ACCU_TECHNICAL_BLOCKED",
        "ACCU_DATA_POLICY_BLOCKED",
    }
)


@dataclass(frozen=True, slots=True)
class AccuVerification:
    """Compact, aggregate-only verification result (no raw ticks or proposals)."""

    classification: str
    decision_reasons: tuple[str, ...]
    symbol: str
    proposals: int
    history_ticks: int
    history_pages: int
    discontinuities: int
    ended_early: bool
    barrier_fraction: str | None
    observed_summary: dict[str, Any]
    reconstructed_summary: dict[str, Any]


def _summary(lengths: Sequence[int]) -> dict[str, Any]:
    if not lengths:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": len(lengths),
        "min": min(lengths),
        "max": max(lengths),
        "mean": round(mean(lengths), 3),
        "median": median(lengths),
    }


def _max_cdf_gap(observed: Sequence[int], reconstructed: Sequence[int]) -> float:
    support = sorted(set(observed) | set(reconstructed))

    def cdf(values: Sequence[int]) -> Callable[[int], float]:
        ordered = sorted(values)
        total = len(ordered)
        return lambda x: bisect_right(ordered, x) / total

    observed_cdf = cdf(observed)
    reconstructed_cdf = cdf(reconstructed)
    return max(abs(observed_cdf(x) - reconstructed_cdf(x)) for x in support)


def _classify(
    observed: Sequence[int],
    reconstructed: Sequence[int],
) -> tuple[str, tuple[str, ...]]:
    if not observed or not reconstructed:
        return "ACCU_PROXY_ONLY", ("INSUFFICIENT_OBSERVATIONS",)
    gap = _max_cdf_gap(observed, reconstructed)
    if gap <= 0.15:
        return "ACCU_RECONSTRUCTION_VERIFIED_FOR_OBSERVED_WINDOWS", ("STREAK_DISTRIBUTION_MATCHES",)
    if gap <= 0.35:
        return "ACCU_RECONSTRUCTION_PARTIAL", ("PARTIAL_STREAK_CORRESPONDENCE",)
    return "ACCU_PROXY_ONLY", ("NO_RELIABLE_STREAK_CORRESPONDENCE",)


def verify_accumulator(
    *,
    symbol: str,
    growth_rate: Decimal,
    stake: Decimal,
    cadence_seconds: int,
    max_proposals: int,
    history_total_count: int,
    deadline_remaining: float | None,
    resolve_url: Callable[[], str],
    propose: Callable[[str, str, Decimal, Decimal], AccumulatorProposal],
    fetch_history: Callable[..., HistoryResult],
) -> AccuVerification:
    """Run the read-only ACCU reconstruction verification."""
    barrier_fractions: list[Decimal] = []
    observed: list[int] = []
    proposals = 0
    for _ in range(max_proposals):
        try:
            proposal = propose(resolve_url(), symbol, growth_rate, stake)
        except Exception:
            break
        proposals += 1
        barrier_fractions.append(proposal.barrier_fraction)
        observed.extend(proposal.ticks_stayed_in)

    if not barrier_fractions:
        return AccuVerification(
            classification="ACCU_TECHNICAL_BLOCKED",
            decision_reasons=("NO_ACCU_PROPOSAL_OBSERVED",),
            symbol=symbol,
            proposals=0,
            history_ticks=0,
            history_pages=0,
            discontinuities=0,
            ended_early=False,
            barrier_fraction=None,
            observed_summary=_summary(()),
            reconstructed_summary=_summary(()),
        )

    barrier = barrier_fractions[0]
    barrier_consistent = all(value == barrier for value in barrier_fractions)

    history = fetch_history(
        resolve_url,
        symbol,
        total_count=history_total_count,
        cadence_seconds=cadence_seconds,
        deadline_remaining=deadline_remaining,
    )

    reconstructed: list[int] = []
    for segment in split_continuous_segments(history.ticks, cadence_seconds):
        reconstructed.extend(streak.length for streak in reconstruct_streaks(segment, barrier))

    classification, reasons = _classify(observed, reconstructed)
    all_reasons = list(reasons)
    if not barrier_consistent:
        classification = "ACCU_PROXY_ONLY"
        all_reasons.append("BARRIER_VARIED_ACROSS_PROPOSALS")
    if history.ended_early:
        all_reasons.append("HISTORY_ENDED_EARLY")

    return AccuVerification(
        classification=classification,
        decision_reasons=tuple(all_reasons),
        symbol=symbol,
        proposals=proposals,
        history_ticks=len(history.ticks),
        history_pages=history.pages,
        discontinuities=history.discontinuities,
        ended_early=history.ended_early,
        barrier_fraction=str(barrier),
        observed_summary=_summary(observed),
        reconstructed_summary=_summary(reconstructed),
    )
