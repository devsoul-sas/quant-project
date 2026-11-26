"""S3.10/F + S3.11 declarative campaign spec validation tests."""

from decimal import Decimal

import pytest

from devsoul_quant.application.campaign_spec import (
    CampaignSpec,
    InvalidCampaignSpec,
    load_campaign_spec,
)

_PROTOCOL_HASH = "0e954428fa25caa4d3b526a81ace39a789400c21775fd5f44ea57ba8d3024610"
_AMENDMENT_HASH = "c08a987e8ce5cdb8a8c7c7807e6f4ee378838b53c2bcf5b017ba556178797f4e"


def _valid_spec_json() -> dict[str, object]:
    """A JSON-shaped spec: lists and floats, as produced by json.load."""
    return {
        "campaign_id": "H1_STEP_SHADOW_001",
        "protocol": "docs/research/s3.9-protocol-step-direction-v1.md",
        "protocol_hash": _PROTOCOL_HASH,
        "amendment": "docs/research/s3.10-protocol-amendment-001.md",
        "amendment_hash": _AMENDMENT_HASH,
        "instrument": "stpRNG",
        "hypothesis": "STEP_DIRECTION_DEPENDENCE_V1",
        "mode": "SHADOW_TRADING",
        "maximum_duration_seconds": 14400,
        "warmup_labels": 120,
        "minimum_sample_size": 2178,
        "tick_cadence_seconds": None,
        "seed": 42,
        "baselines": ["MEMORYLESS", "FREQUENCY_CAUSAL"],
        "metrics": ["BRIER", "LOG_LOSS"],
        "gates": ["IMPROVEMENT_GATE", "HOLM_CORRECTION"],
        "fixed_stake": 0.0,
        "maximum_contracts": 0,
        "maximum_session_loss": 0.0,
        "data_policy": "EPHEMERAL_ONLY",
        "stop_conditions": ["SESSION_DEADLINE", "MINIMUM_SAMPLE"],
    }


def test_loads_and_coerces_a_json_spec() -> None:
    spec = load_campaign_spec(_valid_spec_json())
    assert isinstance(spec, CampaignSpec)
    assert spec.campaign_id == "H1_STEP_SHADOW_001"
    assert spec.mode == "SHADOW_TRADING"
    assert spec.hypothesis == "STEP_DIRECTION_DEPENDENCE_V1"
    assert spec.amendment_hash == _AMENDMENT_HASH
    assert spec.baselines == ("MEMORYLESS", "FREQUENCY_CAUSAL")
    assert spec.stop_conditions == ("SESSION_DEADLINE", "MINIMUM_SAMPLE")
    assert spec.fixed_stake == Decimal("0.0")
    assert spec.maximum_session_loss == Decimal("0.0")
    assert spec.maximum_duration_seconds == 14400
    assert spec.minimum_sample_size == 2178
    assert spec.tick_cadence_seconds is None


def test_rejects_credential_keys() -> None:
    raw = _valid_spec_json()
    raw["token"] = "secret-token"
    with pytest.raises(InvalidCampaignSpec, match="token"):
        load_campaign_spec(raw)


def test_rejects_market_data_keys() -> None:
    raw = _valid_spec_json()
    raw["ticks"] = [1, 2, 3]
    with pytest.raises(InvalidCampaignSpec, match="ticks"):
        load_campaign_spec(raw)


def test_rejects_an_invalid_mode() -> None:
    raw = _valid_spec_json()
    raw["mode"] = "REAL_TRADING"
    with pytest.raises(InvalidCampaignSpec, match="mode"):
        load_campaign_spec(raw)


def test_rejects_an_unfrozen_hypothesis() -> None:
    raw = _valid_spec_json()
    raw["hypothesis"] = "JUMP_DIGIT_DISTRIBUTION_V1"
    with pytest.raises(InvalidCampaignSpec, match="hypothesis"):
        load_campaign_spec(raw)


def test_accepts_v2_hypothesis() -> None:
    raw = _valid_spec_json()
    raw["hypothesis"] = "STEP_DIRECTION_DEPENDENCE_V2"
    spec = load_campaign_spec(raw)
    assert spec.hypothesis == "STEP_DIRECTION_DEPENDENCE_V2"


def test_rejects_a_duration_at_or_above_the_24h_ceiling() -> None:
    raw = _valid_spec_json()
    raw["maximum_duration_seconds"] = 24 * 60 * 60
    with pytest.raises(InvalidCampaignSpec, match="maximum_duration_seconds"):
        load_campaign_spec(raw)


def test_rejects_empty_baselines_and_stop_conditions() -> None:
    raw = _valid_spec_json()
    raw["baselines"] = []
    with pytest.raises(InvalidCampaignSpec, match="baselines"):
        load_campaign_spec(raw)

    raw = _valid_spec_json()
    raw["stop_conditions"] = []
    with pytest.raises(InvalidCampaignSpec, match="stop_conditions"):
        load_campaign_spec(raw)


@pytest.mark.parametrize(
    "field,value",
    (
        ("fixed_stake", True),
        ("fixed_stake", []),
        ("fixed_stake", "not-a-number"),
        ("maximum_session_loss", True),
        ("maximum_contracts", True),
        ("maximum_contracts", 2.5),
        ("maximum_duration_seconds", 14400.5),
        ("seed", "42"),
        ("tick_cadence_seconds", 0),
        ("tick_cadence_seconds", 2.5),
        ("baselines", "MEMORYLESS"),
        ("baselines", ["MEMORYLESS", 3]),
        ("metrics", ["BRIER", ""]),
        ("campaign_id", "   "),
        ("fixed_stake", -0.01),
    ),
)
def test_rejects_invalid_field_types_and_values(field: str, value: object) -> None:
    raw = _valid_spec_json()
    raw[field] = value
    with pytest.raises(InvalidCampaignSpec):
        load_campaign_spec(raw)


def test_rejects_non_mapping_spec() -> None:
    with pytest.raises(InvalidCampaignSpec, match="mapping"):
        load_campaign_spec(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_accepts_typed_decimal_and_tuple_values() -> None:
    raw = _valid_spec_json()
    raw["fixed_stake"] = Decimal("0.01")
    raw["maximum_session_loss"] = Decimal("0.00")
    raw["baselines"] = ("MEMORYLESS", "FREQUENCY_CAUSAL")
    spec = load_campaign_spec(raw)
    assert spec.fixed_stake == Decimal("0.01")
    assert spec.baselines == ("MEMORYLESS", "FREQUENCY_CAUSAL")
