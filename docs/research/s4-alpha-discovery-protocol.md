# S4 — Protocolo de descubrimiento de alpha y trading propietario

Fecha: 2026-11-24
Estado: `DESIGN_ONLY — AWAITING_S4.0_APPROVAL` (no ejecuta backtests ni paper trading)

## 1. Propósito y frontera

Definir el protocolo de S4.1 (backtesting económico), S4.2 (gate de edge económico)
y S4.3 (paper trading) antes de ejecutar nada. Este documento es de diseño: no
corre experimentos, no abre holdouts, no opera.

Objetivo terminal (posterior y condicionado): demostrar rentabilidad neta ajustada
al riesgo sobre capital propio en cripto Spot, sin apalancamiento. La
comercialización SaaS queda fuera y diferida a evidencia verificable.

## 2. Escalera de afirmaciones

Se reutiliza la separación de S3:

```text
S0 descripción → S1 estructura → S2 predicción → S3 candidato a evaluación económica → E1 edge económico
```

S4 solo persigue `E1` (edge económico neto) y únicamente tras evidencia fuera de
muestra y paper trading. Un resultado negativo es válido.

## 3. Familias de estrategia y orden de evaluación

Pre-registrado, en este orden y sin reordenar tras ver datos:

1. **Trend Following** (primaria).
2. **Momentum** (primaria).
3. **Mean Reversion** (hipótesis independiente posterior; NO ajuste retrospectivo
   de las anteriores).

Reglas duras:

- Sin Martingale, progresiones, recuperación de pérdidas ni recargas.
- Sin búsqueda ilimitada de hiperparámetros: cada familia usa una configuración
  primaria congelada y, como mucho, un grid acotado preregistrado con corrección
  por multiplicidad.
- Sin modelos complejos (ML, ensembles) hasta que un baseline simple muestre
  ventaja OOS estable. Primero: reglas lineales/seriales simples.
- Las hipótesis rechazadas en S2 (Even/Odd, Multipliers) y S3 (Range Break) no se
  reabren ni se reetiquetan.

## 4. Universo de activos (selección objetiva, predefinida)

Criterios congelados antes de observar resultados:

1. Listado en el proveedor elegido con mercado Spot activo y par contra USDT/USDC.
2. Capitalización de mercado por encima de un umbral preregistrado.
3. Volumen diario por encima de un umbral preregistrado (liquidez).
4. Antigüedad de listado mínima (histórico suficiente, evita ICOs recientes).
5. Spread medio bajo y fee tier favorable.

Universo inicial objetivo: **3–6 activos** líquidos (p. ej. BTC, ETH, y 1–4 más),
seleccionados por los criterios anteriores. El tamaño exacto y la lista se congelan
en el preregistro específico de S4.1. Añadir o quitar un activo tras ver resultados
crea un protocolo nuevo.

## 5. Horizonte y frecuencia

- Granularidad de datos: velas de minutos (1m, 5m, 15m, 1h).
- Horizontes de operación: minutos a horas. **No HFT** (nada de sub-minuto ni
  arbitraje de latencia).
- El horizonte primario se congela por familia antes de evaluar.

## 6. Datos y derechos (gate previo)

Antes de persistir una sola vela:

1. Resolver los derechos de retención, derivados y uso comercial del proveedor
   elegido (ver `s4-data-provider-assessment.md`).
2. Clasificar en `ALLOWED_NOW` / `EPHEMERAL_ONLY` / `BLOCKED_PENDING_PERMISSION`.
3. Si el proveedor no otorga retención explícita para investigación propietaria,
   la persistencia queda **bloqueada** y S4.1 no puede usar histórico real; la
   etapa se detiene (ver `s4-economic-feasibility.md`).
4. Registro de lineage: URL, versión, fecha, SHA-256 del dataset, schema.

## 7. Backtesting económico (S4.1)

### 7.1 Arquitectura

Reutilizar el núcleo existente sin reescribirlo. Separar medición, señal, decisión,
riesgo, estado y ejecución. El replay debe ser determinista y causal: una señal que
observa la vela `t` entra en `t+1` o posterior, nunca en `t`.

### 7.2 Costos obligatorios (todos modelados, nunca omitidos)

- Comisión maker/taker por tier.
- Spread (bid/ask, no precio medio).
- Slippage conservador (función de volumen y horizonte).
- Latencia de decisión→ejecución.
- Restricciones de ejecución (post-only, market vs limit).
- Tamaño mínimo de operación.
- Costos de conversión de moneda cuando aplique (COP↔USD, stablecoin).
- (Solo si algún día se habilita: financiación/swap — excluido en Spot sin margen.)

