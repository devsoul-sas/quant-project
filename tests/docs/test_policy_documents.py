"""Documentation policy tests for the Deriv review state and the provider pivot."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GATE0 = REPO_ROOT / "docs" / "scope" / "gate-0-status.md"
POLICY = REPO_ROOT / "docs" / "data" / "provider-data-policy.md"
ADR006 = REPO_ROOT / "docs" / "adr" / "ADR-006-provider-independent-research-pivot.md"
ADR011 = REPO_ROOT / "docs" / "adr" / "ADR-011-venue-closure-strategic-pivot.md"
ADR012 = REPO_ROOT / "docs" / "adr" / "ADR-012-ephemeral-deriv-operation.md"
EPHEMERAL_DEMO = REPO_ROOT / "docs" / "deriv" / "ephemeral-demo.md"
CROWDSOURCED = REPO_ROOT / "docs" / "research" / "quant-crowdsourced-opportunities.md"
README = REPO_ROOT / "docs" / "README.md"
MVP_SCOPE = REPO_ROOT / "docs" / "scope" / "mvp-in-out.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_gate0_records_terminal_ephemeral_only_decision() -> None:
    text = _read(GATE0)

    assert "EPHEMERAL_ONLY" in text
    assert "PENDING_PROVIDER_REVIEW" not in text
    assert "no se esperará autorización futura" in text
    assert "no está en el camino crítico" in text


def test_gate0_names_the_alternative_license_path() -> None:
    text = _read(GATE0)

    assert "fuente de datos alternativa con licencia compatible" in text


def test_provider_policy_references_the_terminal_ephemeral_pivot() -> None:
    text = _read(POLICY)

    assert "EPHEMERAL_ONLY" in text
    assert "PENDING_PROVIDER_REVIEW" not in text
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
    assert "Deriv-derived output is disabled outside the <24h ephemeral session" in text
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


def test_ephemeral_demo_documents_the_paper_only_session_without_buying() -> None:
    text = " ".join(_read(EPHEMERAL_DEMO).split())

    assert "paper-session" in text
    assert "--confirm-paper-only" in text
    assert "No compra ningún contrato" in text
    assert "ESTIMATED" in text
    assert "sold" in text
    assert "PAPER_ELIGIBLE" in text
    assert "break-even" in text


def test_adr011_closes_venue_chapter_and_pivots() -> None:
    assert ADR011.is_file()
    text = _read(ADR011)

    # Venue chapter closed, no broker approved.
    assert "Cerrar el capítulo venue de FX retail" in text
    assert "consultas formales a brokers" in text
    # Scientific invariants preserved.
    assert "profitability_claim = False" in text
    assert "promotion_eligibility = NOT_ELIGIBLE" in text
    assert "real_money = EXCLUDED" in text
    assert "holdout_opened = False" in text
    # Strategic pivot targets.
    assert "Numerai" in text
    assert "WorldQuant BRAIN" in text
    assert "Producto educativo" in text
    # Negative conclusion is a valid result.
    assert "conclusión negativa válida" in text


def test_gate0_records_venue_closure_and_pivot() -> None:
    text = _read(GATE0)

    assert "Cierre del capítulo venue" in text
    assert "ADR-011" in text
    assert "Numerai" in text
    assert "WorldQuant BRAIN" in text


def test_crowdsourced_opportunities_document_verified_facts() -> None:
    assert CROWDSOURCED.is_file()
    text = _read(CROWDSOURCED)

    # Numerai verified mechanics.
    assert "Numerai" in text
    assert "Meta Model" in text
    assert "target_jupiter_60" in text
    assert "NMR" in text
    # WorldQuant BRAIN verified facts.
    assert "WorldQuant BRAIN" in text
    assert "Alphas" in text
    assert "$8 000" in text
    assert "$2 000" in text
    assert "Grandmaster" in text
    assert "IQC 2026" in text
    # No profitability claims.
    assert "INVESTIGACIÓN_INICIAL" in text
    assert "No se ha" in text and "abierto cuenta" in text
    assert "afirmación de rentabilidad" in text


def test_adr012_freezes_ephemeral_deriv_operation_without_new_permission_requests() -> None:
    assert ADR012.is_file()
    text = _read(ADR012)
    normalized = text.lower()

    assert "no se enviarán nuevas solicitudes de permiso" in normalized
    assert "ttl estricto menor de 24 horas" in normalized
    assert "solo en memoria" in normalized
    assert "cada sesión comienza sin estado" in normalized
    assert "ninguna sesión aprende de una sesión anterior" in normalized
    assert "NO_EDGE" in text
    assert "INSUFFICIENT_EVIDENCE" in text
    assert "PAPER_ELIGIBLE" in text
    assert "real_money = EXCLUDED" in text


def test_scope_links_the_ephemeral_strategy_protocols_without_reopening_history() -> None:
    readme = _read(README)
    gate = _read(GATE0)
    scope = _read(MVP_SCOPE)
    scope_flat = " ".join(scope.lower().split())

    assert "ADR-012" in readme
    assert "Even/Odd" in readme and "Multipliers" in readme
    assert "no se enviarán nuevas solicitudes de permiso" in gate.lower()
    assert "laboratorio operativo efímero" in gate.lower()
    assert "cada sesión comienza sin estado" in scope_flat
    assert "ninguna sesión aprende de una sesión anterior" in scope_flat
    assert "dinero real" in scope_flat and "excluido" in scope_flat
