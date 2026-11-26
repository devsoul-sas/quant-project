# S3 — Matriz de decisión

Fecha: 2026-11-24
Estado: `RECOMMENDATION_ONLY — AWAITING_APPROVAL`

## 1. Propósito

Sintetizar S3.1 (mercados), S3.2 (proveedores) y S3.3 (protocolo de descubrimiento) en una única recomendación de hipótesis. No autoriza experimentos; se somete a aprobación.

## 2. La restricción dominante

`EPHEMERAL_ONLY` hace que **ninguna** hipótesis sea hoy evaluable de extremo a extremo:

- Persistencia de datos Deriv: prohibida (memoria, TTL <24 h).
- Fuentes persistibles: solo exógenas/no-ejecutables (CFTC, SEC) o FX diario ya cerrado.
- Economía retenible: solo contemporánea y efímera.

Por tanto, la recomendación debe elegir entre:

- **A** — una hipótesis de **estructura estadística** sobre un subyacente, sin economía inmediata (S3.3 puro); o
- **B** — una hipótesis de **factibilidad de medición intrasesión** sobre un contrato con economía observable (S3.1 + S3.3).

## 3. Distinción decisiva: subyacente vs contrato

Range Break y Crash/Boom son **subyacentes sintéticos**; no tienen un settlement único. Rise/Fall, Accumulators, Over/Under y Matches/Differs son **contratos** con reglas de liquidación.

Un estudio estadístico puede operar sobre el subyacente sin contrato. Una evaluación económica exige el contrato y sus campos contemporáneos (`ask_price`, `payout`, disponibilidad, settlement). Esta distinción no es un detalle: define qué pregunta responde cada hipótesis.

## 4. Matriz de hipótesis

Puntuación 1–5 por eje. Puntaje alto = más factible de preregistrar; no = más rentable.

| Hipótesis | Fundamento | Datos | Economía | Independencia S2 | Riesgo falso positivo (5=controlable) |
|---|---:|---:|---:|---:|---:|
| Range Break — hazard/estado del límite | 5 | 3 | 3 | 5 | 3 |
| Crash/Boom — inter-arrival de spike | 4 | 2 | 3 | 5 | 2 |
| Rise/Fall — dirección | 2 | 4 | 4 | 4 | 3 |
| Accumulators — supervivencia/knockout | 3 | 3 | 4 | 5 | 1 |
| Over/Under — barrera de dígito | 3 | 5 | 4 | 1 | 1 |
| Matches/Differs — dígito exacto | 3 | 5 | 4 | 1 | 1 |

Lectura honesta:

- **Mejor fundamento e independencia:** Range Break.
- **Mejor disponibilidad de datos y economía observable:** contratos de dígito.
- **Compromiso:** Rise/Fall (simple, economía observable, independencia media).

Ningún candidato maximiza los tres criterios simultáneamente; esa imposibilidad es el hallazgo central de la factibilidad.

## 5. Matriz de proveedores (resumen)

| Fuente | Decisión |
|---|---|
| BCE / Fed H.10 | Aprobado FX diario; no reabrir (ADR-011) |
| SEC EDGAR | Aprobable para filings/eventos (no precio) |
| CFTC COT | Aprobable para posicionamiento (no precio) |
| FRED / Nasdaq Data Link / Twelve Data | Condicional por dataset/licencia escrita |
| Stooq / CryptoDataDownload / exchanges | Rechazado o sin licencia verificable |
| Deriv | `EPHEMERAL_ONLY` |

Ninguna fuente persistible aporta precio ejecutable + economía + costos. La ruta de descubrimiento estadístico persistente (CFTC/SEC) es exógena y no sustituye un feed de precios.

## 6. Recomendación única

```text
RANGE_BREAK_BOUNDARY_HAZARD_V1
```

Pregunta científica:

> ¿El conteo causal de impactos y el estado normalizado del rango contienen información OOS sobre el hazard y la dirección de la próxima ruptura, por encima de un proceso de renovación calibrado en train?

Por qué Range Break y no un contrato de dígito:

1. Mecanismo programado y falsable (no una mera búsqueda de indicadores).
2. Independencia estricta de Even/Odd y Multipliers.
3. Nulo de renovación explícito y controles negativos naturales.
4. La documentación oficial distingue Range Break de otros sintéticos para el análisis de canal (hecho, no edge).
5. Encaja en S3.3 como descubrimiento estadístico previo a cualquier estrategia.

### Condición de cancelación automática

Si el análisis de potencia muestra que una única sesión no alcanza ≥80% con el número esperado de rupturas dentro del TTL, la recomendación pasa a:

```text
UNDERPOWERED — DO_NOT_RUN
```

La unidad de muestra son **rupturas**, no ticks. Si el límite operativo de una sesión no permite suficientes rupturas, no se corre el experimento.

### Alternativa honesta (si Range Break queda sin potencia)

Contrato de dígito **Matches/Differs** como prueba de factibilidad de medición intrasesión, con un único símbolo, dígito, duración e hipótesis preregistrados. Ventaja: settlement inequívoco y más outcomes. Desventaja decisiva: pertenece a la misma familia estadística que S2 Even/Odd, por lo que solo sería admisible como una hipótesis nueva y preregistrada, nunca como continuación o re-optimización de S2. Queda explícitamente en segundo plano.

## 7. Secuencia propuesta tras aprobación

1. Análisis de potencia (rupturas por sesión, ≥80%).
2. Preregistro congelado: unidad, H0/H1, lags, corrección múltiple, folds, purge/embargo, criterios GO/NO-GO, hash.
3. Definición causal de límite/impacto/reset/ruptura sin uso de futuro.
4. Observación demo pasiva intrasesión, cero persistencia, zeroización.
5. Decisión `NO_EDGE` / `INSUFFICIENT_EVIDENCE` / elegibilidad paper intrasesión.
6. Solo después: economía contractual de una exposición superpuesta (CFD u opción).

## 8. Lo que esta fase NO hace

- No habilita paper trading ni dinero real.
- No reabre S2 ni las semillas 61–80.
- No re-optimiza Even/Odd ni Multipliers.
- No ejecuta modelos predictivos.
- No descarga datasets ni invoca APIs de datos.
- No crea recursos GCP.

## 9. Costos

- Recursos GCP: 0.
- Datasets descargados: 0.
- APIs invocadas: 0.
- Costo GCP incremental: USD 0.

## 10. Solicitud de aprobación

Se solicita autorización explícita para preparar el preregistro `RANGE_BREAK_BOUNDARY_HAZARD_V1` y su análisis de potencia. No se iniciará ninguna sesión de observación hasta aprobación.
