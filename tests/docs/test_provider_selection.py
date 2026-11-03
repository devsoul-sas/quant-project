"""Provider selection documentation tests."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = REPO_ROOT / "docs" / "data" / "provider-evaluation-template.md"
CANDIDATES = REPO_ROOT / "docs" / "data" / "provider-candidates.md"
DECISION = REPO_ROOT / "docs" / "data" / "provider-selection-decision.md"
SOURCE_MANIFEST_SCHEMA = REPO_ROOT / "docs" / "data" / "source-manifest.schema.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_decision_records_no_provider_approved() -> None:
    text = _read(DECISION)

    assert "NO_PROVIDER_APPROVED" in text
    assert "PENDING_PROVIDER_REVIEW" in text


def test_source_manifest_schema_requires_every_rights_gate_field() -> None:
    schema = json.loads(_read(SOURCE_MANIFEST_SCHEMA))

    assert set(schema["required"]) == set(schema["properties"])


def test_decision_requires_human_legal_review() -> None:
    text = _read(DECISION)

    assert "humana" in text
    assert "jurídica" in text


def test_template_lists_mandatory_criteria() -> None:
    text = _read(TEMPLATE)

    for criterion in ("retención", "derivadas", "comercial", "redistribución"):
        assert criterion in text
    assert "NO_PROVIDER_APPROVED" in text


def test_candidates_marks_unknowns_as_blockers() -> None:
    text = _read(CANDIDATES)

    assert "BLOQUEADO" in text or "bloquean" in text
    assert "PENDING_PROVIDER_REVIEW" in text
    # no candidate is asserted as approved
    assert "APROBADO" not in text


def test_decision_names_the_next_evaluation_target() -> None:
    text = _read(DECISION)

    assert "Twelve Data" in text
    assert "subyacente" in text


def test_candidates_lists_verifiable_official_sources() -> None:
    text = _read(CANDIDATES)

    assert "provider-evaluation-dukascopy.md" in text
    assert "provider-evaluation-alpha-vantage.md" in text
    assert "provider-evaluation-twelve-data.md" in text
    assert "provider-evaluation-binance.md" in text
    assert "SIN VERIFICAR" not in text


def test_dukascopy_is_rejected_after_formal_terms_review() -> None:
    candidates = _read(CANDIDATES)
    decision = _read(DECISION)
    evaluation = _read(REPO_ROOT / "docs/data/provider-evaluation-dukascopy.md")

    assert "Dukascopy" in candidates
    assert "RECHAZADO" in candidates
    assert "RECHAZADO" in decision
    assert "personal, non-commercial use" in evaluation
    assert "may not be used to construct a database" in evaluation


def test_remaining_provider_evaluations_are_fail_closed() -> None:
    alpha = _read(REPO_ROOT / "docs/data/provider-evaluation-alpha-vantage.md")
    twelve = _read(REPO_ROOT / "docs/data/provider-evaluation-twelve-data.md")
    binance = _read(REPO_ROOT / "docs/data/provider-evaluation-binance.md")

    assert "RECHAZADO BAJO LOS TÉRMINOS ESTÁNDAR" in alpha
    assert "BLOCKED_PENDING_PERMISSION" in alpha
    assert "CONDICIONAL, BLOQUEADO" in twelve
    assert "BLOCKED_PENDING_PERMISSION" in twelve
    assert "RECHAZADO" in binance


def test_decision_keeps_no_provider_approved_after_shortlist_review() -> None:
    decision = _read(DECISION)

    assert "NO_PROVIDER_APPROVED" in decision
    for provider in ("Dukascopy", "Binance", "Alpha Vantage", "Twelve Data"):
        assert provider in decision


def test_twelve_data_inquiry_is_an_unsent_fail_closed_draft() -> None:
    draft = _read(REPO_ROOT / "docs/legal/twelve-data-commercial-inquiry.md")

    assert "DRAFT — NOT SENT" in draft
    assert "Do not send" in draft
    assert "models" in draft
    assert "backups" in draft
