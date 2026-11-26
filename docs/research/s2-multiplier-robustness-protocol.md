# S2 — Protocolo prerregistrado de robustez para Multipliers

Fecha de congelación: 2026-11-23
Estado al congelar: semillas 21–60 no ejecutadas; holdout no abierto.

## Propósito

Evaluar si la ventaja parcial observada en el control Ornstein–Uhlenbeck es estable o fue variación de la cohorte exploratoria 1–20. Este protocolo no estima rentabilidad ni reproduce los índices propietarios de Deriv.

## Separación de cohortes

- Exploración ya observada: semillas 1–20; queda excluida de toda confirmación.
- Desarrollo confirmatorio de robustez: semillas 21–60.
- Holdout reservado: semillas 61–80; no se genera ni abre durante este bloque salvo que todos los gates de desarrollo pasen.
- Está prohibido sustituir, eliminar o reordenar semillas por sus resultados.

## Protocolo común

- 600 ticks por semilla.
- 3 folds walk-forward.
- Lookback y purge: 20 ticks.
- Embargo: 5 ticks.
- Test: 100 ticks por fold.
- Holdout estructural sellado: 50 ticks.
- Historia local OOS: 20 ticks; el warm-up no se puntúa.
- Detector: ventana 19, referencia por desplazamiento, `abs(z-score) > 1`, deceleración positiva y frecuencia mínima de retorno 0.
- Evidencia train mínima: 5 settlements.
- Riesgo sintético: drawdown 10 unidades, 5 pérdidas consecutivas y cooldown 2.
- Baseline: dirección aleatoria sobre las mismas oportunidades, con probabilidad target estimada exclusivamente en train.
- No-operar permanece como baseline de exposición cero.
- `TIMEOUT` es no-target para Brier y neutro para el reducer de riesgo.
- Una señal reserva el horizonte completo para impedir posiciones solapadas.

## Procesos

1. Ornstein–Uhlenbeck: control positivo de reversión.
2. Random walk: control negativo sin edge direccional construido.
3. GBM: estrés de tendencia multiplicativa.
4. Regímenes de volatilidad: estrés de no-estacionariedad.

Parámetros del generador: volatilidad `0.01`, velocidad de reversión `0.15` cuando aplica y regímenes `(10, 300)`, `(100, 300)`.

## Configuración primaria

- Target relativo: `0.00005`.
- Stop relativo: `0.00005`.
- Horizonte: 5 ticks.

El gate primario se calcula únicamente con esta configuración. Ninguna sensibilidad puede reemplazarla.

## Matriz de sensibilidad congelada

1. Target/stop `0.000025`, horizonte 5.
2. Target/stop `0.00005`, horizonte 3.
3. Configuración primaria: target/stop `0.00005`, horizonte 5.
4. Target/stop `0.00005`, horizonte 10.
5. Target/stop `0.0001`, horizonte 5.

La matriz mide fragilidad. Está prohibido seleccionar la celda con mejor resultado como nueva configuración primaria dentro de este experimento.

## Estadística pareada

Por proceso y celda se calcula por semilla:

`delta_brier = brier_estrategia - brier_baseline`

Un delta negativo favorece la estrategia.

Se reportan:

- Media pareada.
- Intervalo percentile bootstrap bilateral del 95%, 5.000 remuestras, seed estadística fija `20261123`.
- Número de semillas con delta estrictamente negativo.
- Empates.
- Semillas puntuables y no puntuables.
- Diferencia agregada de target rate solo como diagnóstico secundario.

## Gate de desarrollo

Todos los criterios son obligatorios:

### Integridad

1. Las 40 semillas deben ejecutarse para cada proceso primario.
2. Las 40 deben ser puntuables en OU y random walk.
3. Holdouts abiertos: 0.
4. No puede existir una afirmación económica o de rentabilidad.

### Control positivo OU, configuración primaria

1. Delta Brier medio `< 0`.
2. Límite superior del intervalo bootstrap 95% `< 0`.
3. Estrategia gana al menos 28 de 40 semillas.
4. Target rate agregado de estrategia `>` baseline.

### Control negativo random walk

No debe producir un falso positivo. Se exige que al menos una de estas condiciones sea cierta:

- El intervalo bootstrap 95% contiene cero; o
- El delta Brier medio es `>= 0`.

### Estrés de proceso

- Al menos 3 de los 4 procesos deben tener delta Brier medio `<= 0`.
- Ningún proceso puede tener un límite inferior del intervalo 95% `> 0`, lo que indicaría degradación consistentemente peor que el baseline.

### Sensibilidad OU

- Al menos 4 de las 5 celdas deben tener delta Brier medio `< 0`.
- Al menos 3 de las 5 celdas deben ganar en 24 o más de 40 semillas.
- Todas las celdas deben mantener holdout cerrado.

## Decisión automática

- Si todos los criterios pasan: `ROBUSTNESS_GATE_PASSED`; queda permitido abrir una sola vez la cohorte 61–80 en un bloque posterior.
- Si cualquier criterio falla: `NO_EDGE` si la primaria OU falla materialmente; en otro caso `INSUFFICIENT_SYNTHETIC_STABILITY`.
- Un fallo mantiene el holdout 61–80 sellado y prohíbe reajustar este protocolo usando sus resultados.
- Ningún resultado de este bloque puede producir `PAPER_ELIGIBLE` por sí solo.

## Restricciones operativas

- Datos propios y ejecución local/offline.
- Sin llamadas a Deriv.
- Sin persistencia de ticks Deriv.
- Sin dinero real.
- Sin recursos GCP nuevos; costo GCP incremental esperado: USD 0.
