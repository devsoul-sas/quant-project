# Protocolo económico — búsqueda de edge en FX diario (BCE)

- Estado: aceptada
- Fecha: 2026-11-04
- Congela: [ADR-007](../adr/ADR-007-ecb-daily-fx-source.md)

## Propósito

Definir, antes de observar el holdout sellado, el protocolo que convierte la
evidencia direccional en una decisión. Nada aquí afirma rentabilidad: las
métricas son direccionales y el costo se modela como fricción, no como P/L
monetario.

## Universo de hipótesis (congelado)

Estrategias diarias sobre el fixing del BCE (mid-point, EUR base):

1. Momentum con ventana N: CALL si el último fixing supera al de hace N días,
   PUT si cae.
2. Mean-reversion con ventana N: desvanecer el movimiento (CALL en caída, PUT en
   subida).

Grid explorado: lookback N en {1, 2, 5, 10, 20}, duración D en {1, 5, 10, 20}
días.

## Modelo de costos

El fixing es mid-point sin bid/ask ejecutable. Cada entrada paga un spread
relativo `s` sobre el precio de entrada; un movimiento direccional solo cuenta
como acierto neto si supera `s`. Escenarios de spread: `0` (sin fricción, cota
superior teórica), `0.0001` (~1 pip, referencia EURUSD), `0.001` (fricción alta,
conservador).

## Métrica objetivo

Hit rate direccional neto de fricción, agregado por walk-forward (folds no
solapados), con intervalo bootstrap por bloques. El nivel de confianza del
intervalo se ajusta por Bonferroni para el número de configuraciones probadas
(`confidence = 1 − alpha/n_tests`), de modo que un barrido amplio no infle la
tasa de falsos descubrimientos.

## Criterio de decisión (edge)

Una configuración se considera "con señal" solo si el límite inferior del
intervalo bootstrap ajustado por Bonferroni supera estrictamente `0.50` con
fricción aplicada. Es una heurística direccional, NO una métrica de rentabilidad:
no implica P/L positivo ni habilita operar dinero real.

## Regla del holdout

El holdout final permanece sellado (se registran solo su hash y su conteo de
ticks). Se abre una única vez, después de:

1. congelar un `StrategyRelease` (estrategia + features + política de riesgo con
   hash), y
2. que la configuración supere el criterio de edge en los folds de walk-forward.

Abrirlo antes o reutilizarlo invalida la inferencia.

## Invariantes que permanecen

- `promotion_eligibility = NOT_ELIGIBLE` hasta que exista evidencia fuera de
  muestra que supere el criterio.
- `profitability_claim = False` en todo reporte.
- `real_money = EXCLUDED` por construcción.
- Ninguna configuración sin edge se promociona ni se opera.

## Resultado (2026-11-04)

El barrido sobre EURUSD, EURJPY, EURGBP y EURCHF (480 configuraciones) no
encontró señal en EURUSD ni EURJPY. EURGBP concentra una señal preliminar de
mean-reversion de medio plazo (lookback 10, duración 5), estable entre folds y
robusta al seed, que sobrevive 1 pip pero no 10 pips de fricción. Ver
[edge-search-results.md](edge-search-results.md): es preliminar, NO promocionable
y NO operable en esta etapa, por depender de un fixing mid-point no ejecutable.

## Confirmación independiente (2026-11-04)

La hipótesis EURGBP mean-reversion L=10/D=5 fue preregistrada y probada una sola
vez en la Reserva Federal H.10, sin repetir el grid. Con 1 pip obtuvo hit 0.5475
e intervalo bootstrap 95 % [0.5161, 0.5822], con los cinco folds sobre 0.50.
Confirma hasta 2 pips, pero no a 5 pips. Ver
[fed-h10-confirmation-results.md](fed-h10-confirmation-results.md).

El holdout permanece sellado. Antes de congelar el `StrategyRelease` y abrirlo,
se exige economía ejecutable del producto elegido. Como fija
[ADR-009](../adr/ADR-009-eurgbp-execution-economics.md), una opción Deriv CALL/PUT
usa `ask_price`, `payout`, barrera y expiración (no rollover spot); un producto
spot/CFD sí requiere spread, slippage, comisión y rollover/swap para cinco días.
Ninguna ruta está aún habilitada para promoción. La replicación es señal
direccional, no evidencia de rentabilidad.
