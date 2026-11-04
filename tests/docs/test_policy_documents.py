"""Documentation policy tests for the Deriv review state and the provider pivot."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GATE0 = REPO_ROOT / "docs" / "scope" / "gate-0-status.md"
POLICY = REPO_ROOT / "docs" / "data" / "provider-data-policy.md"
ADR006 = REPO_ROOT / "docs" / "adr" / "ADR-006-provider-independent-research-pivot.md"
EPHEMERAL_DEMO = REPO_ROOT / "docs" / "deriv" / "ephemeral-demo.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_gate0_distinguishes_pending_review_from_authorization() -> None:
    text = _read(GATE0)

    assert "PENDING_PROVIDER_REVIEW" in text
    assert "2026-10-29" in text
    assert "no constituye autorización" in text
    assert "no está en el camino crítico" in text


def test_gate0_names_the_alternative_license_path() -> None:
    text = _read(GATE0)

    assert "fuente de datos alternativa con licencia compatible" in text


def test_provider_policy_references_the_pending_review_and_pivot() -> None:
    text = _read(POLICY)

    assert "PENDING_PROVIDER_REVIEW" in text
    assert "ADR-006" in text


def test_adr006_records_all_alternatives_and_selects_the_pivot() -> None:
    assert ADR006.is_file()
    text = _read(ADR006)

    assert "provider-independiente" in text
    assert "Seleccionada" in text
    # the four alternatives considered
    assert "Esperar" in text
    assert "asumir" in text.lower()
    assert "efímera" in text
    assert "fuente licenciada" in text


def test_no_pii_or_verbatim_support_content_in_policy_documents() -> None:
    for path in (GATE0, POLICY, ADR006):
        text = _read(path)
        assert "@" not in text  # no email addresses
        assert "Best regards" not in text  # no verbatim transcript
        assert "ticket" not in text.lower()  # no ticket payload
        assert "Amy" not in text  # no support agent name


def test_ephemeral_demo_documents_the_bounded_demo_execution_and_export_block() -> None:
    text = _read(EPHEMERAL_DEMO)

    assert "Escenario A" in text
    assert "Estadísticas transitorias: permitido" in text
    assert "Dataset histórico de características: bloqueado" in text
    assert "Pesos de modelos entrenados: bloqueado" in text
    assert "Deriv-derived output is disabled pending written authorization" in text
    assert "demo-execute" in text
    assert "máximo de un contrato" in text
    assert "recibo operativo genérico" in text
    assert "deadline monotónico absoluto de una hora" in text
    assert "rechaza el endpoint real (`/ws/real`)" in text
    assert "no backtest histórico ni evidencia de rentabilidad" in text


def test_ephemeral_demo_does_not_instruct_credential_or_network_use() -> None:
    text = _read(EPHEMERAL_DEMO)

    assert "uv run devsoul-quant live-demo" not in text
    assert "uv run devsoul-quant live-evaluate" not in text
    assert "export DEVSOUL_QUANT_DERIV_TOKEN" not in text
    assert "export DEVSOUL_QUANT_DERIV_APP_ID" not in text
    assert "--url" not in text
    assert "--otp" not in text
