# Informe de hallazgos — Fuentes históricas y algoritmo de índices sintéticos de Deriv

Fecha de investigación: 2026-11-23 · Investigación solo de web pública (sin contacto con Deriv, sin API de Deriv).

## A) Fuentes históricas AUTORIZADAS/licenciadas (ticks / OHLC)

**Conclusión de la sección: NO existe ninguna fuente histórica autorizada/licenciada de terceros.**
**NO_PROVIDER_APPROVED.**

Evidencia verificada:

1. Los índices sintéticos son **propiedad de Deriv y se generan internamente** (no cotizan en ningún exchange, no tienen subyacente de mercado real). Deriv los describe oficialmente como:
   - "Deriv's **proprietary** derived indices that simulate continuous market movement at predefined volatility levels" — https://deriv.com/derived-indices/volatility-indices
   - "**proprietary synthetic markets** … operate on a tick-based probability model" — https://deriv.com/derived-indices/crash-boom-indices
   - "Derived Indices are **proprietary markets** by Deriv … simulated markets with **programmed price behaviour**" — https://deriv.com/derived-indices

   Al ser series generadas por un algoritmo privado de Deriv y no datos de un mercado real, **ningún proveedor externo de datos (Bloomberg, Refinitiv, Dukascopy, etc.) puede licenciarlas o redistribuirlas**. No se encontró ningún vendor licenciado.

2. La **única fuente oficial de datos es la API WebSocket de Deriv**, y solo expone histórico acotado:
   - Endpoint `ticks_history` (histórico de ticks o velas OHLC): https://developers.deriv.com/docs/data/ticks-history/
   - Esquema oficial (repo de los docs: https://github.com/deriv-com/deriv-api-docs, `config/v3/ticks_history/send.json`):
     - `count` = "An upper limit on ticks to receive" (límite superior; default 1000).
     - `start` = "For style ticks: this will default to **1 day ago**" (lookback por defecto de 1 día).
     - `style` = `ticks` (precio/epoch) o `candles` (OHLC) con `granularity` de 60 s a 86400 s.
     - `adjust_start_time` = "…or **license limit** is before end time, adjust interval backwards" → la API está sujeta a un límite de licencia de lookback, no a un histórico ilimitado.
   - Nota de migración: el `count` por defecto bajó de 5000 (legacy) a 1000 (nueva API) — https://developers.deriv.com/comparison/ticks-history/
   - **No existe** ningún endpoint de exportación masiva / descarga de histórico completo para índices sintéticos.

3. Conclusión operativa para el proyecto: no hay forma legal de "retener" un histórico largo de ticks/OHLC de índices sintéticos; lo único que Deriv entrega es el lookback acotado de su API, que además está sujeto a las restricciones del proyecto (EPHEMERAL_ONLY). No se identificó ningún proveedor aprobado.

## B) Documentación oficial / papers sobre el algoritmo de generación

**Conclusión de la sección: NO existe documentación pública (ni papers) con detalle suficiente para reproducir el generador de forma determinística.** La semilla y el RNG concreto no se publican.

Evidencia verificada (todo lo que Deriv publica es de alto nivel, sin seed/PRNG/parámetros):

1. Volatility Indices: "generate price movement using **secure algorithms**", "maintain a constant level of volatility (Volatility 10, 50, 100…)". https://deriv.com/derived-indices/volatility-indices
2. Crash/Boom: "**tick-based probability model**, each index has a defined average number of ticks between spikes (150, 300, 600, 1000)". https://deriv.com/derived-indices/crash-boom-indices
3. Step Indices: "**fixed step sizes with balanced probabilities**", "**purely mathematical rules**", Skew Step = "directional bias (80–90 % small moves one way, 10–20 % large counter-moves)". https://deriv.com/derived-indices/step-indices
4. Derived Indices (general): "simulated markets with **programmed price behaviour**". https://deriv.com/derived-indices

Ninguno de estos documentos revela la semilla (seed), el generador de números pseudoaleatorios, ni los parámetros exactos necesarios para regenerar la misma secuencia de precios. No se localizó ningún paper académico o documento técnico que reproduzca el generador de Deriv; cualquier "paper" existente analiza propiedades estadísticas de la serie observada, no el algoritmo (cuya semilla es secreta y no publicada).

## C) Conclusión

1. **¿Existe una fuente histórica licenciada usable?** No. **NO_PROVIDER_APPROVED.** Los índices sintéticos de Deriv son series propietarias generadas internamente; no hay vendor de datos de terceros, y la única fuente (API de Deriv) entrega solo lookback acotado (count limitado / por defecto 1 día), sin endpoint de histórico completo descargable. Esto es incompatible con retener un histórico persistente para backtesting sin persistencia.

2. **¿Es viable reproducir el generador con documentación pública?** No de forma determinística. Deriv publica solo descripciones de alto nivel ("algoritmos seguros", "modelo probabilístico por ticks", "pasos fijos con probabilidades balanceadas") pero no la semilla ni el RNG ni los parámetros exactos. Reproducir la secuencia real de Deriv es, con la información pública disponible, inviable; solo se puede construir un generador sintético propio y distinto (demo-only), que es precisamente lo que permite la restricción EPHEMERAL_ONLY del proyecto.

Recomendación coherente con las restricciones del proyecto: mantener EPHEMERAL_ONLY y, para backtesting, usar **datos sintéticos propios generados localmente** (nunca presentados como datos históricos reales de Deriv), ya que no existe ninguna fuente histórica autorizada que pueda retenerse legalmente.
