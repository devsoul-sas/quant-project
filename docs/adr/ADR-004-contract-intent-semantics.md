# ADR-004 — Semántica de intención y contrato

- Estado: aceptada para MVP
- Fecha: 2026-09-29

## Problema

`BUY / SELL / WAIT` mezcla predicción, intención y operación de API. En Deriv, `buy` compra un contrato; `sell` cierra anticipadamente un contrato existente cuando está permitido. `SELL` no representa necesariamente una nueva posición bajista.

## Decisión

La estrategia emite:

```text
NO_TRADE
ENTER_CONTRACT
EXIT_CONTRACT
```

`ENTER_CONTRACT` contiene como mínimo:

```text
symbol
contract_type
duration o date_expiry
duration_unit
basis
amount_requested
currency
barrier/barrier2 cuando aplique
exit_policy
strategy_reason
```

`EXIT_CONTRACT` contiene:

```text
position_id
minimum_sell_price o market
exit_reason
```

El stake aprobado lo decide riesgo; la estrategia no controla directamente la exposición.

## Piloto

La primera semántica contractual de fixtures es Rise/Fall, representada por `CALL`/`PUT` al traducir hacia Deriv, con horizonte sintético inicial de 5 ticks. Símbolo, moneda, stake y restricciones reales se descubrirán dinámicamente después de resolver la licencia de datos y comprobar una cuenta demo.

No se conserva inventario de disponibilidad de Deriv. Esta elección solo define un tracer sintético; no declara edge ni autoriza trading.

## Consecuencias

- La UI puede mostrar etiquetas amigables, pero el ledger conserva intent y contract spec completos.
- `contracts_for` valida disponibilidad antes de solicitar propuestas.
- La traducción Deriv vive en un adaptador.
- El backtest debe distinguir economía inferida de propuestas observadas.
