from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from devsoul_quant.domain.ledger import DuplicateEvent, InMemoryLedger, verify_chain


def test_ledger_appends_an_immutable_hash_chain() -> None:
    ledger = InMemoryLedger()

    first = ledger.append(
        event_id="event-1",
        event_type="DEMO_STARTED",
        occurred_at=1_000,
        correlation_id="demo-42",
        causation_id=None,
        payload={"seed": 42},
    )
    second = ledger.append(
        event_id="event-2",
        event_type="DECISION_RECORDED",
        occurred_at=1_001,
        correlation_id="demo-42",
        causation_id="event-1",
        payload={"action": "NO_TRADE"},
    )

    assert first.sequence == 0
    assert second.sequence == 1
    assert second.previous_hash == first.event_hash
    assert ledger.verify()
    assert ledger.events == (first, second)
    with pytest.raises(FrozenInstanceError):
        first.event_type = "TAMPERED"  # type: ignore[misc]
    with pytest.raises(TypeError):
        first.payload["seed"] = 7  # type: ignore[index]


def test_ledger_rejects_a_duplicate_event_id() -> None:
    ledger = InMemoryLedger()
    common = {
        "event_id": "event-1",
        "event_type": "DEMO_STARTED",
        "occurred_at": 1_000,
        "correlation_id": "demo-42",
        "causation_id": None,
        "payload": {"seed": 42},
    }
    ledger.append(**common)

    with pytest.raises(DuplicateEvent, match="event-1"):
        ledger.append(**common)


def test_ledger_detects_a_forged_historical_payload() -> None:
    ledger = InMemoryLedger()
    original = ledger.append(
        event_id="event-1",
        event_type="RISK_DECIDED",
        occurred_at=1_000,
        correlation_id="demo-42",
        causation_id=None,
        payload={"approved": False},
    )
    forged = replace(original, payload={"approved": True})

    assert not verify_chain((forged,))


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"event_id": " "}, "event_id"),
        ({"event_type": ""}, "event_type"),
        ({"occurred_at": True}, "occurred_at"),
        ({"correlation_id": "\t"}, "correlation_id"),
        ({"causation_id": ""}, "causation_id"),
        ({"payload": {"amount": Decimal("1")}}, "payload"),
    ],
)
def test_ledger_rejects_invalid_event_envelopes(override: dict[str, object], message: str) -> None:
    ledger = InMemoryLedger()
    valid: dict[str, object] = {
        "event_id": "event-1",
        "event_type": "DEMO_STARTED",
        "occurred_at": 1_000,
        "correlation_id": "demo-42",
        "causation_id": None,
        "payload": {"seed": 42},
    }

    with pytest.raises(ValueError, match=message):
        ledger.append(**(valid | override))  # type: ignore[arg-type]
