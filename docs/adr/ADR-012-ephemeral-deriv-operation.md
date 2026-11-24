# ADR-012 — Operación Deriv estrictamente efímera

- Estado: aceptada
- Fecha: 2026-11-23

## Contexto

Los API Users Terms de Deriv permiten una caché máxima de 24 horas. El proyecto no necesita construir un histórico Deriv para operar una sesión: necesita conservar temporalmente ticks, propuestas, features y decisiones mientras la sesión está activa, y eliminarlos al cerrarla.

Se descarta continuar enviando solicitudes para ampliar derechos de retención. En consecuencia, no se intentará convertir las sesiones efímeras en un corpus longitudinal ni se afirmará que una transformación de los ticks queda fuera de las restricciones contractuales.

## Decisión

1. Deriv permanece `EPHEMERAL_ONLY` con TTL estricto menor de 24 horas.
2. Ticks, propuestas, features, modelos de sesión, decisiones y settlements permanecen solo en memoria.
3. Cada sesión comienza sin estado de mercado o estrategia heredado.
4. Ninguna sesión aprende de una sesión anterior.
5. Al cerrar, expirar o fallar una sesión se eliminan todas las referencias a datos y derivados Deriv.
6. No se escriben CSV, Parquet, PostgreSQL, checkpoints, métricas longitudinales ni reportes con contenido Deriv.
7. No se reconstruye historia encadenando ventanas efímeras.
8. Para este alcance, no se enviarán nuevas solicitudes de permiso a Deriv.

## Estrategia operativa

Cada sesión debe completar dentro de su propio TTL:

1. descubrimiento de símbolos y contratos;
2. warm-up causal;
3. estimación de economía contemporánea;
4. validación forward intrasesión;
5. decisiones paper o demo acotadas;
6. settlement y controles de riesgo;
7. zeroización.

Una mayor frecuencia de ticks no sustituye diversidad temporal ni evidencia longitudinal. Por ello, una sesión puede rechazar una hipótesis o declararla insuficiente, pero no puede fabricar una afirmación histórica de rentabilidad.

## Conclusiones científicas permitidas

El laboratorio solo puede emitir durante la sesión:

- `NO_EDGE`;
- `INSUFFICIENT_EVIDENCE`;
- `PAPER_ELIGIBLE`.

`PAPER_ELIGIBLE` significa que la política puede continuar en simulación paper dentro de esa misma sesión. No autoriza dinero real ni se conserva como promoción entre sesiones.

## Dinero real

Para el release actual:

```text
profitability_claim = False
promotion_eligibility = NOT_ELIGIBLE
real_money = EXCLUDED
```

Una futura ruta real requerirá una decisión de arquitectura y autorización humana separadas. No se añade un endpoint real, un modo `REAL` ni un adaptador real como parte de esta ADR.

## Consecuencias

- Se puede construir un runner automático paper/demo completamente efímero.
- El sistema debe recalentar y revalidar desde cero en cada sesión.
- `NO_TRADE` es correcto durante horas o durante toda la sesión.
- No puede usarse desempeño de sesiones pasadas para ajustar parámetros, stake o selección de mercado.
- Los resultados demo sirven para verificar integración y controles, no para demostrar edge longitudinal.
