# S3 — Factibilidad de mercados y contratos Deriv

**Fecha de corte:** 2026-11-24  
**Alcance:** investigación web pública; sin contactar a Deriv, sin usar su API y sin descargar datasets.  
**Restricciones del proyecto:** Deriv `EPHEMERAL_ONLY` (memoria, TTL estricto `<24 h`), dinero real excluido. Este documento no propone implementación ni modifica/optimiza S2.

## 1. Conclusión ejecutiva

Las seis etiquetas no están al mismo nivel conceptual:

- **Range Break** y **Crash/Boom** son **familias de índices subyacentes sintéticos**. No tienen una regla única de liquidación ni una economía contractual propia. Sobre esos índices pueden ofrecerse opciones o CFDs; el contrato superpuesto determina entrada, salida, liquidación y P/L.
- **Rise/Fall**, **Accumulators**, **Digit Over/Under** y **Digit Matches/Differs** son **familias de contratos de opciones** sobre un `underlying_symbol`.

Esta distinción es decisiva: predecir un spike de Crash/Boom o un break de Range Break no demuestra rentabilidad. Para evaluarla habría que fijar además el contrato exacto y observar, en el instante de decisión, su `ask_price`, `payout`, condiciones, disponibilidad y liquidación. Los ticks por sí solos solo permiten estudiar el comportamiento del subyacente o construir un proxy **no económico**.

**Recomendación preliminar de factibilidad:**

1. **Prioridad para una prueba científica intrasesión:** Digit Matches/Differs, seguido de Digit Over/Under. Tienen etiquetas inequívocas, horizonte corto y baselines de resultado explícitos. Solo son candidatos a medir dependencia estadística hasta observar propuestas; no hay presunción de rentabilidad.
2. **Segundo nivel:** Rise/Fall, con una duración única y semántica de igualdad fijada de antemano. Es simple, pero ofrece menos eventos independientes por unidad de tiempo y el baseline no debe suponerse 50/50.
3. **Tercer nivel:** Accumulators. Su liquidación es observable, pero es path-dependent, el rango cambia tick a tick, el growth rate modifica simultáneamente recompensa y probabilidad de knockout, y una prueba económica requiere cotización de entrada y de salida contemporáneas.
4. **No evaluar Range Break o Crash/Boom como “contratos”.** Solo serían candidatos después de especificar una opción concreta superpuesta. Range Break merece una línea descriptiva aparte porque Deriv afirma que su estructura de soporte/resistencia sí puede hacer útil el análisis de canal; esto no constituye evidencia de edge ni de rentabilidad.
5. Con `EPHEMERAL_ONLY`, ninguna familia puede producir evidencia longitudinal reproducible. Una sesión puede rechazar una hipótesis o quedar en `INSUFFICIENT_EVIDENCE`; no puede convertir resultados intradía en una afirmación histórica de rentabilidad.

## 2. Fuentes, precedencia y grado de certeza

### Fuentes oficiales actuales principales

- Índices sintéticos y separación CFD/opciones: <https://deriv.com/markets/derived-indices/synthetic-indices>
- Crash/Boom: <https://deriv.com/derived-indices/crash-boom-indices>
- Digital Options: <https://deriv.com/trade/options/digital-options>
- Accumulator Options: <https://deriv.com/trade/options/accumulator-options>
- Riesgos de opciones (versión `R26|03`, actualizada 2026-09-10): <https://deriv.com/terms-and-conditions/risk-disclosure>
- Tipos de contrato vigentes en la API: <https://developers.deriv.com/llms/contract-types.md>
- Propuestas y sus campos económicos: <https://developers.deriv.com/llms/proposal.md>
- Estado/liquidación del contrato: <https://developers.deriv.com/llms/proposal-open-contract.md>
- Descubrimiento dinámico de contratos: <https://developers.deriv.com/llms/contracts-for.md>
- Símbolos subyacentes activos: <https://developers.deriv.com/llms/active-symbols.md>
- Histórico de ticks: <https://developers.deriv.com/llms/ticks-history.md>
- Términos para usuarios de API (versión `R26|03`, actualizada 2026-10-16): <https://deriv.com/terms-and-conditions/api-users>

### Guías oficiales legacy usadas solo para semántica detallada

