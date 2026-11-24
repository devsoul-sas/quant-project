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


def test_darwinex_zero_is_recorded_as_track_record_layer_not_venue() -> None:
    doc = REPO_ROOT / "docs" / "data" / "execution-venue-darwinex-zero.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")

    # It is a virtual-capital track-record layer, not an execution venue.
    assert "NO ES UN VENUE" in text
    assert "Third Party Broker" in text
    assert "systematic extraction" in text
    assert "prior written permission" in text
    assert "Tradeslide Technologies Ltd" in text
    assert "FRN 586466" in text
    assert "plataforma virtual, no una demo" in text

    venues = VENUES.read_text(encoding="utf-8")
    assert "Darwinex Zero" in venues
    assert "NINGUNO APROBADO" in venues


def test_darwinex_global_evaluation_separates_entity_and_gates() -> None:
    doc = REPO_ROOT / "docs" / "data" / "provider-evaluation-darwinex-global.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")

    assert "TRADESLIDE GLOBAL LTD" in text
    assert "SD171" in text
    assert "Colombia" in text
    assert "EURGBP" in text
    assert "Expert Advisor" in text
    assert "UNKNOWN/BLOCKING" in text
    assert "NOT APPROVED" in text
    assert "holdout permanece sellado" in text


def test_darwinex_fca_terms_block_data_retention_and_automation() -> None:
    doc = REPO_ROOT / "docs" / "data" / "darwinex-api-market-data-terms.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")

    # Broker terms (Client Agreement, FCA entity) prohibit redistribution and gate automation.
    assert "NOT GRANTED" in text
    assert "9.1(d)" in text
    assert "9.1(c)" in text
    assert "9.6" in text
    assert "13.1" in text
    assert "retransmit, redistribute" in text
    assert "prior written consent" in text
    # DARWIN API terms restrict use and reserve derivative works.
    assert "3.2" in text
    assert "3.4" in text
    assert "derivative work" in text
    assert "internal purposes" in text
    # Verified source hashes (FCA folder).
    assert "b81c7d674fc642f079172047b5759135141dbe42795581f5a3a9ad6c41d997b8" in text
    assert "3cc29b9c7d2b72ce3ff7dc9f97ceeb3e38b9dae78482f76a1514720f7bb48193" in text


def test_darwinex_execution_evidence_documents_eurgbp_conditions() -> None:
    doc = REPO_ROOT / "docs" / "data" / "darwinex-execution-evidence.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")

    assert "FRN 586466" in text
    assert "EURGBP" in text
    assert "0.55" in text
    assert "FIX" in text
    assert "swapLong" in text
    assert "tripleSwapDay" in text
    assert "minSize" in text
    assert "BLOCKING" in text or "UNKNOWN" in text
