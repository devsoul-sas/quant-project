"""S3.10/F declarative campaign spec validation tests."""

from decimal import Decimal

import pytest

from devsoul_quant.application.campaign_spec import (
    CampaignSpec,
    InvalidCampaignSpec,
    load_campaign_spec,
)


def _valid_spec() -> dict[str, object]:
    return {
        "campaign_id": "H1_STEP_SHADOW_001",
        "protocol": "docs/research/s3.9-protocol-step-direction-v1.md",
        "protocol_hash": "0e954428fa25caa4d3b526a81ace39a789400c21775fd5f44ea57ba8d3024610",
        "instrument": "stpRNG",
        "hypothesis": "STEP_DIRECTION_DEPENDENCE_V1",
        "mode": "SHADOW_TRADING",
        "maximum_duration_seconds": 3600,
        "warmup_labels": 120,
        "minimum_sample_size": 1200,
        "seed": 42,
        "baselines": ("MEMORYLESS", "FREQUENCY_CAUSAL"),
        "metrics": ("BRIER", "LOG_LOSS"),
        "gates": ("IMPROVEMENT_GATE", "ECONOMIC_GATE"),
        "fixed_stake": Decimal("0.01"),
        "maximum_contracts": 0,
        "maximum_session_loss": Decimal("0.00"),
        "data_policy": "EPHEMERAL_ONLY",
        "stop_conditions": ("SESSION_DEADLINE", "MINIMUM_SAMPLE"),
    }


def test_loads_a_complete_valid_spec() -> None:
    spec = load_campaign_spec(_valid_spec())
    assert isinstance(spec, CampaignSpec)
    assert spec.campaign_id == "H1_STEP_SHADOW_001"
    assert spec.mode == "SHADOW_TRADING"
    assert spec.baselines == ("MEMORYLESS", "FREQUENCY_CAUSAL")


def test_rejects_credential_keys() -> None:
    raw = _valid_spec()
    raw["token"] = "secret-token"
    with pytest.raises(InvalidCampaignSpec, match="token"):
        load_campaign_spec(raw)


def test_rejects_market_data_keys() -> None:
    raw = _valid_spec()
    raw["ticks"] = [1, 2, 3]
    with pytest.raises(InvalidCampaignSpec, match="ticks"):
        load_campaign_spec(raw)


def test_rejects_an_invalid_mode() -> None:
    raw = _valid_spec()
    raw["mode"] = "REAL_TRADING"
    with pytest.raises(InvalidCampaignSpec, match="mode"):
        load_campaign_spec(raw)


def test_rejects_a_duration_at_or_above_the_24h_ceiling() -> None:
    raw = _valid_spec()
    raw["maximum_duration_seconds"] = 24 * 60 * 60
    with pytest.raises(InvalidCampaignSpec, match="maximum_duration_seconds"):
        load_campaign_spec(raw)


def test_rejects_empty_baselines_and_stop_conditions() -> None:
    raw = _valid_spec()
    raw["baselines"] = ()
    with pytest.raises(InvalidCampaignSpec, match="baselines"):
        load_campaign_spec(raw)

    raw = _valid_spec()
    raw["stop_conditions"] = ()
    with pytest.raises(InvalidCampaignSpec, match="stop_conditions"):
        load_campaign_spec(raw)
