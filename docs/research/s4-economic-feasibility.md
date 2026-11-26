# S4 — Factibilidad económica

Fecha: 2026-11-24
Estado: `ASSESSMENT_ONLY — NO EXECUTION`

## 1. Modelo de costos

Todo backtest de S4.1 debe modelar, sin excepción:

| Costo | Modelado |
|---|---|
| Comisión maker/taker | por tier del proveedor, por lado |
| Spread | bid/ask (no precio medio) |
| Slippage | conservador, función de volumen y horizonte |
| Latencia | decisión → ejecución (vía velas cerradas) |
| Tamaño mínimo | granularidad de la posición |
| Conversión de moneda | COP↔USD/stablecoin (costo de fondeo, una vez) |

El P/L es **neto de todos los costos**. La accuracy no es el criterio.

## 2. Comisiones verificadas (corte 2026-11-24)

| Venue | Maker / Taker (tier base) | Round-trip maker+taker |
|---|---:|---:|
| Binance VIP0 (sin BNB) | 0.100% / 0.100% | 0.20% |
| Binance VIP0 (BNB 25% off) | 0.075% / 0.075% | 0.15% |
| Kraken Pro tier 1 | 0.40% / 0.80% | 1.20% |
| Kraken Pro tier 4 ($25K+/30d) | 0.20% / 0.35% | 0.55% |
| Coinbase Advanced | **NO VERIFICADO** (página de fees tras Cloudflare) | — |

Fuentes: `binance.com/en/fee/schedule` y `kraken.com/pro/fees` (verificadas por
subagentes 2026-11-24; detalle en `s4-data-provider-assessment.md`).

## 3. Break-even por operación

Spread ~1 bp (BTC) + slippage conservador ~5 bp (total 0.06%):

| Venue | Round-trip maker | Break-even edge bruto por trade |
|---|---:|---:|
| Binance VIP0 (sin BNB) | 0.20% | ~0.26% |
| Binance VIP0 (BNB) | 0.15% | ~0.21% |
| Kraken Pro T1 | 1.20% | ~1.26% |
| Kraken Pro T4 | 0.55% | ~0.61% |

Interpretación: para ganar neto, el precio debe moverse a favor más del break-even
**en cada operación**, en promedio. Binance es el único tier que deja margen a un
horizonte de minutos/horas. Kraken exige ~1.26% de movimiento favorable por trade
en tier 1 — inviable para una estrategia activa.

## 4. Drag anual por frecuencia de operación

Retención neta de capital tras fees (round-trip maker), por frecuencia:

| Trades/año | Binance (0.20%) | Binance BNB (0.15%) | Kraken T1 (1.20%) |
|---:|---:|---:|---:|
| 52 (1/semana) | ~90% | ~92% | ~53% |
| 104 (2/semana) | ~81% | ~86% | ~28% |
| 365 (1/día) | ~48% | ~58% | ~1% |

Lectura decisiva:

- **Trading intradía de minutos** (varias operaciones/día) queda **destruido por
  fees** en cualquier venue retail. Inviable económicamente.
- **Swing de horas/días** (1–2 operaciones/semana) mantiene el drag en ~10–20%
  anual en Binance, tolerable; en Kraken T1 destruye 47–72% del capital al año.
- El horizonte primario debe ser **≥ 1 hora, idealmente swing de varios días**, no
  por preferencia sino por aritmética de fees.

## 5. Implicación para el horizonte

El mandato S4 dice "minutos u horas, evitando HFT". La aritmética de fees refina
esto: el extremo "minutos" es económicamente inviable a tarifas retail; el rango
**horario a diario** es el punto de equilibrio entre número de observaciones y
costo. El preregistro de S4.1 fijará el horizonte primario en ese rango.

## 6. Baseline exigente: Buy & Hold

BTC y ETH han mostrado deriva direccional de largo plazo. Buy & Hold es un baseline
fuerte, no trivial. Una estrategia activa debe superar a Buy & Hold **ajustado al
riesgo y neto de costos**, lo que en cripto es un listón alto. Si una estrategia
solo "bate al efectivo" pero no a Buy & Hold, no se promueve.

## 7. Fondeo y conversión (Colombia)

- Conversión COP→USDT/USDC: costo único de entrada/salida (típicamente ~1–3%
  ida+vuelta vía P2P o rampa local; a verificar). Es costo de fondeo, no por trade.
- Impuestos y regulación colombiana sobre cripto: fuera del alcance técnico de S4,
  pero relevante para la decisión final de operar capital real (posterior).

## 8. Presupuesto

- Cloud incremental: **USD 0** (ejecución local).
- Sin hardware nuevo.
- Sin contratar servicios de datos en S4.0.
- Costo directo de S4.0: solo tiempo/ingeniería local.

## 9. Condición de viabilidad y de parada

```text
GO si:
  existe un proveedor con retención de histórico defendible
  Y un tier de comisión <= ~0.2% round-trip efectivo
  Y el horizonte primario >= 1 hora (swing)

STOP si:
  ningún proveedor desbloquea retención de histórico dentro del presupuesto
  O el único venue económicamente tolerable es jurídicamente inviable
```

La decisión final de proveedor (con estas dos variables: comisión y derechos de
retención) está en `s4-data-provider-assessment.md`. Si ambas no se cumplen a la
vez, la etapa se detiene — condición explícita del mandato S4.
