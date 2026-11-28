"""Synthetic tests for the versioned S4.4 ACCU experiment specification."""

import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from devsoul_quant.application.accu_experiment_spec import (
    InvalidAccuExperimentSpec,
    load_accu_experiment_spec,
)

_SPEC = Path(__file__).parents[2] / "protocols" / "s4.4-accu-primary-v1.json"


def test_primary_accu_protocol_is_complete_and_hash_stable() -> None:
    raw = json.loads(_SPEC.read_text(encoding="utf-8"))
    first = load_accu_experiment_spec(raw)
    second = load_accu_experiment_spec(raw)

    assert first.spec_hash == second.spec_hash
    assert first.version == "S4.4-ACCU-PRIMARY-V1"
    assert first.symbols == ("R_75",)
    assert first.growth_rates == (Decimal("0.01"), Decimal("0.03"), Decimal("0.05"))
    assert first.primary_horizon == 3
    assert first.maximum_ticks == 40_000
    assert first.maximum_contracts == 0
    assert first.data_policy == "EPHEMERAL_ONLY"
    assert len(first.rules) == 3


def test_accu_protocol_rejects_learned_or_restricted_state() -> None:
    raw = json.loads(_SPEC.read_text(encoding="utf-8"))
    raw["learned_threshold"] = "0.1"
    with pytest.raises(InvalidAccuExperimentSpec, match="forbidden"):
        load_accu_experiment_spec(raw)


def test_accu_protocol_rejects_combinatorial_primary_scope() -> None:
    raw = json.loads(_SPEC.read_text(encoding="utf-8"))
    raw["symbols"] = ["R_100", "R_75", "R_50", "R_25"]
    raw["growth_rates"] = ["0.01", "0.02", "0.03", "0.04", "0.05"]
    with pytest.raises(InvalidAccuExperimentSpec, match="primary combinations"):
        load_accu_experiment_spec(raw)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda raw: raw.update({"symbols": ["R_10"]}), "unsupported"),
        (lambda raw: raw.update({"growth_rates": ["0.06"]}), "growth rates"),
        (lambda raw: raw.update({"horizons": [6], "primary_horizon": 6}), "horizons"),
        (lambda raw: raw.update({"rules": []}), "non-empty sequence"),
        (lambda raw: raw.update({"split": []}), "must be mappings"),
        (
            lambda raw: raw["split"].update({"holdout_fraction": "0.21"}),
            "sum to one",
        ),
        (lambda raw: raw.update({"primary_horizon": 2}), "primary_horizon"),
        (lambda raw: raw.update({"maximum_ticks": True}), "must be an integer"),
        (lambda raw: raw.update({"growth_rates": ["NaN"]}), "must be finite"),
        (lambda raw: raw.update({"binary_float": 0.1}), "binary floats"),
        (
            lambda raw: raw["rules"][0].update({"rule_id": ""}),
            "invalid rule identity",
        ),
        (
            lambda raw: raw["rules"][0].update({"minimum_range_position": "0.9"}),
            "range positions",
        ),
        (
            lambda raw: raw.update({"rules": [raw["rules"][0], raw["rules"][0]]}),
            "unique mappings",
        ),
    ],
)
def test_accu_protocol_fail_closed_validation(
    mutation: Callable[[dict[str, Any]], object], message: str
) -> None:
    raw = json.loads(_SPEC.read_text(encoding="utf-8"))
    mutation(raw)
    with pytest.raises(InvalidAccuExperimentSpec, match=message):
        load_accu_experiment_spec(raw)


def test_accu_protocol_rejects_non_mapping_and_non_string_keys() -> None:
    with pytest.raises(InvalidAccuExperimentSpec, match="mapping"):
        load_accu_experiment_spec([])  # type: ignore[arg-type]
    with pytest.raises(InvalidAccuExperimentSpec, match="keys must be strings"):
        load_accu_experiment_spec({1: "unsafe"})  # type: ignore[dict-item]