El P/L es **neto de todos los costos**. Accuracy o hit rate no son el criterio.

### 7.3 Splits temporales

- Walk-forward con folds cronológicos (expanding o rolling justificado).
- **Purge y embargo** entre train y test (evitar leakage por features/objetivos
  solapados).
- Warm-up local dentro de cada fold OOS; no puntuar el warm-up.
- Holdout final **sellado** hasta congelar release; se abre una sola vez.

### 7.4 Baselines obligatorios

1. Buy & Hold (del universo).
2. Efectivo (cash).
3. Baseline aleatorio calibrado en train (mismas oportunidades).
4. Baselines simples por familia (p. ej. SMA cross para trend, lookback momentum).

Comparar contra todos. Una estrategia debe superar Buy & Hold y efectivo en
términos ajustados al riesgo, no solo al baseline aleatorio.

### 7.5 Inferencia

- `n_eff` (muestra efectiva) y dependencia temporal.
- Block/stationary bootstrap para intervalos de confianza.
- Corrección por comparaciones múltiples: FWER (Holm/maxT) para el gate; FDR (BH)
  solo para ordenar leads, nunca para promover.

## 8. Gate de edge económico (S4.2)

Congelar antes de ejecutar. El criterio primario es **rentabilidad neta ajustada
al riesgo**, no accuracy.

Métricas y criterios (umbrales se fijan en el preregistro específico):

| Criterio | Definición |
|---|---|
| EV neto | valor esperado por operación neto de costos, con IC |
| Profit Factor | ganancia bruta / pérdida bruta netas |
| Max Drawdown | máximo drawdown (absoluto y %) con límite |
| Sharpe / Sortino | con definición explícita de retorno, frecuencia y anualización |
| Estabilidad temporal | consistencia entre folds/subperiodos |
| Sensibilidad a costos | supervivencia bajo escenario adverso de fees/spread/slippage |
| Tamaño mínimo de muestra | n_eff mínimo preregistrado |

Regla de rechazo dura:

```text
PROMOVER solo si:
  límite inferior del IC del EV neto OOS > 0
  AND supera a Buy & Hold y efectivo (ajustado a riesgo)
  AND Max Drawdown <= límite
  AND Profit Factor >= umbral
  AND n_eff >= mínimo
  AND sobrevive al escenario adverso de costos
```

**No promover** una estrategia cuya rentabilidad desaparezca bajo supuestos
razonables de ejecución. La sensibilidad mide fragilidad, no selecciona la mejor
variante.

## 9. Paper trading (S4.3)

Solo para estrategias que superen el gate S4.2. Reutilizar sin duplicar:

- Risk Engine (límites, drawdown, kill switch).
- Ledger append-only (tamper-evident).
- State Machine (fases de sesión).
- Strategy Release (identidad inmutable: hashes de spec/código/riesgo).
- Validation Run.
- Experiment Registry.

Adaptadores de mercado **desacoplados** del dominio (puertos/provider-adapter); el
núcleo no conoce al proveedor.

Reglas de paper:

- Sin dinero real durante todo S4.
- Sin apalancamiento.
- Sin capital de terceros.
- `NO_TRADE` es el default fail-closed.
- El paper trading no genera afirmación de rentabilidad; solo evidencia de
  comportamiento operativo y compatibilidad con la hipótesis congelada.

## 10. Restricciones de presupuesto y alcance

- Presupuesto cloud incremental: USD 0 (ejecución local).
- Sin compras de hardware.
- Sin contratar servicios ni abrir cuentas en S4.0.
- Timebox S4: 30 días para determinar viabilidad inicial.
- El trading real exige un protocolo posterior, evidencia suficiente en paper y
  aprobación explícita del propietario.

## 11. Estados terminales permitidos

```text
INVALID_STUDY | DATA_RIGHTS_BLOCKED | INSUFFICIENT_EVIDENCE |
NO_REPLICABLE_STRUCTURE_WITHIN_SCOPE | STATISTICAL_STRUCTURE_ONLY |
NO_PREDICTIVE_ADVANTAGE | REPLICATION_FAILED | ECONOMIC_EVALUATION_ELIGIBLE |
PAPER_ELIGIBLE
```

Nunca: `REAL_MONEY_ELIGIBLE` dentro de S4.

## 12. Objetivo final (recordatorio)

Desarrollar un activo tecnológico que permita a DevSoul operar capital propio de
forma disciplinada. No fabricar evidencia favorable para conseguir inversión.
Un resultado negativo reproducido es un entregable válido.
