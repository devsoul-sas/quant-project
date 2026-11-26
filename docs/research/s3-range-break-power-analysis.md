# S3 — Análisis de potencia: RANGE_BREAK_BOUNDARY_HAZARD_V1

Fecha: 2026-11-24
Estado: `COMPLETED — VERDICT: UNDERPOWERED — DO_NOT_RUN`

## 1. Propósito

Determinar si el test primario de la hipótesis de hazard (detección de una tasa
de ruptura mayor en la fase tardía del ciclo de rango) puede alcanzar ≥80% de
potencia dentro de una única sesión efímera (`EPHEMERAL_ONLY`, TTL <24 h,
fail-closed).

Método: fórmula de eventos de Schoenfeld (1983) para la comparación de tasas,
validada con una simulación Monte Carlo de 20 000 réplicas (stdlib, sin numpy).

## 2. Diseño estadístico

- Hipótesis: hazard no constante; la tasa de ruptura es mayor en la fase tardía.
- Test: z one-sided de diferencia de tasas de ruptura (tardía vs temprana).
- α = 0.05 (one-sided), potencia objetivo = 0.80.
- Efecto mínimo relevante (MDE) preregistrado: **HR = 2.0** (duplicación de la
  tasa de ruptura en la fase tardía respecto de la temprana).
- Unidad de muestra: **rupturas** (eventos), no ticks.

Fórmula de eventos (two-sample log-rank, grupos 1:1, one-sided):

```text
N_eventos = 4 * (z_{1-α} + z_{1-β})² / (ln HR)²
          = 24.7302 / (ln HR)²
```

## 3. Eventos requeridos por efecto

| HR | N eventos (rupturas) |
|---:|---:|
| 1.20 | 744.0 |
| 1.30 | 359.3 |
| 1.50 | 150.4 |
| 2.00 | 51.5 |
| 2.50 | 29.5 |
| 3.00 | 20.5 |

El MDE (HR=2.0) exige **~52 rupturas**.

## 4. Validación Monte Carlo de la fórmula

Simulación de la comparación de dos tasas de Poisson (exposición 1:1), 20 000
réplicas, semilla 12345:

| HR | N Schoenfeld | Potencia empírica |
|---:|---:|---:|
| 1.5 | 150.4 | 0.87 |
| 2.0 | 51.5 | 0.91 |
| 3.0 | 20.5 | 0.95 |

La potencia empírica es ≥0.87 en los N calculados: la fórmula es **conservadora**
(los N reportados son cotas inferiores seguras). Usar 52 rupturas para HR=2.0
cumple el objetivo de 0.80 con margen.

## 5. Duración de sesión requerida

N=52 rupturas (HR=2.0), asumiendo 1 impacto/segundo (optimista):

| Media impactos/ruptura | Duración |
|---:|---:|
| 100 (Range Break 100) | 5 147 s ≈ **1.4 h** |
| 200 (Range Break 200) | 10 295 s ≈ **2.9 h** |

Barrido de segundos por impacto para HR=2.0, N=52:

| s/impacto | Range Break 100 | Range Break 200 |
|---:|---:|---:|
| 0.5 | 0.71 h | 1.43 h |
| 1.0 | 1.43 h | 2.86 h |
| 2.0 | 2.86 h | 5.72 h |
| 5.0 | 7.15 h | 14.3 h |
| 10.0 | 14.3 h | 28.6 h |

Nota de realismo: "impacto" es un toque del límite, no un tick. Si el rango tiene
varios ticks de ancho, los impactos son más raros que los ticks, y la duración
**escala hacia arriba**. El supuesto de 1 impacto/s ya es optimista.

## 6. Efecto mínimo detectable (MDE) por capacidad de sesión

Asumiendo 1 impacto/s y Range Break 100:

| Capacidad de sesión | ~Rupturas | HR detectable |
|---:|---:|---:|
| 15 min | 9 | ≥ 5.25 |
| 60 min | 36 | ≥ 2.29 |
| 120 min | 72 | ≥ 1.80 |
| 240 min | 144 | ≥ 1.51 |
| 480 min | 288 | ≥ 1.34 |

Incluso una sesión de una hora solo detecta HR ≥ 2.3, y una de 15 minutos solo
HR ≥ 5.3. Son efectos enormes, muy por encima de cualquier estructura plausible
y económicamente significativa.

## 7. Veredicto

```text
UNDERPOWERED — DO_NOT_RUN
```

Justificación:

1. El MDE (HR=2.0) exige ~52 rupturas.
2. A 1 impacto/s y Range Break 100 son ~1.4 h de ticks continuos; con tasas de
   impacto realistas, 3–15+ h.
3. Las sesiones demo efímeras observadas en el proyecto (~4 min, WebSocket que
   se corta ~120 s, OTP de un solo uso, `collect_ticks_resilient`) no sostienen
   una recolección limpia de horas de forma fail-closed.
4. Una sesión de 15–60 min solo puede detectar HR ≥ 2.3–5.3: un efecto tan grande
   que, de existir, haría inviable el propio mercado; no es una hipótesis útil.

Conclusión terminal: `INSUFFICIENT_EVIDENCE` por falta de potencia intrasesión.
**No se abre confirmation.** Aplicada la condición de cancelación de
`s3-decision-matrix.md`, el estudio no se ejecuta.

## 8. Opciones honestas hacia adelante (no ejecutadas)

1. **Reformular la unidad de análisis** al evento ~100× más frecuente: la
   dirección del movimiento **tras cada impacto de límite** (rebote vs cruce),
   en lugar de la ruptura misma. Esto recupera potencia pero es una hipótesis
   distinta (más próxima a contratos de dirección/toque), que exigiría un
   preregistro nuevo y reabre el solapamiento conceptual con Rise/Fall.
2. **Pivotar el descubrimiento estadístico a fuentes persistentes** (CFTC COT,
   SEC EDGAR — dominio público) donde la historia retenida permite potencia sin
   la restricción efímera. Es una vía real y consistente con el protocolo S3,
   pero fuera de la familia Range Break y sin precio ejecutable.
3. **Aceptar el resultado**: la hipótesis de hazard de Range Break no es
   confirmable bajo `EPHEMERAL_ONLY`. Es un hallazgo negativo legítimo.

Ninguna de las tres se activa sin aprobación explícita del usuario.

## 9. Costos

- Recursos GCP: 0.
- Sesiones ejecutadas: 0.
- APIs invocadas: 0.
- Costo GCP incremental: USD 0.
