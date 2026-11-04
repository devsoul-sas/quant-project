# ADR-007 — Fuente histórica permisiva: BCE euro FX (frecuencia diaria)

- Estado: aceptada
- Fecha: 2026-11-04

## Contexto

La shortlist de proveedores concluyó `NO_PROVIDER_APPROVED`: Dukascopy, Binance y
Alpha Vantage quedaron rechazados por términos no comerciales o que prohíben construir
bases de datos, y Twelve Data quedó condicional bloqueado a la espera de una licencia
escrita de pago. Para la vía de opciones binarias por ticks no existe fuente permisiva.

La política de copyright del Banco Central Europeo, verificada en su fuente oficial el
2026-11-04, concede "free use of the information obtained directly" con tres condiciones:
citar al BCE como fuente, informar la disponibilidad gratuita si el dato se vende dentro
de un documento y declarar las modificaciones. Es la primera fuente que permite
almacenamiento, derivados y uso comercial sin contrato escrito.

## Decisión

Adoptar las euro foreign exchange reference rates del BCE como primera fuente histórica
aprobada, pero solo para una estrategia FX de frecuencia diaria:

- nuevo `DataSourceKind.OPEN_LICENSE` (licencia pública permisiva, sin autorización escrita);
- nuevo `EvidenceMode.QUOTE_REPLAY_BACKTEST` que exige economía `OBSERVED`;
- adapter de ingesta del CSV oficial (`eurofxref-hist`) con provenance `OBSERVED`;
- backtest diario con walk-forward y holdout sellado.

La vía de ticks/opciones permanece `NO_PROVIDER_APPROVED`.

## Alternativas consideradas

1. Twelve Data de pago: mejor cobertura intradía, pero exige licencia escrita, costo y
   contrato con la identidad contractual correcta; se pospone como opción futura.
2. Datasets cripto CC0: procedencia débil (reempaques de exchanges con términos
   restrictivos); riesgo legal equivalente al de los proveedores rechazados.
3. Seguir solo sintético: no produce evidencia económica real.
4. BCE FX diario: gratis, oficial, reproducible desde 1999, licencia permisiva.
   **Seleccionada**, con la salvedad de granularidad diaria y costos modelados.

## Consecuencias

- El backtest real corre sobre datos observados (7129 ticks EURUSD, 1999–2026) y produce
  evidencia `QUOTE_REPLAY_BACKTEST`. El primer resultado no muestra ventaja direccional
  (hit rate ~47 %, bootstrap incluye 0.50), como corresponde sin edge.
- `promotion_eligibility` sigue `NOT_ELIGIBLE`: la promoción exige criterios fuera de
  muestra y de holdout que aún no se establecen.
- El dinero real permanece excluido; Deriv sigue siendo solo broker al final de la cadena.
- Twelve Data queda registrado como opción futura de pago, no como camino actual.
