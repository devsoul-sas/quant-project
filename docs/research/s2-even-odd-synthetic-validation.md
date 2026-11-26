# S2 — Validación sintética walk-forward Even/Odd (bloque 1)

Fecha: 2026-11-23

## Alcance y protocolo

- Evidencia: `OWNED_SYNTHETIC_TICK_PROXY` (datos propios, no históricos de Deriv).
- Procesos: dígito uniforme y paridad Markov con persistencia 0.9.
- Semillas preregistradas para este bloque: 1–20.
- Por semilla: 180 ticks; 3 folds; 20 ticks de warm-up local + 10 pronósticos forward por fold; purge 20; embargo 5; holdout sellado de 20 ticks.
- Total por proceso: 600 pronósticos OOS.
- Economía sintética simétrica: ask 1, payout 2, solo para fijar break-even en 0.5; no representa propuestas observadas de Deriv.
- Riesgo por fold: drawdown máximo 5 unidades sintéticas, 3 pérdidas consecutivas, cooldown de 2 decisiones.
- Comparadores: moneda justa determinista (probabilidad 0.5) y no-operar.
- Métricas primarias: Brier y calibración; hit rate de entradas es secundario y condicionado por selección.
- Holdout: no abierto.

## Resultados

| Proceso | Pronósticos | Entradas estrategia | Aciertos estrategia | Hit rate condicionado | Brier estrategia | Brier aleatorio | Semillas con mejor Brier | Error calibración estrategia | Error calibración aleatorio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dígito uniforme | 600 | 13 | 6 | 0.461538 | 0.2617458333 | 0.25 | 8/20 | 0.14325 | 0.085 |
| Paridad Markov 0.9 | 600 | 276 | 190 | 0.688406 | 0.2648333333 | 0.25 | 8/20 | 0.22650 | 0.080 |

Baseline aleatorio después del mismo motor de riesgo:

- Dígito uniforme: 291/558 = 0.521505.
- Paridad Markov: 260/533 = 0.487805.
- No-operar: 0 entradas por construcción.

## Interpretación

1. En dígito uniforme, la estrategia no supera al baseline: peor Brier, peor calibración y muy pocas entradas. Resultado esperado y útil como control negativo.
2. En Markov 0.9 aparece un hit rate alto entre las entradas seleccionadas, porque el proceso sintético fue diseñado con persistencia fuerte. Sin embargo, la probabilidad emitida por el baseline de frecuencia incondicional está peor calibrada que 0.5 en el conjunto completo: Brier 0.26483 frente a 0.25 y mejor Brier en solo 8/20 semillas.
3. Por tanto, el resultado Markov es una pista para estudiar un predictor condicional de transición, no evidencia de que el motor actual esté calibrado.
4. No se abrió ningún holdout y no se optimizaron parámetros contra estos resultados.
5. No hay economía observada de Deriv, así que no se calculan ROI, P/L, profit factor ni rentabilidad.

## Conclusión del bloque

`NO_SYNTHETIC_CALIBRATION_ADVANTAGE` para el motor Even/Odd actual en ambos procesos según la métrica primaria Brier.

Esto no descarta una hipótesis Markov condicional futura; exige implementarla y validarla como una hipótesis separada, sin reutilizar estos datos como holdout.

`profitability_claim=false`
`promotion_eligibility=NOT_ELIGIBLE`
