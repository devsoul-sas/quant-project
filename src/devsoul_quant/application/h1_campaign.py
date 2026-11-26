"""S3.11/H1 — autonomous step-direction shadow campaign runner.

Runs a single bounded shadow campaign: it feeds collected ticks to the H1
prequential evaluator until the frozen session deadline elapses or the tick
source is exhausted, then returns only the in-memory result. No early stopping
on favourable results and no extension after the deadline. On any collection or
sequence failure it fails closed to ``H1_TECHNICAL_BLOCKED`` without surfacing
provider details.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from devsoul_quant.application.campaign_spec import CampaignSpec
from devsoul_quant.application.session_deadline import SessionDeadline
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.step_direction import (
    InvalidStepDirection,
    StepDirectionModelMetrics,
    StepDirectionPrequentialEvaluator,
    StepDirectionResult,
)

CollectTicks = Callable[[int, float], Sequence[Tick]]

_BATCH_SIZE = 512


def run_h1_campaign(
    *,
    spec: CampaignSpec,
    collect_ticks: CollectTicks,
    monotonic: Callable[[], float] = time.monotonic,
) -> StepDirectionResult:
    """Run one bounded campaign and return only its ephemeral result."""
    deadline = SessionDeadline(session_seconds=spec.maximum_duration_seconds, monotonic=monotonic)
    evaluator = StepDirectionPrequentialEvaluator(
        warmup_transitions=spec.warmup_labels,
        seed=spec.seed,
        cadence=spec.tick_cadence_seconds,
    )
    total_collected = 0
    try:
        while deadline.remaining() > 0:
            batch = collect_ticks(_BATCH_SIZE, deadline.remaining())
            if not batch:
                break
            total_collected += len(batch)
            for tick in batch:
                evaluator.observe_tick(tick)
        if total_collected == 0:
            return _blocked("H1_TECHNICAL_BLOCKED", "NO_TICKS_COLLECTED")
        return evaluator.finalize()
    except InvalidStepDirection:
        return _blocked("H1_TECHNICAL_BLOCKED", "INVALID_STEP_SEQUENCE")
    except Exception:
        return _blocked("H1_TECHNICAL_BLOCKED", "COLLECTION_FAILED")
    finally:
        evaluator.clear()


def _blocked(classification: str, reason: str) -> StepDirectionResult:
    empty_models = tuple(
        StepDirectionModelMetrics(
            model=name, observations=0, brier_score=None, log_loss=None, accuracy=None
        )
        for name in ("MEMORYLESS", "FREQUENCY_CAUSAL", "MARKOV_1", "MARKOV_1_ADAPTIVE")
    )
    return StepDirectionResult(
        classification=classification,
        decision_reasons=(reason,),
        ticks_received=0,
        warmup_transitions=0,
        valid_transitions=0,
        flat_transitions=0,
        discontinuous_transitions=0,
        nominal_cadence=None,
        effective_sample_size=None,
        warmup_p_up=None,
        causal_p_up=None,
        transition_matrix=None,
        lag1_chi_square=None,
        models=empty_models,
        improvement_memoryless_adaptive=None,
        improvement_memoryless_markov=None,
        improvement_causal_adaptive=None,
        first_half_improvement=None,
        second_half_improvement=None,
        bootstrap_lower_bound=None,
        p_marginal=None,
        p_lag1=None,
        holm_significant_marginal=False,
        holm_significant_lag1=False,
        economic_eligibility="UNAVAILABLE",
        contractual_correspondence="RISE_FALL_TICK_EXIT_VS_ENTRY_SHADOW_ONLY",
    )
