"""S3.11/H1 — autonomous step-direction shadow campaign runner (S3.12.1 hotfix).

Runs a single bounded shadow campaign: it feeds collected ticks to the H1
prequential evaluator until the frozen session deadline elapses or the tick
source is exhausted, then returns only the in-memory result. A normal deadline
expiry evaluates the valid observations already collected; it never discards
them. Genuine failures fail closed to ``H1_TECHNICAL_BLOCKED`` with an explicit
stop reason, the real counters observed so far, and a sanitized operational
diagnostic (no provider tokens, OTP URLs, payloads or restricted data).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import replace

from devsoul_quant.adapters.deriv.client import CollectionTimeout, DerivClientError
from devsoul_quant.application.campaign_spec import CampaignSpec
from devsoul_quant.application.session_deadline import SessionDeadline
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.step_direction import (
    InvalidStepDirection,
    OperationalDiagnostic,
    StepDirectionPrequentialEvaluator,
    StepDirectionResult,
)

CollectTicks = Callable[[int, float], tuple[Sequence[Tick], int]]

_BATCH_SIZE = 512

SESSION_DEADLINE_REACHED = "SESSION_DEADLINE_REACHED"
FEED_EXHAUSTED = "FEED_EXHAUSTED"
COLLECTION_TIMEOUT = "COLLECTION_TIMEOUT"
CONNECTION_FAILED = "CONNECTION_FAILED"
INVALID_SEQUENCE = "INVALID_SEQUENCE"
EVALUATION_FAILED = "EVALUATION_FAILED"
INTERNAL_ERROR = "INTERNAL_ERROR"


def run_h1_campaign(
    *,
    spec: CampaignSpec,
    collect_ticks: CollectTicks,
    monotonic: Callable[[], float] = time.monotonic,
) -> StepDirectionResult:
    """Run one bounded campaign and return only its ephemeral result.

    ``collect_ticks`` returns ``(ticks, reconnections)`` per batch. The runner
    aggregates reconnections for the operational diagnostic and evaluates any
    observations collected before a normal deadline expiry.
    """
    deadline = SessionDeadline(session_seconds=spec.maximum_duration_seconds, monotonic=monotonic)
    evaluator = StepDirectionPrequentialEvaluator(
        warmup_transitions=spec.warmup_labels,
        seed=spec.seed,
        cadence=spec.tick_cadence_seconds,
    )
    completed_batches = 0
    reconnections = 0
    phase = "collecting"
    try:
        while deadline.remaining() > 0:
            batch, reconnects = collect_ticks(_BATCH_SIZE, deadline.remaining())
            reconnections += reconnects
            if not batch:
                break
            completed_batches += 1
            for tick in batch:
                evaluator.observe_tick(tick)

        phase = "finalizing"
        try:
            result = evaluator.finalize()
        except Exception:
            return evaluator.blocked_result(
                "H1_TECHNICAL_BLOCKED",
                (EVALUATION_FAILED,),
                diagnostic=OperationalDiagnostic(
                    phase, EVALUATION_FAILED, completed_batches, reconnections, False
                ),
            )
        deadline_reached = deadline.remaining() <= 0
        stop_reason = SESSION_DEADLINE_REACHED if deadline_reached else FEED_EXHAUSTED
        return replace(
            result,
            operational_diagnostic=OperationalDiagnostic(
                phase, stop_reason, completed_batches, reconnections, deadline_reached
            ),
        )
    except InvalidStepDirection:
        return evaluator.blocked_result(
            "H1_TECHNICAL_BLOCKED",
            (INVALID_SEQUENCE,),
            diagnostic=OperationalDiagnostic(
                phase, INVALID_SEQUENCE, completed_batches, reconnections, False
            ),
        )
    except CollectionTimeout:
        return evaluator.blocked_result(
            "H1_TECHNICAL_BLOCKED",
            (COLLECTION_TIMEOUT,),
            diagnostic=OperationalDiagnostic(
                phase, COLLECTION_TIMEOUT, completed_batches, reconnections, False
            ),
        )
    except DerivClientError:
        return evaluator.blocked_result(
            "H1_TECHNICAL_BLOCKED",
            (CONNECTION_FAILED,),
            diagnostic=OperationalDiagnostic(
                phase, CONNECTION_FAILED, completed_batches, reconnections, False
            ),
        )
    except Exception:
        return evaluator.blocked_result(
            "H1_TECHNICAL_BLOCKED",
            (INTERNAL_ERROR,),
            diagnostic=OperationalDiagnostic(
                phase, INTERNAL_ERROR, completed_batches, reconnections, False
            ),
        )
    finally:
        evaluator.clear()
