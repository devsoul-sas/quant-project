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
- [Protocolo S3 — descubrimiento de estructura estadística](research/s3-statistical-discovery-protocol.md)
- [Cierre S2 — NO_EDGE](research/s2-closure-report.md)
- [S3 — factibilidad de mercados](research/s3-market-feasibility.md)
- [S3 — factibilidad de proveedores](research/s3-provider-feasibility.md)
- [S3 — matriz de decisión](research/s3-decision-matrix.md)
- [S3 — preregistro Range Break](research/s3-range-break-boundary-hazard-v1.md)
- [S3 — potencia Range Break (UNDERPOWERED)](research/s3-range-break-power-analysis.md)
- [S4 — selección de mercado](research/s4-market-selection.md)
- [S4 — evaluación de proveedores](research/s4-data-provider-assessment.md)
- [S4 — factibilidad económica](research/s4-economic-feasibility.md)
- [S4 — protocolo de alpha discovery](research/s4-alpha-discovery-protocol.md)
- [S3.5 — protocolo de laboratorio en vivo](research/s3.5-live-experimental-protocol.md)
- [S3.5 — campaña experimental continua](research/s3.5-continuous-campaign.md)
- [S3.5 — conectividad y fiabilidad](research/s3.5-connectivity-report.md)
- [S3.5 — caracterización de mercado](research/s3.5-market-characterization.md)
- [S3.5 — reporte económico demo](research/s3.5-demo-economic-report.md)
- [S3.5 — decisión final](research/s3.5-final-decision.md)
- [S3.6 — Autonomous Demo MVP](research/s3.6-autonomous-demo-mvp.md)
- [S3.7 — protocolo Predictive Demo Trading](research/s3.7-predictive-demo-protocol.md)
- [S3.7 — enmienda fail-closed de recuperación](research/s3.7-recovery-amendment.md)
- [S3.8 — Adaptive Market Intelligence](research/s3.8-adaptive-intelligence-protocol.md)
- [S3.8 — enmienda prospectiva 001](research/s3.8-protocol-amendment-001.md)
- [S3.8 — réplica shadow de dos horas](research/s3.8-protocol-amendment-002.md)
- [S3.8 — evaluación exploratoria y decisión final](research/s3.8-exploratory-evaluation.md)
- [S3.9 — Market Edge Discovery](research/s3.9-market-discovery.md)
- [S3.9 — matriz de hipótesis](research/s3.9-hypothesis-matrix.md)
- [S3.9 — protocolo Step direction (H1)](research/s3.9-protocol-step-direction-v1.md)
- [S3.9 — protocolo Jump digit (H2)](research/s3.9-protocol-jump-digit-v1.md)
- [S3.10 — remediación de ingeniería](research/s3.10-engineering-remediation.md)
- [S3.10 — enmienda prospectiva 001 (H1/H2)](research/s3.10-protocol-amendment-001.md)
- [S3.11 — H1 Step Direction: implementación, potencia y decisión](research/s3.11-h1-campaign-report.md)
- [S3.12 — enmienda prospectiva 002 (H1 V2 adaptativo)](research/s3.12-protocol-amendment-002.md)
- [S3.12 — H1 V2 (MARKOV_1_ADAPTIVE): implementación, potencia y ejecución](research/s3.12-h1-v2-campaign-report.md)
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