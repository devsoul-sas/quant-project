# ADR-009 — Economía de ejecución EURGBP con horizonte de cinco observaciones

- Estado: aceptada para investigación; promoción bloqueada
- Fecha: 2026-11-05
- Supersede cualquier supuesto de que un costo spot y una opción de pago fijo son equivalentes

## Contexto

La señal confirmada usa EURGBP diario con horizonte de cinco observaciones. BCE y Federal
Reserve H.10 son fixings de referencia y no contienen economía ejecutable.

El 2026-11-05 se consultó de forma pública, efímera y sin credenciales el endpoint
oficial de Deriv Options:

`wss://api.derivws.com/trading/v1/options/ws/public`

`active_symbols` confirmó `frxEURGBP`; `contracts_for` devolvió CALL/PUT diarios con
duración mínima 1 día y máxima 365 días. Esto demuestra capacidad contractual,
pero una duración `5d` calendario no equivale al horizonte causal de ADR-010. No
se solicitó una propuesta económica ni se conservó el payload.

## Decisión

Se separan dos productos y dos modelos incompatibles:

### Deriv Options CALL/PUT

- producto de pago fijo, no posición spot;
- costo/economía observada por propuesta: `ask_price`, `payout`, barrera/strike y
  expiración;
- break-even: `ask_price / payout`;
- valor esperado por contrato: `p * payout - ask_price`;
- no se añade rollover como si fuera una posición spot: la economía completa está
  embebida en la propuesta;
- solo `OBSERVED` puede usarse para una afirmación económica; `ESTIMATED` y
  `UNAVAILABLE` no promocionan.

### Broker spot/CFD (no seleccionado)

- requiere venue concreto;
- costo debe incluir spread de entrada/salida, slippage, comisión y swap/rollover
  direccional para cada noche (incluyendo reglas de triple swap);
- no se permite trasladar especificaciones de otro broker ni usar un promedio sin
  provenance.

## Gate antes del holdout

El holdout BCE permanece sellado. Deriv Options no es una ruta de promoción: su
TTL <24 h no permite observar y retener un contrato multidiario equivalente a
ADR-010. Solo podrá abrirse después de elegir un broker spot/CFD alternativo,
verificar términos, spread/slippage/comisión/swap y evidencia de paper execution,
y congelarlo en un `StrategyRelease`.

La mera disponibilidad técnica de un contrato no demuestra valor esperado positivo.
El hit rate H.10 de 0.5475 no se compara con una propuesta que no haya sido observada.

## Consecuencias

- `BinaryOptionEconomics` implementa break-even y EV con datos explícitos.
- `ContractProposal` falla cerrado cuando la economía es incompleta o
  contradictoria.
- no se persisten propuestas Deriv ni resultados derivados; el estado se elimina
  dentro del TTL <24 h;
- `promotion_eligibility = NOT_ELIGIBLE`;
- `profitability_claim = False`;
- `real_money = EXCLUDED`.