- Rise/Fall: <https://legacy-docs.deriv.com/docs/risefall>
- Digit Matches/Differs: <https://legacy-docs.deriv.com/docs/digit-matchesdiffers>
- Digit Over/Under: <https://legacy-docs.deriv.com/docs/digit-overunder>
- Accumulator Options: <https://legacy-docs.deriv.com/docs/accumulator-options>
- Índice de Digital Options: <https://legacy-docs.deriv.com/docs/digital-options>

Estas páginas se identifican explícitamente como **legacy**. Sus códigos (`CALL`, `PUT`, `CALLE`, `PUTE`, `DIGITMATCH`, `DIGITDIFF`, `DIGITOVER`, `DIGITUNDER`, `ACCU`) coinciden con la enumeración del schema actual, pero no sustituyen `contracts_for`. Se usan para reglas de resultado que la página comercial actual resume con menos detalle.

### Incertidumbres transversales

- La oferta puede variar por país, entidad, cuenta, plataforma y dispositivo. La página actual de Digital Options muestra Rise/Fall, Higher/Lower y Touch/No Touch, mientras que el schema actual aún enumera los contratos de dígitos. Por tanto, **existencia en el schema no prueba disponibilidad para una cuenta/símbolo concretos**.
- Sin llamar a `active_symbols`, `contracts_for` y `proposal` —fuera del alcance de este informe— no se verificaron símbolos, duraciones, barreras, stakes, growth rates ni disponibilidad efectiva el 2026-11-24.
- La documentación pública no revela seed, PRNG ni parámetros completos del generador. No es posible reproducir determinísticamente los índices sintéticos de Deriv.
- “Promedio de N ticks” o “promedio de N boundary hits” no implica periodicidad ni una distribución concreta.

## 3. Marco común: resultado estadístico versus economía

Para cualquier opción digital comprada a precio `A = ask_price` y con pago total `P = payout`, si `p` es la probabilidad real de ganar y una pérdida paga cero, el valor esperado al vencimiento es:

```text
EV = p × P − A
punto de equilibrio = A / P
```

La API documenta `ask_price`, `payout`, `spot`, `spot_time`, `date_start`, `date_expiry`, `longcode` y parámetros de validación en `proposal`. El lifecycle documenta `buy_price`, `bid_price`, `payout`, `profit`, `sell_price`, `status`, `entry_spot`, `exit_spot`, barreras y timestamps en `proposal_open_contract`.

Por tanto:

- **Observable con ticks:** resultado mecánico hipotético, frecuencias, dependencia, duración y path del subyacente.
- **Requerido para una afirmación monetaria:** propuesta contemporánea válida, precio realmente comprado o paper equivalente, payout, parámetros exactos, disponibilidad/rechazo y liquidación o precio de venta.
- **No reconstruible defensiblemente a partir de ticks históricos:** margen implícito de Deriv, propuesta que habría sido ofrecida, payout, límites agregados, suspensión, rechazo, precio de salida anticipada y slippage.
- **Baseline económico obligatorio para todas las familias:** `NO_TRADE` con EV = 0, además del baseline predictivo propio de la familia. Acertar más que un baseline de clasificación no basta si no supera `A/P` y los costes/condiciones observados.

## 4. Análisis por familia

### 4.1 Range Break

**Naturaleza.** Es un **índice subyacente**, no un `contract_type`. Deriv lo describe como un mercado en rango cuyo precio rebota entre límites superior e inferior y ocasionalmente rompe por arriba o abajo para crear un rango nuevo. Las variantes se caracterizan por breaks cada **100 o 200 impactos de frontera en promedio**. Fuente: <https://deriv.com/markets/derived-indices/synthetic-indices>.

**Mecanismo observable.** Serie de ticks generada por Deriv; estado aparente de rango, fronteras estimadas, rebotes, número de impactos y transición a un rango nuevo. Deriv declara que los índices sintéticos se generan con un generador aleatorio criptográficamente seguro y que no dependen de noticias reales.

**Liquidación.** No existe una liquidación “Range Break” única. Un CFD sobre el índice se liquida según su propia posición y precios; una opción se liquida según `contract_type`, duración, barrera y quote elegidos. Debe evitarse convertir “break alto/bajo” en P/L sin especificar el contrato superpuesto.

**Variables observables/requeridas.** Ticks (`epoch`, `quote`, `pip_size`), retornos, extremos locales, fronteras estimadas causalmente, impactos de frontera, dirección y tiempo del break. Para economía: símbolo, contrato, duración/barrera, `ask_price`, `payout`, bid/settlement y disponibilidad.

