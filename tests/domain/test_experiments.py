from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from devsoul_quant.domain.experiments import (
    InvalidExperiment,
    Signal,
    StrategyRelease,
    ValidationRun,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64


def test_signal_preserves_versions_without_deciding_stake() -> None:
    signal = Signal(
        signal_id="signal-1",
        strategy_release_id="release-1",
        feature_set_hash=HASH_A,
        symbol="SYNTH_OWNED",
        reason="positive deterministic momentum",
    )

    assert signal.feature_set_hash == HASH_A
    assert not hasattr(signal, "amount")
    assert not hasattr(signal, "stake")


def test_strategy_release_freezes_before_validation() -> None:
    draft = StrategyRelease.draft(
        release_id="release-1",
        strategy_hash=HASH_A,
        feature_set_hash=HASH_B,
        risk_policy_hash=HASH_C,
    )
    frozen_at = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)

    frozen = draft.freeze(frozen_at)

    assert draft.frozen_at is None
    assert frozen.frozen_at == frozen_at
    with pytest.raises(FrozenInstanceError):
        frozen.strategy_hash = HASH_D  # type: ignore[misc]


def test_validation_run_captures_all_frozen_evidence_hashes() -> None:
    release = StrategyRelease.draft(
        release_id="release-1",
        strategy_hash=HASH_A,
        feature_set_hash=HASH_B,
        risk_policy_hash=HASH_C,
    ).freeze(datetime(2026, 9, 30, 15, 0, tzinfo=UTC))

    run = ValidationRun.start(
        run_id="validation-1",
        release=release,
        dataset_hash=HASH_D,
        code_hash=HASH_E,
        contract_spec_hash="f" * 64,
    )

    assert run.strategy_hash == HASH_A
    assert run.feature_set_hash == HASH_B
    assert run.risk_policy_hash == HASH_C
    assert run.dataset_hash == HASH_D
    assert run.code_hash == HASH_E
    assert run.contract_spec_hash == "f" * 64


def test_validation_run_rejects_an_unfrozen_release() -> None:
    draft = StrategyRelease.draft(
        release_id="release-1",
        strategy_hash=HASH_A,
        feature_set_hash=HASH_B,
        risk_policy_hash=HASH_C,
    )

    with pytest.raises(InvalidExperiment, match="frozen"):
        ValidationRun.start(
            run_id="validation-1",
            release=draft,
            dataset_hash=HASH_D,
            code_hash=HASH_E,
            contract_spec_hash="f" * 64,
        )


@pytest.mark.parametrize("invalid_hash", ["", "abc", "g" * 64])
def test_experiment_entities_reject_invalid_hashes(invalid_hash: str) -> None:
    with pytest.raises(InvalidExperiment, match="hash"):
        StrategyRelease.draft(
            release_id="release-1",
            strategy_hash=invalid_hash,
            feature_set_hash=HASH_B,
            risk_policy_hash=HASH_C,
        )
