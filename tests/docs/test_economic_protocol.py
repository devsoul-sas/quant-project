"""Economic-protocol document integrity tests."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = REPO_ROOT / "docs" / "research" / "economic-protocol.md"


def _read() -> str:
    return PROTOCOL.read_text(encoding="utf-8")


def test_economic_protocol_exists() -> None:
    assert PROTOCOL.is_file()


def test_economic_protocol_keeps_non_profitability_invariants() -> None:
    text = _read()

    assert "NOT_ELIGIBLE" in text
    assert "profitability_claim = False" in text
    assert "real_money = EXCLUDED" in text
    assert "NO una métrica de rentabilidad" in text


def test_economic_protocol_freezes_criteria_before_holdout() -> None:
    text = _read()

    assert "0.50" in text
    assert "bootstrap" in text.lower()
    assert "holdout" in text.lower()
    assert "sellado" in text
    assert "una única vez" in text


def test_economic_protocol_models_transaction_cost() -> None:
    text = _read()

    assert "spread" in text
    assert "fricción" in text
    assert "mid-point" in text
    assert "sin bid/ask" in text
