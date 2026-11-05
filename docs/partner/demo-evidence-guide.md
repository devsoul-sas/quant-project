# DevSoul Quant — Guía del paquete de evidencia demo

Este documento explica cómo leer el paquete de evidencia que produce el comando:

```bash
uv run devsoul-quant research synthetic \
  --spec examples/research-synthetic.json \
  --output <directorio>
```

El comando falla cerrado si el árbol de trabajo tiene cambios sin commitear (incluidos archivos
sin rastrear) o si el directorio de salida ya existe. La evidencia registra el SHA del commit:
por eso se exige un árbol limpio, para que el paquete sea reconstruible desde ese commit.

## Qué contiene el paquete

Tres archivos:

- `run-report.json` — informe canónico legible por máquina.
- `run-summary.md` — resumen legible por humanos.
- `manifest.json` — nombres, tamaños y SHA-256 de los otros dos archivos.

No se incluyen datos crudos de proveedor, credenciales, cuentas, DSNs ni rutas locales
absolutas. El paquete contiene hashes y métricas, no el corpus de ticks.

## Cómo leer el informe

Cuatro estados separan lo que está listo de lo que no:

1. **engineering_readiness** — `READY`: la arquitectura de ejecución/replay/auditoría
   funciona de extremo a extremo y el pipeline es reproducible.
2. **scientific_evidence** — `NON_ECONOMIC`: los resultados sintéticos validan ingeniería,
   no rentabilidad. La tasa de acierto direccional es un proxy no económico.
3. **provider_license_blockers** — `DERIV_EPHEMERAL_ONLY`: no se esperará
   autorización futura; no se usa contenido Deriv persistido.
4. **real_money_exclusion** — `EXCLUDED`: no existe modo de dinero real.

El campo `evaluation.promotion_eligibility` es `NOT_ELIGIBLE`: la evidencia sintética no
habilita promoción a demo ni a dinero real.

## Reproducibilidad

El mismo `spec.json` sobre el mismo commit produce un paquete byte a byte idéntico. La
identidad de cada artefacto (dataset, features, split, holdout) está encadenada por SHA-256
y ligada al commit Git registrado en `git_sha`.

## Qué no afirma este paquete

- No afirma ventaja económica ni rentabilidad esperada.
- No implica autorización de Deriv ni de ningún proveedor.
- No demuestra que la estrategia gane dinero.
