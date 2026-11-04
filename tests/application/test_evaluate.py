"""Walk-forward evaluation over a temporal split tests."""

from decimal import Decimal

import pytest

from devsoul_quant.application.build_dataset import build_dataset
from devsoul_quant.application.evaluate import evaluate_split, trials_from_ticks
from devsoul_quant.application.prepare_validation import prepare_validation
from devsoul_quant.domain.contracts import ContractAction, NoTradeIntent
from devsoul_quant.domain.costs import ExecutionCostModel
from devsoul_quant.domain.data_rights import DataRightsManifest, DataSourceKind, build_manifest
from devsoul_quant.domain.datasets import GENERATOR_VERSION, SCHEMA_VERSION, DatasetSpec
from devsoul_quant.domain.metrics import EvidenceMode, PromotionEligibility
from devsoul_quant.domain.replay import Outcome, Tick
from devsoul_quant.domain.synthetic import generate_ticks
from devsoul_quant.domain.validation import TemporalSplitSpec


def _manifest() -> DataRightsManifest:
    return build_manifest(
        source_id="devsoul-synthetic",
        source_kind=DataSourceKind.DEVSOUL_SYNTHETIC,
        license_identifier="DEVSOUL-INTERNAL-1.0",
        license_url=None,
        retrieved_at=1_760_000_000,
        retention_seconds=31_536_000,
        derived_artifacts_allowed=True,
        partner_display_allowed=True,
        redistribution_allowed=False,
        commercial_use_allowed=False,
        geographic_constraints=(),
        written_authorization_ref=None,
    )


def test_trials_from_ticks_cover_the_test_window() -> None:
    ticks = generate_ticks(seed=42, count=8)

    trials = trials_from_ticks(ticks=ticks, duration=3)

    assert len(trials) == len(ticks) - 3 - 2
    assert all(trial.decision.value in ("ENTER_CONTRACT", "NO_TRADE") for trial in trials)


def test_trials_enter_after_the_momentum_signal_without_lookahead() -> None:
    ticks = (
        Tick(epoch=1, quote=Decimal("100")),
        Tick(epoch=2, quote=Decimal("101")),
        Tick(epoch=3, quote=Decimal("100")),
        Tick(epoch=4, quote=Decimal("102")),
    )

    trials = trials_from_ticks(ticks=ticks, duration=1)

    assert len(trials) == 1
    assert trials[0].decision.value == "ENTER_CONTRACT"
    assert trials[0].outcome is not None
    assert trials[0].outcome.value == "WIN"


def test_trials_from_ticks_rejects_invalid_duration() -> None:
    ticks = generate_ticks(seed=42, count=8)

    with pytest.raises(ValueError, match="duration"):
        trials_from_ticks(ticks=ticks, duration=0)


def test_trials_from_ticks_emits_no_trade_when_flat() -> None:
    ticks = tuple(Tick(epoch=100 + i, quote=Decimal("100.0000")) for i in range(6))

    trials = trials_from_ticks(ticks=ticks, duration=3)

    assert trials
    assert all(trial.decision.value == "NO_TRADE" for trial in trials)


def test_evaluate_split_is_deterministic_and_non_economic() -> None:
    manifest = _manifest()
    snapshot = build_dataset(
        spec=DatasetSpec(
            generator_version=GENERATOR_VERSION,
            seed=42,
            start_epoch=1_700_000_000,
            interval=1,
            row_count=40,
            schema_version=SCHEMA_VERSION,
            rights_manifest_hash=manifest.manifest_hash,
        ),
        manifest=manifest,
    )
    split = prepare_validation(
        spec=TemporalSplitSpec(
            lookback_ticks=3,
            purge_ticks=3,
            embargo_ticks=2,
            test_ticks=10,
            fold_count=2,
            holdout_ticks=5,
        ),
        snapshot=snapshot,
        run_id="run-1",
    )

    first = evaluate_split(split=split, evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST, seed=9)
    second = evaluate_split(split=split, evidence_mode=EvidenceMode.TICK_PROXY_BACKTEST, seed=9)

    assert first == second
    assert first.decisions > 0
    assert first.economic_metrics_available is False
    assert first.promotion_eligibility is PromotionEligibility.NOT_ELIGIBLE


def _never_trade(
    *, history: object, duration: object, amount_requested: object, symbol: object
) -> NoTradeIntent:
    return NoTradeIntent(action=ContractAction.NO_TRADE, strategy_reason="never")


def test_trials_from_ticks_uses_injected_strategy() -> None:
    ticks = generate_ticks(seed=42, count=8)

    trials = trials_from_ticks(ticks=ticks, duration=3, strategy=_never_trade)

    assert trials
    assert all(trial.decision is ContractAction.NO_TRADE for trial in trials)


def test_trials_from_ticks_applies_execution_cost() -> None:
    ticks = (
        Tick(epoch=1, quote=Decimal("1.0000")),
        Tick(epoch=2, quote=Decimal("1.0100")),
        Tick(epoch=3, quote=Decimal("1.0000")),
        Tick(epoch=4, quote=Decimal("1.0050")),
    )

    raw = trials_from_ticks(ticks=ticks, duration=1)
    net = trials_from_ticks(
        ticks=ticks,
        duration=1,
        cost=ExecutionCostModel(Decimal("0.01")),
    )

    assert raw[0].outcome is Outcome.WIN
    assert net[0].outcome is Outcome.LOSS


def test_trials_from_ticks_rejects_invalid_decision_history() -> None:
    ticks = generate_ticks(seed=42, count=8)

    with pytest.raises(ValueError, match="decision_history"):
        trials_from_ticks(ticks=ticks, duration=3, decision_history=1)
