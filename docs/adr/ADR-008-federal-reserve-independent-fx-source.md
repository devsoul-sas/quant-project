# ADR-008: Reserva Federal H.10 como segunda fuente independiente (FX diario)

- Estado: aceptada
- Fecha: 2026-11-04
- Congela: [ADR-007](ADR-007-ecb-daily-fx-source.md)

## Contexto

El barrido de edge sobre el BCE encontró una señal preliminar de mean-reversion en EURGBP
(lookback 10, duración 5), estable entre folds y robusta al seed, que sobrevive 1 pip pero no
10 pips de fricción ([edge-search-results.md](../research/edge-search-results.md)). El caveat
principal es que el fixing del BCE es un único fixing mid-point no ejecutable: la señal podría
ser un artefacto de ese fixing concreto (redondeo, convención, hora de concertación). Para
descartarlo se necesita una fuente independiente.

## Decisión

Adoptar el H.10 de la Junta de Gobernadores de la Reserva Federal (noon buying rates diarios
contra el USD, dominio público) como segunda fuente independiente para la validación cruzada de
la señal FX diaria. Ver [provider-evaluation-federal-reserve.md](../data/provider-evaluation-federal-reserve.md).

## Consecuencias

- La serie EURGBP se puede reconstruir de forma independiente desde USD/GBP y USD/EUR del fixing
  de Nueva York, sin depender del fixing del BCE.
- Si la señal de mean-reversion persiste en el H.10, gana credibilidad fuera del fixing original;
  si desaparece, el hallazgo del BCE se descarta como artefacto de fixing.
- El Bank of England (OGL v3.0 con exclusión de "selected exchange rate data") queda registrado
  como opción de tercer fixing, no como dependencia
  ([provider-evaluation-bank-of-england.md](../data/provider-evaluation-bank-of-england.md)).
- Ningún fixing diario es precio ejecutable: se mantiene el modelado de costos de ejecución.

## Condición de cambio

Solo una re-verificación de los términos del Fed o un cambio de alcance (intradía/ticks) reabre
esta decisión. El dominio público del Fed es estable por ley (17 U.S.C. § 105), pero el aviso del
sitio no está versionado y debe re-consultarse periódicamente.
