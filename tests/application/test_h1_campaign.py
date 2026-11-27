"""S3.11/H1 — campaign runner tests (S3.12.1 collection-lifecycle hotfix)."""

import random
from decimal import Decimal

from devsoul_quant.adapters.deriv.client import CollectionTimeout, DerivClientError
from devsoul_quant.application.campaign_spec import CampaignSpec
from devsoul_quant.application.h1_campaign import run_h1_campaign
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.step_direction import StepDirectionPrequentialEvaluator

_ALLOWED = {"H1_NO_EDGE", "H1_INSUFFICIENT_EVIDENCE", "H1_CANDIDATE_FOR_INDEPENDENT_VALIDATION"}


def _spec(duration_seconds: int = 14400, cadence: int | None = 2) -> CampaignSpec:
    return CampaignSpec(
        campaign_id="H1_STEP_SHADOW_001",
        protocol="docs/research/s3.9-protocol-step-direction-v1.md",
        protocol_hash="0e954428fa25caa4d3b526a81ace39a789400c21775fd5f44ea57ba8d3024610",
        amendment="docs/research/s3.12-protocol-amendment-002.md",
        amendment_hash="c585b38326617ed1adcb476b4a88bcb304f6297b1623bbe3f1495be529647d3c",
        instrument="stpRNG",
        hypothesis="STEP_DIRECTION_DEPENDENCE_V2",
        mode="SHADOW_TRADING",
        maximum_duration_seconds=duration_seconds,
        warmup_labels=120,
        minimum_sample_size=2178,
        tick_cadence_seconds=cadence,
        seed=42,
        baselines=("MEMORYLESS", "FREQUENCY_CAUSAL"),
        metrics=("BRIER", "LOG_LOSS"),
        gates=("IMPROVEMENT_GATE", "HOLM_CORRECTION"),
        fixed_stake=Decimal("0.0"),
        maximum_contracts=0,
        maximum_session_loss=Decimal("0.0"),
        data_policy="EPHEMERAL_ONLY",
        stop_conditions=("SESSION_DEADLINE", "MINIMUM_SAMPLE"),
    )


def _batch(epoch: int, count: int, *, cadence: int = 2, seed: int = 7) -> tuple[Tick, ...]:
    """One batch of i.i.d. ticks starting at ``epoch``, spaced by ``cadence``."""
    generator = random.Random(seed)
    quote = Decimal("100.00")
    ticks: list[Tick] = []
    for index in range(count):
        direction = generator.randrange(2)
        quote += Decimal("0.10") if direction else -Decimal("0.10")
        ticks.append(Tick(epoch + index * cadence, quote, pip_size=1))
    return tuple(ticks)


def _synthetic_collect(total_ticks: int, *, cadence: int = 2, seed: int = 7):
    """Collect callback yielding ``total_ticks`` i.i.d. ticks in batches, no reconnects."""
    remaining_ticks = [total_ticks]
    generator = random.Random(seed)
    epoch = 1
    quote = Decimal("100.00")

    def collect(count: int, remaining: float) -> tuple[tuple[Tick, ...], int]:
        nonlocal epoch, quote
        if remaining_ticks[0] <= 0:
            return (), 0
        take = min(count, remaining_ticks[0])
        remaining_ticks[0] -= take
        ticks: list[Tick] = []
        for _ in range(take):
            direction = generator.randrange(2)
            quote += Decimal("0.10") if direction else -Decimal("0.10")
            epoch += cadence
            ticks.append(Tick(epoch, quote, pip_size=1))
        return tuple(ticks), 0

    return collect


def test_dry_run_produces_an_allowed_classification() -> None:
    result = run_h1_campaign(
        spec=_spec(),
        collect_ticks=_synthetic_collect(7400, cadence=2, seed=7),
    )
    assert result.classification in _ALLOWED
    assert result.valid_transitions > 0
    assert result.operational_diagnostic is not None
    assert result.operational_diagnostic.deadline_reached is False
    assert result.operational_diagnostic.stop_reason == "FEED_EXHAUSTED"


def test_no_ticks_finalizes_as_insufficient_evidence() -> None:
    result = run_h1_campaign(spec=_spec(), collect_ticks=lambda count, remaining: ((), 0))
    assert result.classification == "H1_INSUFFICIENT_EVIDENCE"
    assert result.ticks_received == 0
    assert result.operational_diagnostic.stop_reason == "FEED_EXHAUSTED"


def test_deadline_during_partial_batch_finalizes_available_observations() -> None:
    now = [0.0]

    def monotonic() -> float:
        return now[0]

    spec = _spec(duration_seconds=10)
    calls = [0]

    def collect(count: int, remaining: float) -> tuple[tuple[Tick, ...], int]:
        calls[0] += 1
        if calls[0] == 1:
            now[0] += 4.0
            return _batch(1, 512), 0
        now[0] += 20.0  # deadline elapses mid-batch
        return _batch(1 + 512 * 2, 300), 0

    result = run_h1_campaign(spec=spec, collect_ticks=collect, monotonic=monotonic)

    assert result.classification in _ALLOWED
    diagnostic = result.operational_diagnostic
    assert diagnostic is not None
    assert diagnostic.deadline_reached is True
    assert diagnostic.stop_reason == "SESSION_DEADLINE_REACHED"
    assert diagnostic.completed_batches == 2
    assert result.ticks_received == 812