**Hipótesis falsables.**

- H-RB1: una definición causal y preregistrada de frontera predice la probabilidad de break en los próximos `k` ticks mejor que la frecuencia incondicional del mismo estado.
- H-RB2: la hazard de break depende del número de impactos desde el último cambio de rango.
- H-RB3: la dirección del próximo break contiene información en la asimetría de rebotes recientes.

Cada hipótesis exige una definición previa de “impacto”, “break”, tolerancia por `pip_size`, ventana y reset; no puede identificarse el rango retrospectivamente.

**Baseline.** Modelo de estado sin memoria condicionado solo por la variante 100/200 y la frecuencia empírica estimada en warm-up; para dirección, frecuencia incondicional alta/baja. “Ocurre exactamente al impacto 100/200” es un baseline inválido: Deriv dice promedio.

**Falsos positivos.** Dibujar canales ex post; contar varios ticks cerca del límite como impactos separados; cambiar tolerancias tras ver el break; confundir 100/200 impactos con ticks; ventanas solapadas; transiciones de régimen; múltiples variantes/ventanas/indicadores; seleccionar solo rangos visualmente limpios.

**Economía y viabilidad.** Factibilidad **media para estudiar mecanismo**, **baja como candidato económico autónomo**. Es la única familia para la que Deriv afirma que el análisis de canal e indicadores “may be effective”; en la misma FAQ advierte que los patrones visibles de otros índices sintéticos pueden ser coincidentales. Esa afirmación comercial es una motivación falsable, no evidencia. Sin contrato superpuesto y proposals observadas, el resultado permanece no económico.

**Limitaciones.** Las fronteras no aparecen documentadas como campos del feed; probablemente habría que inferirlas del precio, aumentando error de etiqueta. No se conoce la distribución del tiempo hasta break ni el algoritmo de creación del siguiente rango.

### 4.2 Crash/Boom

**Naturaleza.** Familia de **índices subyacentes sintéticos**, no contrato. Crash produce spikes rápidos bajistas con drift alcista entre ellos; Boom, spikes alcistas con drift bajista. Deriv publica intervalos medios entre spikes, por ejemplo 150, 300, 600 o 1000 ticks, mediante un “tick-based probability model”. Fuente: <https://deriv.com/derived-indices/crash-boom-indices>.

**Mecanismo observable.** Ticks, drift, retornos, magnitud/dirección de spikes e intervalos entre spikes. Los números del nombre significan promedio, no cuenta regresiva. La página oficial también indica que los números mayores suelen asociarse con spikes menos frecuentes y típicamente mayores.

**Liquidación.** No hay liquidación Crash/Boom única. Deriv ofrece estos índices mediante CFDs y opciones; cada producto tiene lifecycle y economía propios. Un spike correctamente anticipado puede no producir beneficio si el contrato, duración, barrera o payout no lo monetizan.

**Variables observables/requeridas.** Retornos por tick, definición causal de spike, tiempo desde último spike, drift entre spikes, volatilidad local, variante N. Para economía: producto superpuesto, dirección, duración, `ask_price`, `payout`, bid/settlement, spread/margen o condiciones CFD.

**Hipótesis falsables.**

- H-CB1: la hazard de spike es constante (modelo geométrico/memoryless) frente a una alternativa dependiente del tiempo desde el último spike.
- H-CB2: features exclusivamente anteriores al tick predicen spike dentro de `k` ticks mejor que la tasa base.
- H-CB3: el drift entre spikes contiene persistencia explotable en resultado contractual, no solo correlación de precio.

H-CB1 es una prueba de modelo propia: Deriv publica la media, pero **no afirma** que la distribución sea geométrica.

**Baseline.** Tasa incondicional de spike por variante y modelo memoryless ajustado solo en warm-up; para dirección no aplica dentro de cada familia porque la dirección del spike está programada. Baseline económico: no operar y, si existe contrato definido, política sin features con la misma cadencia/duración.

**Falsos positivos.** Falacia del jugador (“ya toca” tras N ticks); definir spike por umbral elegido ex post; leakage al usar el máximo/mínimo futuro; confundir drift conocido con timing de spike; sobrecontar un spike de varios ticks; ventanas solapadas; probar muchos N, umbrales y horizontes; ignorar payouts que se encarecen cuando una condición es más probable.

