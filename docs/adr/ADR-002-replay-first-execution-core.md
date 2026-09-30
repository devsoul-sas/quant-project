# ADR-002 — Núcleo replay-first y determinista

- Estado: aceptada para MVP
- Fecha: 2026-09-29

## Contexto

Construir motores distintos para backtest y tiempo real produce divergencias difíciles de detectar. El MVP necesita explicar por qué una señal histórica, paper o demo ocurrió.

## Decisión

El mismo núcleo de features, estrategia y riesgo procesará una secuencia ordenada de eventos tanto en replay como en tiempo real.

Componentes obligatorios:

- `Clock` inyectable: UTC para instantes y monotónico para duraciones;
- orden total definido para eventos con el mismo timestamp;
- features incrementales con lookback y warm-up explícitos;
- `StrategyIntent` provider-agnostic;
- `RiskDecision` separada de la estrategia;
- `BrokerPort` implementado por paper y Deriv demo;
- IDs de correlación y causalidad;
- Decimal para dinero/contabilidad;
- hashes/versiones de datasets, features, estrategias, modelos y configuración.

## Invariantes

1. Cambiar datos posteriores al decision time no altera decisiones pasadas.
2. Mismo snapshot, código, configuración y semilla produce mismas decisiones y métricas normalizadas.
3. La estrategia nunca llama directamente al broker.
4. Riesgo puede rechazar cualquier intención, aun con alta confianza.
5. Los eventos cerrados no se actualizan ni eliminan; las correcciones son eventos nuevos.
6. Reiniciar obliga a reconciliar posiciones antes de aceptar nuevas entradas.

## Consecuencias

El diseño inicial requiere reloj, eventos y fixtures antes que modelos, pero reduce el riesgo de que el backtest describa un sistema diferente al ejecutado.