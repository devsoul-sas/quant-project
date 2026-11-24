# DevSoul Quant — documentación de Gate 0

## Estado crítico

El Gate 0 está **bloqueado para almacenamiento persistente de datos Deriv** por los API Users Terms 2.1–2.4. Véase:

- [Estado del Gate 0](scope/gate-0-status.md)
- [Bloqueo de almacenamiento](deriv/api-storage-blocker.md)
- [ADR-005](adr/ADR-005-deriv-data-retention-blocker.md)

## Alcance y plan

- [Alcance MVP corregido](scope/mvp-in-out.md)
- [Plan maestro](../.hermes/plans/2026-09-28_202135-devsoul-quant-mvp.md)

## Decisiones de arquitectura

- [ADR-001: local-first modular monolith](adr/ADR-001-local-first-modular-monolith.md)
- [ADR-002: replay-first](adr/ADR-002-replay-first-execution-core.md)
- [ADR-003: demo-only](adr/ADR-003-demo-only-safety-boundary.md)
- [ADR-004: contract intent](adr/ADR-004-contract-intent-semantics.md)
- [ADR-005: bloqueo de retención](adr/ADR-005-deriv-data-retention-blocker.md)
- [ADR-006: pivot provider-independiente](adr/ADR-006-provider-independent-research-pivot.md)
- [ADR-012: operación Deriv estrictamente efímera](adr/ADR-012-ephemeral-deriv-operation.md)

## Deriv

- [API actual](deriv/current-api.md)
- [Manifest de schemas](deriv/schema-manifest.json)
- [Bloqueo de almacenamiento](deriv/api-storage-blocker.md)
- [Demo efímera (<24 h)](deriv/ephemeral-demo.md)

## Investigación

- [Plantilla de protocolo](research/validation-protocol-template.md)
- [Even/Odd efímero](research/deriv-even-odd-session-protocol.md)
- [Multipliers efímero](research/deriv-multiplier-session-protocol.md)

## Datos y legal

- [Política provisional de datos](data/provider-data-policy.md)
- [Plantilla de evaluación de proveedores](data/provider-evaluation-template.md)
- [Candidatos a proveedor](data/provider-candidates.md)
- [Evaluación Dukascopy](data/provider-evaluation-dukascopy.md)
- [Evaluación Binance](data/provider-evaluation-binance.md)
- [Evaluación Alpha Vantage](data/provider-evaluation-alpha-vantage.md)
- [Evaluación Twelve Data](data/provider-evaluation-twelve-data.md)
- [Decisión de selección de proveedor](data/provider-selection-decision.md)
- [Esquema de manifest de derechos](data/source-manifest.schema.json)
- [Checklist jurídico/contractual](legal/early-gate-checklist.md)
- [Registro de fuentes legales](legal/source-register.json)
- [Borrador de solicitud a Deriv](legal/deriv-data-permission-request.md)
- [Borrador de consulta comercial a Twelve Data](legal/twelve-data-commercial-inquiry.md)

## Socios

- [Guía del paquete de evidencia demo](partner/demo-evidence-guide.md)

## Datos locales

No se conserva market data Deriv. Los payloads públicos temporales usados para la comprobación fueron eliminados antes de 24 horas. El único artefacto vendor retenido es el bundle oficial de schemas descargado desde GitHub y fijado por hash.