**Economía y viabilidad.** Factibilidad **alta para describir estadística intrasesión**, **baja para inferir edge económico**. El generador es propietario y Deriv advierte, en la FAQ general de sintéticos, que fuera de Range Break los patrones históricos visibles pueden ser coincidencia. La frecuencia media publicada no crea por sí misma capacidad predictiva.

**Limitaciones.** No hay especificación pública de distribución, magnitud, seed o PRNG. Una sesión `<24 h` puede contener pocos spikes efectivos, sobre todo en variantes de alta media, y su tamaño muestral efectivo es muy inferior al número de ticks.

### 4.3 Rise/Fall

**Naturaleza y mecanismo.** Contratos digitales `CALL` (Rise) y `PUT` (Fall); variantes con igualdad `CALLE` y `PUTE`. Se compara spot de salida con spot de entrada al final del contrato. Fuentes: <https://legacy-docs.deriv.com/docs/risefall> y enum actual <https://developers.deriv.com/llms/contract-types.md>.

**Regla de liquidación.** Rise gana si `exit_spot > entry_spot`; Fall si `exit_spot < entry_spot`. Con “Allow equals”, Rise gana con `>=` y Fall con `<=`. La página actual resume que la predicción se evalúa al final del contrato: <https://deriv.com/trade/options/digital-options>. La divulgación de riesgo clasifica Digital Options como all-or-nothing y señala pérdida del 100% de la stake/premium si la condición falla: <https://deriv.com/terms-and-conditions/risk-disclosure> §4.2.

**Variables observables/requeridas.** Entrada/salida, duración o expiry, unidad (ticks/segundos/etc.), semántica strict/equal, retornos y features causales previas. Economía: `ask_price`, `payout`, quote timestamp, parámetros exactos, compra/settlement y posible venta anticipada.

**Hipótesis falsables.**

- H-RF1: la probabilidad condicional de Rise a una duración fija difiere de su tasa incondicional de warm-up.
- H-RF2: una feature preregistrada mejora el log-loss/Brier score OOS respecto del pronóstico constante.
- H-RF3: la política supera el umbral económico `ask_price/payout` en proposals observadas, con intervalo apropiado para dependencia temporal.

**Baseline.** Pronóstico constante con tasa Rise/Fall/tie del warm-up, y política aleatoria con la misma cadencia. No imponer 50/50: drift, ties, precisión y duración pueden romper esa simetría. La variante strict y “allow equals” son experimentos distintos.

**Falsos positivos.** Alinear señal con el tick anterior; solapar horizontes; omitir ties; elegir duración/símbolo tras observar resultados; probar CALL y PUT como tests independientes sin corrección; usar precio final de una vela distinto del tick contractual; confundir exactitud direccional con EV positivo.

**Economía y viabilidad.** **Alta mecánicamente, media experimentalmente.** Es simple de etiquetar y auditar. Sin proposals contemporáneas es solo `TICK_PROXY`, no evidencia monetaria. La disponibilidad exacta debe descubrirse dinámicamente.

**Limitaciones.** Menos decisiones independientes que en contratos de un tick si se evita solapamiento; tiempos de tick irregulares; `exit_spot_time` puede preceder ligeramente a expiry en instrumentos que no tickean cada segundo, según `proposal_open_contract`.

### 4.4 Accumulators

**Naturaleza y mecanismo.** Contrato `ACCU`, path-dependent. Se elige growth rate de 1%, 2%, 3%, 4% o 5%. El payout crece de forma compuesta por cada tick consecutivo cuyo spot permanece dentro de un rango definido alrededor del spot anterior; tasas mayores implican rango más estrecho. Fuentes: <https://deriv.com/trade/options/accumulator-options>, <https://legacy-docs.deriv.com/docs/accumulator-options> y <https://developers.deriv.com/llms/proposal.md>.

**Regla de liquidación.** Si el precio **toca o cruza** cualquiera de los límites (“slip condition”), el contrato termina automáticamente y se pierde la stake y todo payout acumulado no realizado. Puede venderse antes si `is_valid_to_sell == 1`; también puede cerrarse por take-profit, máximo de ticks o máximo payout. La regla de pérdida está explícita en <https://deriv.com/terms-and-conditions/risk-disclosure> §4.3. La API expone `growth_rate`, `barrier_spot_distance`, barreras actuales, `tick_passed`, `max_ticks` y `max_payout`.

