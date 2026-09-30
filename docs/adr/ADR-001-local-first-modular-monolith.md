# ADR-001 — Arquitectura local-first como monolito modular

- Estado: aceptada para MVP
- Fecha: 2026-09-29

## Contexto

El objetivo es validar una hipótesis, no operar una plataforma multiusuario. La complejidad distribuida dificultaría reproducibilidad, operación y diagnóstico sin aportar evidencia científica.

## Decisión

Usar un único repositorio Python con módulos de dominio/aplicación/adaptadores y procesos desplegables separados cuando lo exija el lifecycle:

- `collector`;
- `trader`;
- `api`;
- dashboard mínimo.

Todos se ejecutan en una máquina Linux mediante Docker Compose y comparten PostgreSQL. Los snapshots analíticos propios o de una fuente con licencia compatible pueden escribirse como Parquet en filesystem local. Market data de Deriv no se persiste ni exporta mientras aplique el bloqueo de ADR-005. El dominio permanece independiente de Deriv, FastAPI y SQLAlchemy.

## Consecuencias

### Positivas

- despliegue y recuperación simples;
- menor costo fijo;
- contratos internos comprobables;
- facilita replay y pruebas de integración reales;
- permite separar procesos sin convertirlos en microservicios.

### Negativas

- un solo host es un dominio de fallo;
- no promete alta disponibilidad;
- exige UPS, backup externo, métricas y registro de downtime.

## Restricciones

- no Kubernetes;
- no cloud obligatorio;
- no TimescaleDB hasta medir necesidad;
- no MLflow en la primera fase;
- acceso remoto solo mediante red privada aprobada.

## Criterio de revisión

Revisar únicamente si CPU, RAM, I/O, disponibilidad o volumen medidos exceden los objetivos pre-registrados. La preferencia arquitectónica por sí sola no justifica distribuir.