"""Economic-protocol document integrity tests."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = REPO_ROOT / "docs" / "research" / "economic-protocol.md"
RESULTS = REPO_ROOT / "docs" / "research" / "edge-search-results.md"
CONFIRMATION = REPO_ROOT / "docs" / "research" / "fed-h10-confirmation-results.md"
EXECUTION_ADR = REPO_ROOT / "docs" / "adr" / "ADR-009-eurgbp-execution-economics.md"
HORIZON_ADR = REPO_ROOT / "docs" / "adr" / "ADR-010-observation-horizon-semantics.md"
VENUES = REPO_ROOT / "docs" / "data" / "execution-venue-evaluation.md"


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


def test_economic_protocol_documents_multiple_testing_correction() -> None:
    text = _read()

    assert "Bonferroni" in text
    assert "n_tests" in text
    assert "falsos descubrimientos" in text


def test_edge_search_results_exist_and_stay_non_promotable() -> None:
    assert RESULTS.is_file()
    text = RESULTS.read_text(encoding="utf-8")

    assert "preliminar" in text
    assert "NOT_ELIGIBLE" in text
    assert "profitability_claim = False" in text
    assert "EURGBP" in text
    assert "mean-reversion" in text


def test_fed_confirmation_records_replication_without_promotion() -> None:
    assert CONFIRMATION.is_file()
    text = CONFIRMATION.read_text(encoding="utf-8")

    assert "0.5475" in text
    assert "0.5161" in text
    assert "holdout" in text
    assert "abierto: **No**" in text
    assert "NOT_ELIGIBLE" in text
    assert "NO promocionable, NO operable" in text
    assert "rollover" in text


def test_execution_economics_separate_options_from_spot_costs() -> None:
    assert EXECUTION_ADR.is_file()
    text = EXECUTION_ADR.read_text(encoding="utf-8")

    assert "ask_price / payout" in text
    assert "p * payout - ask_price" in text
    assert "spread" in text
    assert "rollover" in text
    assert "holdout BCE permanece sellado" in text
    assert "NOT_ELIGIBLE" in text
    assert "real_money = EXCLUDED" in text


def test_observation_horizon_is_causal_and_not_calendar_duration() -> None:
    text = HORIZON_ADR.read_text(encoding="utf-8")

    assert "F_{t+1}" in text
    assert "F_{t+6}" in text
    assert "cinco días calendario" in text
    assert "holdout permanece sellado" in text


def test_execution_venues_remain_blocked() -> None:
    text = VENUES.read_text(encoding="utf-8")

    assert "NINGUNO APROBADO" in text
    assert "IG International" in text
    assert "Interactive Brokers" in text
    assert "OANDA" in text
    assert "no se abren cuentas" in text