**Variables observables/requeridas.** Secuencia tick a tick; spot anterior; high/low barrier vigente; distancia de barrera; growth rate; ticks sobrevividos; toque/cruce; max ticks/payout; precio de venta disponible. Economía: stake/ask de entrada, bid de venta, payout realizado, take-profit, caps y liquidación.

**Hipótesis falsables.**

- H-AC1: la hazard de knockout al próximo tick no es constante y depende de features causales de volatilidad/retorno.
- H-AC2: para un growth rate fijo, una regla de salida preregistrada mejora EV frente a salida fija en tick `n`, usando quotes de venta observadas.
- H-AC3: las duraciones de supervivencia se desvían de un baseline geométrico ajustado en warm-up.

No combinar growth rates en una sola hipótesis: cambian simultáneamente barrera y compounding.

**Baseline.** Curva de supervivencia/hazard incondicional por símbolo y growth rate; salida fija en un tick preregistrado; `NO_TRADE`. Para economía no basta aplicar `(1+g)^n` a la stake: el bid real de salida, knockout, caps y condiciones deben observarse.

**Falsos positivos.** Mostrar solo contratos supervivientes; tratar payout no realizado como beneficio; optional stopping; ignorar knockouts a cero; usar barreras fijas cuando se recalculan desde el spot anterior; mezclar growth rates; censura por cierre de sesión; copiar ejemplos porcentuales de una guía como constantes universales; asumir que compounding implica EV positivo.

**Economía y viabilidad.** **Media.** La mecánica es clara, pero es la familia más exigente en lifecycle y cotizaciones. La divulgación de riesgo actual es autoritativa. Una guía oficial 2026 menciona caps concretos (230 ticks a 5% y USD 10,000), pero estos valores pueden variar y la API ofrece `validation_params`; por tanto, deben tratarse como ejemplos fechados, no constantes.

**Limitaciones.** Producto disponible actualmente solo en Derived Indices según la página comercial; la guía oficial limita la oferta descrita a volatility indices, pero puede cambiar. Disponibilidad temporal puede depender de límites agregados. Path dependence y venta anticipada reducen tamaño efectivo y hacen inadecuado un simple clasificador win/loss.

### 4.5 Digit Over/Under

**Naturaleza y mecanismo.** Contratos digitales `DIGITOVER` y `DIGITUNDER`. Se elige una barrera/dígito `b` de 0 a 9 y se evalúa el último dígito del último tick. Fuente: <https://legacy-docs.deriv.com/docs/digit-overunder>; enum actual: <https://developers.deriv.com/llms/contract-types.md>.

**Regla de liquidación.** Over gana si el último dígito es **estrictamente mayor** que `b`; Under gana si es **estrictamente menor**. La igualdad pierde en ambos casos. Es all-or-nothing bajo la regla general de Digital Options.

**Variables observables/requeridas.** Quote del tick final, `pip_size`/precisión de display que determina el último dígito, barrera, duración y timestamps. Economía: proposal por lado/barrera/duración, `ask_price`, `payout`, buy/settlement y disponibilidad.

**Hipótesis falsables.**

- H-OU1: la distribución marginal de dígitos difiere de uniformidad en una ventana forward preregistrada.
- H-OU2: el dígito siguiente depende de una secuencia pasada fija más allá de la marginal.
- H-OU3: para un único `b` preregistrado, la probabilidad condicional supera `ask_price/payout` OOS.

**Baseline.** Bajo uniformidad exacta de dígitos 0–9: `P(Over b)=(9-b)/10` y `P(Under b)=b/10`. Ejemplos: con `b=4`, Over=50% y Under=40%; la igualdad (10%) pierde. El baseline operativo preferible es la distribución empírica del warm-up, congelada antes del forward.

**Falsos positivos.** Tratar Over/Under como complementos (falta la igualdad); extraer el dígito desde un float binario o con precisión incorrecta; probar nueve barreras, múltiples lags y símbolos sin corrección; solapar señales; sesgo de selección hacia payouts altos/bajos; detectar desviación de uniformidad que ya está completamente incorporada en la quote.

**Economía y viabilidad.** **Alta para etiquetado y muestreo; media para economía.** Tiene más grados de libertad y riesgo de p-hacking que Matches/Differs. La dependencia estadística de dígitos no implica superar la curva de precios por barrera.

