# Protocolo preregistrado de sesión — Multipliers

- Estado: preregistro inicial
- Fecha: 2026-11-23
- Alcance: paper/demo efímero
- Hipótesis independiente: régimen direccional causal

## Invariantes

La sesión usa TTL estricto menor de 24 horas. Cada sesión comienza sin estado de mercado, features o parámetros aprendidos. Ninguna sesión aprende de una sesión anterior. No se persiste ningún tick, propuesta, feature, decisión, settlement, métrica o modelo derivado de Deriv.

Las únicas conclusiones intrasesión son `NO_EDGE`, `INSUFFICIENT_EVIDENCE` y `PAPER_ELIGIBLE`. Para este release, `real_money = EXCLUDED`.

## Selección runtime del mercado

1. Consultar `active_symbols`.
2. Preferir un Drift Switching estándar; excluir nombres `1s`.
3. Consultar `contracts_for` y exigir simultáneamente `MULTUP` y `MULTDOWN`.
4. Ambos deben declarar `no_expiry`, cero barreras y un `multiplier_range` positivo no vacío con intersección común.
5. Si el candidato no cumple, evaluar únicamente Volatility 10 estándar como fallback.
6. Si tampoco cumple, producir `NO_TRADE`.

No se codifica el identificador de Drift Switching ni un multiplicador observado en otra sesión. El multiplicador del release se toma exclusivamente de la intersección descubierta en runtime.

## Hipótesis

- Nula: retorno y consistencia direccional causales no generan expectativa neta positiva después de todos los costos y cierres.
- Alternativa operativa: un régimen congelado produce una expectativa paper conservadora positiva dentro de la porción forward de la sesión.

Even/Odd, EURGBP y otros mercados no aportan features, parámetros ni evidencia a esta hipótesis.

## Política primaria

El primer release usa una sola regla explicable:

- retorno absoluto sobre `lookback_ticks`;
- proporción de movimientos alineados con la dirección total;
- `minimum_absolute_return` y `minimum_directional_consistency` congelados;
- una sola configuración primaria, sin grid intrasesión.

Los valores empleados en fixtures unitarias no son parámetros operativos. Los outcomes forward no cambian lookback, umbral, multiplicador, stake o cierres.

## Economía y proposal

La proposal contemporánea debe incluir spot de entrada, ask/stake, multiplicador permitido y comisión. No se envían duración, `duration_unit`, expiry ni barrera porque el contrato es `no_expiry`.

El cálculo paper documentado es:

```text
P/L = (% movimiento × multiplier × stake) − comisión − slippage
```

Además se modelan latencia, stop-out, stop-loss, take-profit y máximo de tiempo/ticks. Si comisión, slippage, latencia o reglas de stop-out están `UNAVAILABLE`, la salida es `NO_TRADE`.

Un replay basado en ticks se etiqueta siempre `ESTIMATED`; solo el `profit` final del proveedor con `is_sold == 1` puede ser `OBSERVED`. `status="sold"` es terminal válido.

## Diseño causal intrasesión

1. **Descubrimiento:** mercado, catálogo y multiplicadores.
2. **Warm-up:** acumular `lookback_ticks` sin entrar.
3. **Validación forward:** las decisiones usan solo ticks anteriores; el cierre posterior no entra en sus features.
4. **Paper:** aplicar cierre por stop-loss, take-profit, stop-out o máximo de ticks/tiempo.
5. **Zeroización:** eliminar todo al finalizar, fallar o alcanzar el TTL.

No se encadenan sesiones ni se usa P/L previo para modificar stake o dirección.

## Criterios terminales

- `NO_EDGE`: muestra forward suficiente y expectativa neta conservadora no positiva.
- `INSUFFICIENT_EVIDENCE`: muestra, catálogo, economía, reglas de cierre o tiempo insuficientes.
- `PAPER_ELIGIBLE`: límite conservador de expectativa neta positivo bajo costos y estrés preregistrados; habilita solo paper en la misma sesión.

`PAPER_ELIGIBLE` no sobrevive al cierre de sesión ni autoriza compras demo automáticas o dinero real.

## Riesgo

Stake fijo, multiplicador mínimo permitido por el release/runtime, máximo una posición paper abierta, pérdida y drawdown intrasesión acotados, cierre antes del TTL y kill switch monotónico. Se prohíben martingala, progresiones, recuperación de pérdidas, recarga y aumento de multiplicador tras pérdidas. `NO_TRADE` es el resultado predeterminado.
