"""Prepare temporal validation splits and open sealed holdouts."""

from collections.abc import Mapping

from devsoul_quant.application.ports.ledger import LedgerPort
from devsoul_quant.domain.datasets import DatasetSnapshot
from devsoul_quant.domain.experiments import StrategyRelease
from devsoul_quant.domain.ledger import LedgerScalar
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.validation import (
    SealedHoldout,
    TemporalSplit,
    TemporalSplitSpec,
    split_ticks,
)


def prepare_validation(
    *,
    spec: TemporalSplitSpec,
    snapshot: DatasetSnapshot,
    run_id: str,
) -> TemporalSplit:
    """Build a validated walk-forward split over a dataset snapshot."""
    return split_ticks(spec=spec, ticks=snapshot.ticks, run_id=run_id)


def open_holdout(
    *,
    holdout: SealedHoldout,
    ticks: tuple[Tick, ...],
    release: StrategyRelease,
    ledger: LedgerPort,
    run_id: str,
    occurred_at: int,
) -> tuple[Tick, ...]:
    """Open a sealed holdout, appending a ledger event tied to release and run."""

    def record(event_type: str, payload: Mapping[str, LedgerScalar]) -> None:
        sequence = len(ledger.events)
        ledger.append(
            event_id=f"{run_id}:holdout:{sequence:04d}",
            event_type=event_type,
            occurred_at=occurred_at,
            correlation_id=run_id,
            causation_id=ledger.events[-1].event_id if ledger.events else None,
            payload=payload,
        )

    return holdout.open(release, ticks=ticks, record=record)
