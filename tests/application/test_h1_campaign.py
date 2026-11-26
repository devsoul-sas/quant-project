"""S3.11/H1 — campaign runner tests."""

import random
from decimal import Decimal

from devsoul_quant.application.campaign_spec import CampaignSpec
from devsoul_quant.application.h1_campaign import run_h1_campaign
from devsoul_quant.domain.replay import Tick


def _spec(duration_seconds: int = 14400, cadence: int | None = 2) -> CampaignSpec:
    return CampaignSpec(
        campaign_id="H1_STEP_SHADOW_001",
        protocol="docs/research/s3.9-protocol-step-direction-v1.md",
        protocol_hash="0e954428fa25caa4d3b526a81ace39a789400c21775fd5f44ea57ba8d3024610",
        amendment="docs/research/s3.10-protocol-amendment-001.md",
        amendment_hash="c08a987e8ce5cdb8a8c7c7807e6f4ee378838b53c2bcf5b017ba556178797f4e",
        instrument="stpRNG",
        hypothesis="STEP_DIRECTION_DEPENDENCE_V1",
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


def _synthetic_collect(total_ticks: int, *, cadence: int = 2, seed: int = 7):
    """Return a collect callback that yields ``total_ticks`` i.i.d. ticks in batches."""
    generator = random.Random(seed)
    epoch = 1
    quote = Decimal("100.00")

    def collect(count: int, remaining: float) -> tuple[Tick, ...]:
        nonlocal total_ticks, epoch, quote
        if total_ticks <= 0:
            return ()
        take = min(count, total_ticks)
        total_ticks -= take
        ticks: list[Tick] = []
        for _ in range(take):
            direction = generator.randrange(2)
            quote += Decimal("0.10") if direction else -Decimal("0.10")
            epoch += cadence
            ticks.append(Tick(epoch, quote, pip_size=1))
        return tuple(ticks)

    return collect


def test_dry_run_produces_an_allowed_classification() -> None:
    result = run_h1_campaign(
        spec=_spec(),
        collect_ticks=_synthetic_collect(7400, cadence=2, seed=7),
    )
    assert result.classification in {
        "H1_NO_EDGE",
        "H1_INSUFFICIENT_EVIDENCE",
        "H1_CANDIDATE_FOR_INDEPENDENT_VALIDATION",
    }
    assert result.valid_transitions > 0


def test_no_ticks_is_technically_blocked() -> None:
    result = run_h1_campaign(spec=_spec(), collect_ticks=lambda count, remaining: ())
    assert result.classification == "H1_TECHNICAL_BLOCKED"
    assert result.decision_reasons == ("NO_TICKS_COLLECTED",)


def test_collection_failure_fails_closed() -> None:
    def failing(count: int, remaining: float) -> tuple[Tick, ...]:
        raise RuntimeError("authenticated-url-must-not-leak")

    result = run_h1_campaign(spec=_spec(), collect_ticks=failing)
    assert result.classification == "H1_TECHNICAL_BLOCKED"
    assert result.decision_reasons == ("COLLECTION_FAILED",)