**Limitaciones.** Barreras extremas producen una clase imposible en un lado (`Under 0`, `Over 9`) y probablemente no estén ofrecidas; debe prevalecer `contracts_for`. Precisión/pip size forma parte de la definición del outcome.

### 4.6 Digit Matches/Differs

**Naturaleza y mecanismo.** Contratos digitales `DIGITMATCH` y `DIGITDIFF`. Se predice un dígito 0–9 y se compara con el último dígito del último tick. Fuente: <https://legacy-docs.deriv.com/docs/digit-matchesdiffers>; enum actual: <https://developers.deriv.com/llms/contract-types.md>.

**Regla de liquidación.** Match gana si el dígito final coincide exactamente; Differs gana si no coincide. Son resultados complementarios para una predicción fija y una representación de dígito bien definida.

**Variables observables/requeridas.** Dígito predicho, quote final, `pip_size`, duración, secuencia previa y timestamp. Economía: proposal específica para Match/Differs y dígito, ask, payout y settlement.

**Hipótesis falsables.**

- H-MD1: la marginal de los diez dígitos no es uniforme.
- H-MD2: una secuencia pasada preregistrada cambia la probabilidad del próximo dígito frente a la marginal de warm-up.
- H-MD3: una única predicción preregistrada supera el break-even `ask_price/payout` en forward.

**Baseline.** Uniformidad: Match=10% y Differs=90% para un dígito fijado. Baseline más robusto: pronóstico categórico empírico congelado tras warm-up. Para comparar Match con Differs deben usarse las quotes de ambos; 90% de acierto en Differs no es evidencia de edge porque el payout reflejará la alta tasa base.

**Falsos positivos.** Celebrar hit rate de Differs sin payout; elegir el dígito menos/más frecuente después de mirar el forward; diez tests por dígito más múltiples lags; precisión decimal incorrecta; dependencia serial y ventanas solapadas; confundir una desviación minúscula estadísticamente detectable con margen económico.

**Economía y viabilidad.** **La mejor candidata mecánica intrasesión**, por etiquetas simples, frecuencia alta y baseline explícito. Sigue siendo solo un detector de dependencia hasta observar quotes. Dado que Deriv describe sus sintéticos como generados por RNG criptográficamente seguro y advierte sobre patrones coincidentes, la hipótesis nula debe ser fuerte y `NO_EDGE` un resultado esperado y válido.

**Limitaciones.** Gran desbalance de clase en Match/Differs; la precisión estadística útil debe medirse sobre el evento raro y con dependencia temporal. Oferta concreta no confirmada sin descubrimiento dinámico.

## 5. Comparación resumida

| Familia | Capa | Settlement etiquetable con ticks | Economía histórica desde ticks | Muestras intrasesión | Riesgo principal | Factibilidad preliminar |
|---|---|---:|---:|---:|---|---|
| Range Break | Subyacente | Solo evento de break inferido | No; falta contrato/quote | Media | fronteras ex post; 100/200 mal interpretado | Media mecánica / baja económica autónoma |
| Crash/Boom | Subyacente | Spike inferido | No; falta contrato/quote | Baja–media efectiva | falacia del jugador; pocos spikes | Alta descriptiva / baja económica |
| Rise/Fall | Contrato | Sí | No; falta proposal/payout | Media | ties, duración, solapamiento | Alta mecánica / media experimental |
| Accumulators | Contrato path-dependent | Parcial; barreras/lifecycle son claves | No | Media | survivorship, optional stopping, bids | Media |
| Over/Under | Contrato de dígito | Sí | No | Alta | igualdad, precisión, múltiples barreras | Alta mecánica / media económica |
| Matches/Differs | Contrato de dígito | Sí | No | Alta | desbalance, payout, múltiples dígitos | **Mayor prioridad de prueba** |

## 6. Disponibilidad y licencia de datos

La disponibilidad técnica pública no equivale a una licencia de retención:

