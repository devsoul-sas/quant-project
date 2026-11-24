# Protocolo preregistrado de sesión — Even/Odd

- Estado: preregistro inicial
- Fecha: 2026-11-23
- Alcance: paper/demo efímero
- Hipótesis independiente: paridad del último dígito

## Invariantes

La sesión usa TTL estricto menor de 24 horas. Cada sesión comienza sin estado de mercado, features o parámetros aprendidos. Ninguna sesión aprende de una sesión anterior. No se persiste ningún tick, propuesta, feature, decisión, resultado, métrica o modelo derivado de Deriv.

Las únicas conclusiones intrasesión son `NO_EDGE`, `INSUFFICIENT_EVIDENCE` y `PAPER_ELIGIBLE`. Para este release, `real_money = EXCLUDED`.

## Mercado y disponibilidad

El candidato es Volatility 10 estándar, nunca una variante `1s`. El código del símbolo se obtiene mediante `active_symbols`; no se congela por nombre supuesto. Antes de cualquier propuesta, `contracts_for` debe demostrar simultáneamente `DIGITEVEN` y `DIGITODD`, expiry por tick y cero barreras. Una ausencia o contradicción produce `NO_TRADE`.

## Representación

El último dígito se obtiene exclusivamente del precio mostrado con el `pip_size` publicado por el proveedor. No se convierte desde `float`, no se infiere del exponente accidental de `Decimal` y se conservan ceros finales.

## Hipótesis

- Nula: la probabilidad condicional de paridad es 50/50 y no supera el break-even contemporáneo.
- Alternativa operativa: una cota conservadora para un lado supera su break-even más un margen preregistrado.
- La volatilidad del índice no constituye evidencia de predictibilidad del dígito.

## Economía

En cada checkpoint de decisión se solicitan propuestas contemporáneas para ambos lados. Para cada contrato:

```text
break_even = ask_price / payout
```

Una propuesta ausente, stale, inválida o no correlacionable con el checkpoint produce `NO_TRADE`. No se reutiliza una propuesta para una decisión posterior.

## Diseño causal intrasesión

1. **Descubrimiento:** símbolo, `pip_size`, contratos y duración.
2. **Warm-up:** acumular la muestra mínima sin entrar.
3. **Validación forward:** evaluar únicamente ticks posteriores al warm-up; ningún resultado futuro entra en la decisión que lo precede.
4. **Paper:** una decisión usa solo el historial disponible y se liquida con el tick de expiry posterior.
5. **Zeroización:** al terminar o expirar, eliminar todo el estado.

Los parámetros no cambian durante la sesión. Los outcomes forward no seleccionan una nueva ventana, feature, margen o dirección.

## Tamaño de muestra y multiplicidad

El baseline es 50/50. `min_samples` no se toma de fixtures unitarias: se calcula antes de operar usando el break-even observado, el efecto mínimo económicamente útil, potencia mínima de 80% y alfa familiar. Se corrigen los dos lados mediante Bonferroni. Si el tamaño requerido no cabe de forma segura dentro de la sesión, la conclusión es `INSUFFICIENT_EVIDENCE`.

La decisión usa una cota inferior de Wilson con el `z_score` congelado. La cota debe superar estrictamente `ask_price / payout` más `min_edge_probability`. Igualdad o evidencia inferior produce `NO_TRADE`.

## Features permitidas en el primer release

El primer release usa únicamente frecuencia causal par/impar. Transiciones, rachas, dependencia o calibración adicional requieren un release posterior y una nueva corrección por múltiples pruebas. No se habilitan por inspección de resultados de la sesión actual.

## Criterios terminales

- `NO_EDGE`: muestra forward suficiente y la cota conservadora no supera break-even.
- `INSUFFICIENT_EVIDENCE`: muestra, economía, catálogo o tiempo insuficientes.
- `PAPER_ELIGIBLE`: la cota conservadora supera break-even más margen y habilita únicamente simulación paper durante la misma sesión.

`PAPER_ELIGIBLE` no sobrevive al cierre de sesión ni autoriza demo automática o dinero real.

## Riesgo

Stake fijo, máximo una posición paper a la vez, sin martingala, progresiones, recuperación de pérdidas, recarga o selección retrospectiva. `NO_TRADE` es el resultado predeterminado.
