"""Immutable strategy-release tests for ephemeral Deriv sessions."""

import pytest

from devsoul_quant.domain.strategy_release import (
    InvalidStrategyRelease,
    ResearchConclusion,
    StrategyFamily,
    StrategyRelease,
)

HASH_A = "a" * 64
HASH_B = "b" * 64


def test_strategy_release_is_deterministic_and_contains_no_real_money_state() -> None:
    release = StrategyRelease(
        family=StrategyFamily.EVEN_ODD,
        specification_hash=HASH_A,
        code_version="0.1.0",
        risk_policy_hash=HASH_B,
        ttl_seconds=82_800,
    )

    duplicate = StrategyRelease(
        family=StrategyFamily.EVEN_ODD,
        specification_hash=HASH_A,
        code_version="0.1.0",
        risk_policy_hash=HASH_B,
        ttl_seconds=82_800,
    )

    assert release.release_id == duplicate.release_id
    assert len(release.release_id) == 64
    assert not hasattr(release, "real_money_eligible")


def test_research_conclusions_are_closed_to_the_three_permitted_states() -> None:
    assert {item.value for item in ResearchConclusion} == {
        "NO_EDGE",
        "INSUFFICIENT_EVIDENCE",
        "PAPER_ELIGIBLE",
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"family": "EVEN_ODD"},
        {"specification_hash": "not-a-hash"},
        {"risk_policy_hash": "A" * 64},
        {"code_version": " "},
        {"ttl_seconds": 0},
        {"ttl_seconds": 86_400},
        {"ttl_seconds": True},
    ],
)
def test_strategy_release_rejects_ambiguous_or_non_ephemeral_inputs(
    changes: dict[str, object],
) -> None:
    arguments: dict[str, object] = {
        "family": StrategyFamily.MULTIPLIER,
        "specification_hash": HASH_A,
        "code_version": "0.1.0",
        "risk_policy_hash": HASH_B,
        "ttl_seconds": 82_800,
    }
    arguments.update(changes)

    with pytest.raises(InvalidStrategyRelease):
        StrategyRelease(**arguments)  # type: ignore[arg-type]