def test_deadline_before_first_batch_finalizes_empty() -> None:
    calls = [0]

    def monotonic() -> float:
        calls[0] += 1
        return 100.0 if calls[0] > 1 else 0.0

    result = run_h1_campaign(
        spec=_spec(duration_seconds=5),
        collect_ticks=lambda count, remaining: (_batch(1, 10), 0),
        monotonic=monotonic,
    )

    assert result.classification == "H1_INSUFFICIENT_EVIDENCE"
    diagnostic = result.operational_diagnostic
    assert diagnostic is not None
    assert diagnostic.deadline_reached is True
    assert diagnostic.stop_reason == "SESSION_DEADLINE_REACHED"
    assert diagnostic.completed_batches == 0
    assert result.ticks_received == 0


def test_connection_error_after_batches_fails_closed_with_real_counters() -> None:
    calls = [0]

    def collect(count: int, remaining: float) -> tuple[tuple[Tick, ...], int]:
        calls[0] += 1
        if calls[0] == 1:
            return _batch(1, 512), 0
        if calls[0] == 2:
            return _batch(1 + 512 * 2, 512), 0
        raise DerivClientError("connection lost")

    result = run_h1_campaign(spec=_spec(), collect_ticks=collect)

    assert result.classification == "H1_TECHNICAL_BLOCKED"
    assert result.decision_reasons == ("CONNECTION_FAILED",)
    assert result.ticks_received == 1024
    assert result.operational_diagnostic.stop_reason == "CONNECTION_FAILED"
    assert result.operational_diagnostic.completed_batches == 2
    assert result.effective_sample_size is None
    assert result.improvement_causal_adaptive is None


def test_collection_timeout_is_differentiated() -> None:
    def collect(count: int, remaining: float) -> tuple[tuple[Tick, ...], int]:
        raise CollectionTimeout("stall")

    result = run_h1_campaign(spec=_spec(), collect_ticks=collect)

    assert result.classification == "H1_TECHNICAL_BLOCKED"
    assert result.decision_reasons == ("COLLECTION_TIMEOUT",)
    assert result.operational_diagnostic.stop_reason == "COLLECTION_TIMEOUT"


def test_invalid_sequence_is_differentiated() -> None:
    bad = (Tick(10, Decimal("100"), pip_size=1), Tick(10, Decimal("101"), pip_size=1))

    def collect(count: int, remaining: float) -> tuple[tuple[Tick, ...], int]:
        return bad, 0

    result = run_h1_campaign(spec=_spec(), collect_ticks=collect)

    assert result.classification == "H1_TECHNICAL_BLOCKED"
    assert result.decision_reasons == ("INVALID_SEQUENCE",)
    assert result.operational_diagnostic.stop_reason == "INVALID_SEQUENCE"


def test_internal_error_is_differentiated() -> None:
    def collect(count: int, remaining: float) -> tuple[tuple[Tick, ...], int]:
        raise ValueError("unexpected")

    result = run_h1_campaign(spec=_spec(), collect_ticks=collect)

    assert result.classification == "H1_TECHNICAL_BLOCKED"
    assert result.decision_reasons == ("INTERNAL_ERROR",)
    assert result.operational_diagnostic.stop_reason == "INTERNAL_ERROR"


def test_reconnection_with_discontinuity_is_handled() -> None:
    calls = [0]

    def collect(count: int, remaining: float) -> tuple[tuple[Tick, ...], int]:
        calls[0] += 1
        if calls[0] == 1:
            return _batch(1, 512), 0
        if calls[0] == 2:
            # Epoch jump (gap != cadence) simulates a reconnect discontinuity.
            return _batch(2000, 512), 1
        return (), 0

    result = run_h1_campaign(spec=_spec(), collect_ticks=collect)

    assert result.classification in _ALLOWED
    assert result.discontinuous_transitions >= 1
    assert result.operational_diagnostic.reconnections == 1
    assert result.operational_diagnostic.stop_reason == "FEED_EXHAUSTED"


def test_error_during_finalize_is_evaluation_failed(monkeypatch) -> None:
    def boom(self) -> object:
        raise RuntimeError("finalize failed")

    monkeypatch.setattr(StepDirectionPrequentialEvaluator, "finalize", boom)

    result = run_h1_campaign(
        spec=_spec(), collect_ticks=_synthetic_collect(7400, cadence=2, seed=7)
    )

    assert result.classification == "H1_TECHNICAL_BLOCKED"
    assert result.decision_reasons == ("EVALUATION_FAILED",)
    assert result.operational_diagnostic.stop_reason == "EVALUATION_FAILED"
    assert result.ticks_received > 0


def test_evaluator_state_is_cleared_in_normal_and_failed_runs(monkeypatch) -> None:
    final_clears: list[int] = []
    original_clear = StepDirectionPrequentialEvaluator.clear

    def spy_clear(self) -> None:
        ticks = getattr(self, "_ticks_received", None)
        if ticks is not None:
            final_clears.append(ticks)
        original_clear(self)

    monkeypatch.setattr(StepDirectionPrequentialEvaluator, "clear", spy_clear)

    run_h1_campaign(spec=_spec(), collect_ticks=_synthetic_collect(7400, cadence=2, seed=7))

    def failing(count: int, remaining: float) -> tuple[tuple[Tick, ...], int]:
        raise DerivClientError("boom")

    run_h1_campaign(spec=_spec(), collect_ticks=failing)

    assert final_clears == [7400, 0]