- `ticks_history` permite solicitar ticks o velas, con `count`, `start`, `end`, `style` y granularidad; no documenta un dataset histórico completo descargable: <https://developers.deriv.com/llms/ticks-history.md>.
- `proposal` ofrece economía actual, no un archivo de proposals históricas: <https://developers.deriv.com/llms/proposal.md>.
- `contracts_for` devuelve contratos y límites **actualmente** disponibles para un símbolo: <https://developers.deriv.com/llms/contracts-for.md>.
- API Users Terms `R26|03` §2.1 prohíbe almacenar contenido, incluido feed data, derivado/originado en el sitio o accedido vía API; §2.3 permite cachearlo hasta 24 horas desde la solicitud; §2.4 exige borrado al terminar la relación: <https://deriv.com/terms-and-conditions/api-users>.

Aplicación a las seis familias:

1. No se identificó fuente externa autorizada de historia para los índices sintéticos propietarios.
2. La única fuente oficial de ticks/proposals es Deriv, bajo el límite de cache.
3. Ticks, proposals, features, labels, decisiones y settlements deben permanecer en memoria y eliminarse antes de `<24 h`, conforme a ADR-012.
4. No se pueden encadenar sesiones para reconstruir historia, ni conservar métricas longitudinales derivadas como si transformar el payload resolviera §2.1.
5. Un experimento intrasesión no puede respaldar un backtest histórico reproducible ni una afirmación de rentabilidad longitudinal.

## 7. Diseño conceptual de evaluación (sin propuesta de implementación)

Para que cualquier resultado sea interpretable, cada hipótesis deberá congelar antes del forward:

- familia y si es subyacente o contrato;
- `underlying_symbol` y `contract_type` exactos;
- duración, barrera/dígito, growth rate y semántica de igualdad;
- unidad experimental no solapada o corrección explícita por solapamiento;
- warm-up y forward dentro de una sola sesión;
- una hipótesis primaria y corrección de múltiples tests;
- baseline predictivo y baseline económico `NO_TRADE`;
- métrica de probabilidad/calibración, no solo accuracy;
- fuente económica `UNAVAILABLE` (ticks) u `OBSERVED` (proposal/lifecycle contemporáneos);
- conclusión limitada a `NO_EDGE`, `INSUFFICIENT_EVIDENCE` o elegibilidad paper intrasesión.

No debe abrirse una inferencia económica si faltan `ask_price`, `payout`, disponibilidad y settlement/bid observados. Una dependencia estadística real pero ya reflejada por Deriv en la quote tiene EV no positivo para el comprador.

## 8. Recomendación final preliminar

> **Reconciliación (autoritativa: [`s3-decision-matrix.md`](s3-decision-matrix.md)).** Esta sección prioriza la factibilidad de *medición intrasesión* con economía observable (contratos de dígito). La matriz de decisión, aplicando además el criterio de independencia estricta respecto de S2, promueve como hipótesis primaria de descubrimiento estadístico **Range Break** (`RANGE_BREAK_BOUNDARY_HAZARD_V1`), condicionada a potencia ≥80%. El contrato de dígito Matches/Differs queda como alternativa honesta de segundo plano. Para la recomendación única, remitirse a la matriz.

- **Seleccionar primero Digit Matches/Differs solo como prueba de factibilidad científica intrasesión**, con un único símbolo, dígito, duración e hipótesis preregistrados. Razón: settlement inequívoco, baseline explícito y mayor cantidad de outcomes. La meta no es “encontrar una estrategia”, sino comprobar si puede medirse una desviación forward sin leakage y, separadamente, si la economía contemporánea es observable.
- **Usar Digit Over/Under como contraste**, no como grid de nueve barreras. Su igualdad perdedora y la curva de tasas base ofrecen un buen control de calidad, pero multiplican oportunidades de selección.
- **Mantener Rise/Fall como alternativa simple** si los contratos de dígitos no están disponibles para la cuenta/símbolo. Congelar strict versus allow-equals.
- **Posponer Accumulators** hasta que el objetivo sea estudiar hazard/salida con lifecycle completo; el tick outcome aislado es insuficiente.
- **Tratar Range Break y Crash/Boom exclusivamente como universos subyacentes.** Antes de evaluarlos económicamente hay que elegir una familia contractual superpuesta. No recomendar Crash/Boom por su frecuencia media publicada; eso invita a la falacia del jugador. Range Break sí justifica una hipótesis de canal falsable, pero no una recomendación económica.
- **No promover ninguna familia por esta revisión.** La documentación establece mecanismo y observabilidad, no edge. Bajo `EPHEMERAL_ONLY`, la recomendación máxima es una comparación paper intrasesión y honesta; dinero real continúa bloqueado.
