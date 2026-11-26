# S2 — Informe formal de cierre

Fecha de cierre: 2026-11-24
Estado terminal: `NO_EDGE`

## 1. Decisión

S2 queda formalmente cerrada. Ninguna de las dos familias evaluadas —Even/Odd y Multipliers— demostró una ventaja estadística estable, causal y económicamente interpretable suficiente para promoción.

Consecuencias obligatorias:

- `promotion_eligibility = NOT_ELIGIBLE`;
- `paper_trading = BLOCKED` para las estrategias S2;
- `real_money = EXCLUDED` por construcción;
- `profitability_claim = false`;
- las semillas 61–80 permanecen selladas y no se generarán;
- no se reoptimizarán retrospectivamente features, target, stop, horizonte, filtros o semillas;
- los artefactos S2 se preservan como evidencia negativa y no se sustituyen por S3.

## 2. Evidencia cerrada

### 2.1 Even/Odd

Fuente normativa: [`s2-even-odd-synthetic-validation.md`](s2-even-odd-synthetic-validation.md).

- Evidencia: `OWNED_SYNTHETIC_TICK_PROXY`.
- Semillas observadas: 1–20.
- Dígito uniforme: Brier estrategia 0.2617458333 frente a 0.25; mejor en 8/20 semillas.
- Paridad Markov 0.9: Brier estrategia 0.2648333333 frente a 0.25; mejor en 8/20 semillas.
- El hit rate condicionado de 68.84% en Markov no compensó la peor calibración global.
- Holdout abierto: no.
- Resultado del bloque: `NO_SYNTHETIC_CALIBRATION_ADVANTAGE`.

### 2.2 Multipliers — exploración

Fuente normativa: [`s2-multiplier-synthetic-validation.md`](s2-multiplier-synthetic-validation.md).

- Evidencia: movimiento sintético del quote, sin economía contractual observada.
- Semillas exploratorias: 1–20.
- Ornstein–Uhlenbeck produjo una mejora parcial e inestable.
- Random walk y GBM no respaldaron una ventaja generalizable.
- Regímenes de volatilidad mostraron fragilidad y peor calibración agregada.
- Resultado exploratorio: `INSUFFICIENT_SYNTHETIC_STABILITY`.

### 2.3 Multipliers — robustez preregistrada

Fuentes normativas:

- [`s2-multiplier-robustness-protocol.md`](s2-multiplier-robustness-protocol.md);
- [`s2-multiplier-robustness-results.md`](s2-multiplier-robustness-results.md).

- Semillas de desarrollo ejecutadas: 21–60.
- Semillas reservadas 61–80: no generadas.
- OU: delta Brier medio -0.0099225150, IC bootstrap 95% [-0.0161337633, -0.0035434795], pero 26/40 wins frente al mínimo preregistrado de 28.
- Solo 2/4 procesos tuvieron delta Brier no positivo.
- GBM presentó degradación consistente frente al baseline.
- Resultado automático: `NO_EDGE`.

## 3. Límites de la evidencia

1. Los procesos DevSoul son modelos propios, no reproducciones de los índices de Deriv.
2. No existe histórico persistible aprobado de índices sintéticos Deriv.
3. No se modeló economía contractual observada de Multipliers: ask, payout, multiplicador efectivo, comisión, latencia, rechazo y settlement del proveedor.
4. Por lo anterior, S2 no produce ROI, P/L, profit factor, expected value monetario ni una afirmación sobre rentabilidad en Deriv.
5. Las sesiones Deriv fueron efímeras y no pueden agregarse longitudinalmente.

## 4. Preservación y no reutilización

Los siguientes elementos quedan congelados como evidencia histórica:

- protocolos;
- configuraciones;
- semillas observadas;
- reportes;
- resultados negativos;
- pruebas automatizadas;
- código de validación y robustez.

S3 puede reutilizar infraestructura neutral —replay, splits, scoring, riesgo, ledger, provenance y gates—, pero no puede:

- presentar una variante Even/Odd o Multipliers como hipótesis independiente;
- seleccionar retrospectivamente horizonte 3 u otra celda favorable;
- reutilizar las semillas 61–80 para otra finalidad;
- promover las estrategias S2 a paper o demo autónoma;
- reinterpretar dependencia sintética como edge económico.

## 5. Transición a S3

S3 comienza como una evaluación de factibilidad y descubrimiento estadístico previa a cualquier nueva estrategia. La secuencia autorizada es:

1. verificar derechos de datos;
2. documentar mecanismo y settlement del producto;
3. definir hipótesis estadísticas falsables;
4. identificar economía observable;
5. controlar comparaciones múltiples y potencia;
6. construir una matriz de decisión;
7. recomendar una sola hipótesis;
8. esperar aprobación antes de experimentos confirmatorios.

Esta transición no reabre S2 ni sus holdouts.

## 6. Impacto operativo y costos

- Cambios en estrategias o modelos: ninguno.
- Operaciones paper habilitadas: ninguna.
- Operaciones con dinero real: ninguna.
- Datos Deriv persistidos: ninguno.
- Recursos GCP creados o modificados: ninguno.
- Costo GCP incremental: USD 0.
