"""Synthetic verification of ACCU reconstruction orchestration (S4.1)."""

from decimal import Decimal
from typing import Any

from devsoul_quant.adapters.deriv.accu_proposal import AccumulatorProposal
from devsoul_quant.adapters.deriv.history import HistoryResult
from devsoul_quant.application.accu_verify import (
    _classify,
    completed_fifo_snapshot,
    verify_accumulator,
)
from devsoul_quant.domain.accumulator import reconstruct_streaks
from devsoul_quant.domain.replay import Tick

_BARRIER = Decimal("0.0005")


def _proposal(symbol: str, barrier: Decimal, stayed: tuple[int, ...]) -> AccumulatorProposal:
    return AccumulatorProposal(
        proposal_id="p",
        symbol=symbol,
        growth_rate=Decimal("0.05"),
        barrier_fraction=barrier,
        barrier_percentage=barrier * Decimal("100"),
        high_barrier=Decimal("101"),
        low_barrier=Decimal("99"),
        barrier_spot_distance=Decimal("1"),
        spot=Decimal("100"),
        maximum_ticks=50,
        maximum_payout=Decimal("6000"),
        minimum_stake=Decimal("1"),
        maximum_stake=Decimal("1000"),
        ticks_stayed_in=stayed,
    )


def _streak_ticks() -> tuple[Tick, ...]:
    quotes = (
        "100.00",
        "100.02",
        "100.04",
        "100.10",
        "100.12",
        "100.14",
        "100.20",
        "100.22",
        "100.24",
        "100.30",
    )
    return tuple(Tick(1000 + i * 2, Decimal(quote), pip_size=2) for i, quote in enumerate(quotes))


def test_classify_identical_distributions_is_only_partial() -> None:
    classification, reasons = _classify((1, 1, 2, 2, 3), (1, 1, 2, 2, 3))
    assert classification == "ACCU_RECONSTRUCTION_PARTIAL"
    assert reasons == ("DISTRIBUTIONAL_SIMILARITY_ONLY",)


def test_completed_fifo_snapshot_excludes_the_live_censored_streak() -> None:
    assert completed_fifo_snapshot((4, 7, 11)) == (4, 7)


def test_completed_fifo_snapshot_requires_a_live_tail() -> None:
    assert completed_fifo_snapshot(()) == ()


def test_classify_disjoint_distributions_is_proxy() -> None:
    classification, _ = _classify((1, 2, 3), (100, 200, 300))
    assert classification == "ACCU_PROXY_ONLY"


def test_classify_empty_is_proxy() -> None:
    classification, reasons = _classify((), ())
    assert classification == "ACCU_PROXY_ONLY"
    assert "INSUFFICIENT_OBSERVATIONS" in reasons


def test_verify_no_proposal_is_technically_blocked() -> None:
    def propose(url: str, symbol: str, growth_rate: Decimal, stake: Decimal) -> AccumulatorProposal:
        del url, symbol, growth_rate, stake
        raise RuntimeError("no proposal")

    result = verify_accumulator(
        symbol="R_100",
        growth_rate=Decimal("0.05"),
        stake=Decimal("1"),
        cadence_seconds=2,
        max_proposals=3,
        history_total_count=10,
        deadline_remaining=None,
        resolve_url=lambda: "",
        propose=propose,
        fetch_history=lambda *a, **k: HistoryResult((), 0, 0, False),
    )
    assert result.classification == "ACCU_TECHNICAL_BLOCKED"
    assert result.proposals == 0


def test_verify_end_to_end_matching_streaks() -> None:
    ticks = _streak_ticks()
    reconstructed = tuple(s.length for s in reconstruct_streaks(ticks, _BARRIER))

    def propose(url: str, symbol: str, growth_rate: Decimal, stake: Decimal) -> AccumulatorProposal:
        del url, growth_rate, stake
        return _proposal(symbol, _BARRIER, reconstructed)

    def fetch_history(*args: Any, **kwargs: Any) -> HistoryResult:
        del args, kwargs
        return HistoryResult(ticks=ticks, pages=1, discontinuities=0, ended_early=False)

    result = verify_accumulator(
        symbol="R_100",
        growth_rate=Decimal("0.05"),
        stake=Decimal("1"),
        cadence_seconds=2,
        max_proposals=1,
        history_total_count=10,
        deadline_remaining=None,
        resolve_url=lambda: "",
        propose=propose,
        fetch_history=fetch_history,
    )
    assert result.classification == "ACCU_RECONSTRUCTION_PARTIAL"
    assert result.proposals == 1
    assert result.history_ticks == len(ticks)


def test_verify_does_not_pseudoreplicate_overlapping_fifo_snapshots() -> None:
    ticks = _streak_ticks()
    snapshots = iter(((1, 2, 3, 4), (2, 3, 4, 5)))

    def propose(url: str, symbol: str, growth_rate: Decimal, stake: Decimal) -> AccumulatorProposal:
        del url, growth_rate, stake
        return _proposal(symbol, _BARRIER, next(snapshots))

    result = verify_accumulator(
        symbol="R_100",
        growth_rate=Decimal("0.05"),
        stake=Decimal("1"),
        cadence_seconds=2,
        max_proposals=2,
        history_total_count=10,
        deadline_remaining=None,
        resolve_url=lambda: "",
        propose=propose,
        fetch_history=lambda *a, **k: HistoryResult(ticks, 1, 0, False),
    )

    assert result.observed_summary["count"] == 3
    assert result.observed_summary["max"] == 4


def test_verify_mismatched_streaks_is_proxy() -> None:
    ticks = _streak_ticks()

    def propose(url: str, symbol: str, growth_rate: Decimal, stake: Decimal) -> AccumulatorProposal:
        del url, growth_rate, stake
        return _proposal(symbol, _BARRIER, (500, 600, 700))

    def fetch_history(*args: Any, **kwargs: Any) -> HistoryResult:
        del args, kwargs
        return HistoryResult(ticks=ticks, pages=1, discontinuities=0, ended_early=False)

    result = verify_accumulator(
        symbol="R_100",
        growth_rate=Decimal("0.05"),
        stake=Decimal("1"),
        cadence_seconds=2,
        max_proposals=1,
        history_total_count=10,
        deadline_remaining=None,
        resolve_url=lambda: "",
        propose=propose,
        fetch_history=fetch_history,
    )
    assert result.classification == "ACCU_PROXY_ONLY"


def test_verify_barrier_variation_downgrades_to_proxy() -> None:
    ticks = _streak_ticks()
    reconstructed = tuple(s.length for s in reconstruct_streaks(ticks, _BARRIER))
    barriers = iter((_BARRIER, Decimal("0.0006")))

    def propose(url: str, symbol: str, growth_rate: Decimal, stake: Decimal) -> AccumulatorProposal:
        del url, growth_rate, stake
        return _proposal(symbol, next(barriers), reconstructed)

    def fetch_history(*args: Any, **kwargs: Any) -> HistoryResult:
        del args, kwargs
        return HistoryResult(ticks=ticks, pages=1, discontinuities=0, ended_early=False)

    result = verify_accumulator(
        symbol="R_100",
        growth_rate=Decimal("0.05"),
        stake=Decimal("1"),
        cadence_seconds=2,
        max_proposals=2,
        history_total_count=10,
        deadline_remaining=None,
        resolve_url=lambda: "",
        propose=propose,
        fetch_history=fetch_history,
    )
    assert result.classification == "ACCU_PROXY_ONLY"
    assert "BARRIER_VARIED_ACROSS_PROPOSALS" in result.decision_reasons
