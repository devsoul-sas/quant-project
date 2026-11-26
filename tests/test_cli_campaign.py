"""CLI coverage for the frozen campaign runner."""

import json
from io import StringIO
from pathlib import Path

import pytest

from devsoul_quant.cli import main

_PROTOCOL_HASH = "0e954428fa25caa4d3b526a81ace39a789400c21775fd5f44ea57ba8d3024610"
_AMENDMENT_HASH = "c08a987e8ce5cdb8a8c7c7807e6f4ee378838b53c2bcf5b017ba556178797f4e"


def _spec_json() -> dict[str, object]:
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
        "tick_cadence_seconds": 2,
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


def _write_spec(tmp_path: Path, spec: dict[str, object]) -> Path:
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def test_campaign_dry_run_emits_a_classification(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path, _spec_json())
    output = StringIO()

    code = main(
        ["campaign", "--spec", str(spec_path), "--dry-run", "--dry-run-ticks", "100"],
        stdout=output,
    )

    rendered = output.getvalue()
    assert code == 0
    assert '"type": "final"' in rendered
    assert '"classification"' in rendered


def test_campaign_rejects_a_hash_mismatch(tmp_path: Path) -> None:
    spec = _spec_json()
    spec["protocol_hash"] = "0" * 64
    spec_path = _write_spec(tmp_path, spec)
    output = StringIO()

    code = main(["campaign", "--spec", str(spec_path), "--dry-run"], stdout=output)

    assert code == 2
    assert "hash mismatch" in output.getvalue()


def test_campaign_live_requires_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_TOKEN", raising=False)
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_APP_ID", raising=False)
    spec_path = _write_spec(tmp_path, _spec_json())
    output = StringIO()

    code = main(["campaign", "--spec", str(spec_path)], stdout=output)

    assert code == 2
    assert "demo credentials are not configured" in output.getvalue()


def test_campaign_rejects_missing_spec_file(tmp_path: Path) -> None:
    output = StringIO()
    code = main(["campaign", "--spec", str(tmp_path / "missing.json"), "--dry-run"], stdout=output)
    assert code == 2


def test_campaign_v2_spec_dry_runs() -> None:
    """The frozen V2 spec (adaptive hypothesis + amendment 002) resolves its hash
    chain and emits a classification with the causal-adaptive gate metric."""
    spec_path = Path("examples/campaign-h1-v2-step.json")
    output = StringIO()

    code = main(
        ["campaign", "--spec", str(spec_path), "--dry-run", "--dry-run-ticks", "300"],
        stdout=output,
    )

    rendered = output.getvalue()
    assert code == 0
    assert '"classification"' in rendered
    assert '"improvement_causal_adaptive"' in rendered
