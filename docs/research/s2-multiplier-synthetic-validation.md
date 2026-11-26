# S2 — Validación sintética walk-forward Multipliers (bloque 2)

Fecha: 2026-11-23

## Alcance

Este bloque evalúa la señal técnica de reversión `MULTUP` / `MULTDOWN` mediante un outcome no económico `target-before-stop`. Los barriers son movimientos relativos del quote sintético, no precios, comisiones, payouts ni settlement observados de Deriv.

- Evidencia: `OWNED_SYNTHETIC_TICK_PROXY`.
- Holdout: sellado; no se abrió en ninguna corrida.
- Dinero real: ausente por construcción.
- P/L, ROI, profit factor y EV monetario: no disponibles.
- Baselines:
  - Dirección aleatoria en las mismas oportunidades técnicas, con su probabilidad estimada exclusivamente en train.
  - No-operar.

## Protocolo congelado

- Semillas explícitas: 1–20, sin selección retrospectiva.
- 600 ticks por semilla.
- 3 folds por semilla.
- 20 ticks de warm-up local dentro de cada test fold.
- Train y test separados por purge de 20 ticks; embargo de 5 ticks.
- 100 ticks test por fold; holdout sellado de 50 ticks.
- Detector:
  - Ventana: 19 retornos / 20 ticks de historia.
  - Referencia: desplazamiento desde el inicio de ventana.
  - `abs(z-score) > 1`.
  - Deceleración estrictamente positiva.
  - Frecuencia mínima de retorno: 0.
- Evidencia train mínima: 5 señales settled por fold.
- Settlement:
  - Target relativo: 0.00005.
  - Stop relativo: 0.00005.
  - Horizonte máximo: 5 ticks.
  - `TIMEOUT` cuenta como no-target para calibración, pero como resultado neutro para el reducer de riesgo.
- Una sola posición por método: cada señal reserva el horizonte completo congelado.
- Riesgo sintético por fold: drawdown 10 unidades, 5 pérdidas consecutivas, cooldown 2 decisiones.
- Métrica primaria: Brier OOS de `P(target-before-stop)` estimada en train.
- Métricas secundarias: frecuencia target condicionada a entrada, stops, timeouts y estabilidad entre semillas.

## Corrección metodológica durante el bloque

Un piloto inicial fijaba la probabilidad del baseline aleatorio en 0.5. Ese supuesto era inválido porque `TIMEOUT` hace que el evento `TARGET` no sea una moneda justa, incluso con barriers simétricos. El defecto produjo una comparación artificialmente favorable en random walk.

Se añadió una regresión determinista y se corrigió el baseline para estimar su propia tasa target únicamente en train. Se repitieron las mismas 20 semillas y parámetros. Los resultados del piloto previo quedaron invalidados y no se usan en las conclusiones siguientes.

## Resultados corregidos

| Proceso | Señales OOS | Entradas estrategia | Target / Stop / Timeout | Target rate estrategia | Entradas aleatorio | Target rate aleatorio | Brier estrategia | Brier aleatorio | Mejor Brier por semilla |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ornstein–Uhlenbeck | 522 | 517 | 290 / 223 / 4 | 0.560928 | 518 | 0.530888 | 0.2512725370 | 0.2610716969 | 11/20 |
| Random walk | 569 | 569 | 21 / 19 / 529 | 0.036907 | 569 | 0.036907 | 0.0374158351 | 0.0365706215 | 10/20 |
| GBM | 561 | 555 | 284 / 271 / 0 | 0.511712 | 556 | 0.526978 | 0.2616583157 | 0.2577372424 | 8/20 |
| Regímenes de volatilidad | 542 | 536 | 228 / 202 / 106 | 0.425373 | 537 | 0.396648 | 0.3795130222 | 0.3539296360 | 6/20 |

Todas las 20 corridas de cada proceso tuvieron señales train suficientes y al menos una entrada OOS. Holdouts abiertos: 0.

## Interpretación

1. **Ornstein–Uhlenbeck:** la señal reconoce parte de la reversión incorporada deliberadamente en el generador. Mejora el Brier medio y la tasa target frente a dirección aleatoria, pero solo gana en 11/20 semillas. La estabilidad es insuficiente y el hallazgo es específico de un proceso sintético construido para revertir a la media.
2. **Random walk:** no hay ventaja direccional; ambos métodos obtienen la misma tasa target agregada. La estrategia tiene Brier ligeramente peor. La gran cantidad de timeouts confirma que 0.5 no era un baseline probabilístico válido.
3. **GBM:** la estrategia queda por debajo del baseline tanto en Brier como en tasa target.
4. **Regímenes de volatilidad:** aunque la tasa target agregada supera a la aleatoria, la calibración es claramente peor y solo gana en 6/20 semillas. No es evidencia estable.
5. Ningún resultado permite inferir payout, beneficio o ventaja sobre los índices propietarios de Deriv. Los generadores DevSoul no reproducen su distribución ni su algoritmo.

## Conclusión

`INSUFFICIENT_SYNTHETIC_STABILITY`

- `PAPER_ELIGIBLE`: no.
- `profitability_claim=false`.
- `economic_metrics_available=false`.
- `promotion_eligibility=NOT_ELIGIBLE`.

La respuesta positiva parcial sobre OU valida que el pipeline puede detectar una propiedad deliberadamente presente en un proceso propio. No valida la estrategia sobre Deriv ni autoriza demo execution. El siguiente incremento científico debe congelar sensibilidad de barriers/horizonte y criterios de estabilidad antes de cualquier nueva corrida; no debe optimizarlos contra estos resultados.

## Impacto operativo y costos

- Ejecución local y offline; no usa APIs de Deriv ni de terceros.
- Persistencia de datos Deriv: ninguna.
- Recursos GCP creados o modificados: ninguno.
- Logs, métricas y almacenamiento GCP adicionales frente a la línea base: ninguno.
- Impacto estimado en costo GCP: USD 0.
