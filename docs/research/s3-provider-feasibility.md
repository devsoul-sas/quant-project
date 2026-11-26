# Evaluación de fuentes alternativas de datos — viabilidad de persistencia (S3)

- Fecha de investigación y acceso a fuentes: **2026-11-24**
- Alcance: fuentes con autorización verificable para (1) persistencia/almacenamiento,
  (2) investigación cuantitativa reproducible, (3) explotación comercial eventual
  (derivados/features, presentación, redistribución).
- Regla de decisión: **lo no autorizado explícitamente se considera bloqueante.**
  `Unspecified ≠ allowed`.
- Naturaleza del documento: investigación técnica de derechos, **no** asesoría jurídica.
  No se descargaron datos de mercado, no se contactó a proveedores, no se abrieron
  cuentas ni credenciales.

Este documento complementa y no reemplaza las evaluaciones previas en
`docs/data/` (ECB, Federal Reserve, Bank of England, Dukascopy, Binance,
Alpha Vantage, Twelve Data, Darwinex). Los rechazos previos se mantienen salvo que
esta revisión aporte evidencia nueva.

---

## 1. Veredicto resumido

| Fuente | Veredicto | Razón determinante |
|---|---|---|
| ECB (euro FX reference rates) | **APROBABLE AHORA** | Copyright policy: "free use" con atribución; sin TTL ni prohibición de BD |
| Federal Reserve Board (H.10) | **APROBABLE AHORA** | Dominio público (17 U.S.C. §105); aviso del Board lo declara expresamente |
| SEC / EDGAR | **APROBABLE AHORA** | "información pública ... may be copied or further distributed ... without the SEC's permission" |
| CFTC (Commitments of Traders) | **APROBABLE AHORA** | "Government information ... is in the public domain ... freely distributed and copied" |
| Nasdaq Data Link | **CONDICIONAL (licencia escrita)** | nasdaq.com/legal §6 personal/no-comercial; §7 prohíbe derivados/redistribución; prohibición expresa de ML/analítica sin permiso escrito |
| Twelve Data | **CONDICIONAL (licencia escrita)** | Evaluación previa vigente (Business/Derived Data reconocidos, TTL/modelos/borrado requieren escrito) |
| Proveedores comerciales de venue (CME, Cboe, ICE, Databento) | **CONDICIONAL (licencia escrita)** | Licencias de market data contractuales; sin acuerdo no hay persistencia/redistribución |
| CryptoDataDownload (tier "Go Pro" de pago) | **CONDICIONAL (licencia de pago)** | El tier gratuito es CC BY-NC-SA; la vía comercial es una licencia de pago separada |
| FRED (St. Louis Fed) | **RECHAZADO para persistencia** | Prohibición expresa de "store, cache, or archive ... incorporate in any database" |
| Stooq | **RECHAZADO / NO VERIFICABLE** | §5.3 prohíbe redistribución; no concede almacenamiento ni uso comercial |
| CryptoDataDownload (tier gratuito) | **RECHAZADO** | CC BY-NC-SA 4.0 + "non-commercial uses only" |
| Dukascopy / Binance / Alpha Vantage | **RECHAZADO (sin cambio)** | Sin evidencia nueva; ver evaluaciones previas |

---

## 2. Categorías de derechos evaluadas

Para cada fuente se revisaron cinco ejes, alineados con la matriz de
`DataRightsManifest` del dominio:

1. **Almacenamiento / persistencia** — retención durable, construcción de base de
   datos histórica, backups, sin TTL.
2. **Derivados / features** — derecho a construir features, métricas, modelos y
   parámetros derivados.
3. **Investigación** — uso para backtesting/validación reproducible.
4. **Uso comercial** — explotación comercial interna o a socios, y productos que
   incorporen los datos.
5. **Redistribución** — re-exportación, feed, API sustituta, presentación a terceros.

---

## 3. Fuentes aprobables ahora (licencia abierta / dominio público verificada)

### 3.1 ECB — euro foreign exchange reference rates
- Estado previo: APROBADO (ADR-007). **Re-verificado 2026-11-24 sin cambios.**
- URL: https://www.ecb.europa.eu/services/disclaimer/html/index.en.html
  (redirige a `.../using-our-site/disclaimer/...`); 107 792 bytes, coincide con el
  tamaño registrado en la evaluación del 2026-11-04.
- Derechos: "free use of the information obtained directly from it" con tres
  condiciones (citar al BCE, declarar disponibilidad gratuita si se vende, declarar
  modificaciones). Sin TTL, sin prohibición de bases de datos, sin obligación de borrado.
- **Restricción de producto** (no legal): fixing diario, mid-point, sin bid/ask.
  Habilita `QUOTE_REPLAY_BACKTEST` diario con costos modelados, no ticks/opciones.
- Datos: https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip (CSV completo desde 1999).

### 3.2 Federal Reserve Board — H.10 Foreign Exchange Rates
- Estado previo: APROBADO (ADR-008). **Re-verificado 2026-11-24 sin cambios.**
- URL: https://www.federalreserve.gov/disclaimer.htm (85 306 bytes, coincide).
- Derechos: "information on Board's website is in the public domain and may be copied
  and distributed without permission. Please cite to the Board." Marco: 17 U.S.C. §105.
- Restricción de producto: fixing diario (noon buying rates, Nueva York), base USD.
  Segunda fuente independiente para validación cruzada de la señal EURGBP.
- Nota: los sellos/logos del Board están protegidos por ley federal; no usarlos.

### 3.3 SEC / EDGAR — filings y datos estructurados
- **Nuevo en esta revisión.** Fuente oficial:
  - Diseminación/reutilización: https://www.sec.gov/about/privacy-information
    ("Last Reviewed or Updated: Nov. 29, 2023").
    > "Information presented on sec.gov is considered public information and may be
    > copied or further distributed by users of the web site without the SEC's permission.
    > Please consider appropriate citation to the SEC as the source."
  - Acceso a EDGAR: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
  - Developer/fair access: https://www.sec.gov/about/developer-resources
    ("Last Reviewed or Updated: March 10, 2025"): límite ≤ 10 req/s; no se permite
    "unclassified bots"; moderar volumen.
- Derechos: información pública, copiable y redistribuible; atribución recomendada.
  Restricciones: sellos/logos/marcas (EDGAR) registradas — no usar en nombre de dominio
  ni trade name; límite de tasa (fair access).
- Naturaleza de datos: **no es OHLC/ticks**. Es datos de filings/eventos (fechas,
  formularios, XBRL financiero). Encaja como **fuente de eventos ordenados** (ver §6),
  no como serie de precios.

### 3.4 CFTC — Commitments of Traders (COT)
- **Nuevo en esta revisión.** Fuente oficial:
  - Política web/copyright: https://www.cftc.gov/webpolicy/index.htm
    > "Government information at the CFTC website is in the public domain. Public
    > domain information may be freely distributed and copied, but it is requested that
    > in any subsequent use the CFTC be given appropriate acknowledgement."
  - Reportes COT: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
    (histórico comprimido anual + Public Reporting Environment desde oct. 2022).
- Derechos: dominio público; atribución solicitada. Restricción: no usar el sello CFTC;
  materiales de terceros señalados pueden tener copyright propio.
- Naturaleza: **posicionamiento semanal** (open interest por categoría de trader),
  datos del martes publicados el viernes. No es precio; es señal de flujo/posicionamiento.

---

## 4. Fuentes condicionadas a licencia contractual escrita

### 4.1 Nasdaq Data Link (antes Quandl)
- Fuente oficial: https://www.nasdaq.com/legal (términos generales de Nasdaq aplicables
  al servicio; la página de términos del portal `data.nasdaq.com` está tras una app JS +
  Incapsula — no se pudo leer texto estático público el 2026-11-24).
- Cláusulas determinantes (nasdaq.com/legal, accedido 2026-11-24):
  - §6: "grants you a personal, limited, revocable, non-exclusive, non-assignable,
    non-sublicensable and non-transferable license to use the Services **solely for your
    personal, non-commercial use**."
  - §7: "you shall not market, sell or distribute the Services ... without Nasdaq's prior
    written consent" y "You shall not share, transfer, disclose, copy, publish or create
    **derivative works** from the content ... without Nasdaq's prior written approval."
  - §7 (ML): "You agree not to use, copy, or extract any part of the Content ... for the
    purpose of **training, coding or development of artificial intelligence systems,
    machine learning models, or any other form of data analysis software** without
    Nasdaq's express written permission."
  - Content: "You may not ... **store for subsequent use**, create any derivative works
    from, offer products or services based on ... the Content without the prior written
    consent of Nasdaq."
- Veredicto: **CONDICIONAL.** Ni los datasets "abiertos/gratuitos" del portal ni los
  premium son usables para persistencia/derivados/comercial sin un acuerdo escrito.
  Los datasets premium tienen además licencias por-publicador (publisher-specific).
  La prohibición explícita de "data analysis software / ML" alcanza directamente la
  actividad cuantitativa del proyecto.

### 4.2 Twelve Data
- Evaluación previa vigente (docs/data/provider-evaluation-twelve-data.md):
  **CANDIDATO CONDICIONAL, BLOQUEADO.** Reconoce planes Business y Derived Data no
  reversible, pero TTL para corpus históricos, modelos, backups y retención
  post-terminación requieren orden/licencia escrita.

### 4.3 Proveedores comerciales de venue (mercados convencionales)
- CME Group Market Data: https://www.cmegroup.com/market-data/ (licencias de market
  data contractuales; página de licensing devolvió 403 a bots el 2026-11-24, consistente
  con un muro de acceso — el texto de licencia no es público).
- Cboe / Cboe DataShop: https://datashop.cboe.com/ (términos en portal autenticado).
- ICE Data Services: https://www.ice.com/fixed-income-data-services (portal corporativo;
  licencias contractuales).
- Databento (tick/OHLC equities, futures, options, crypto): https://databento.com/pricing
  (app JS; licencias por contrato/entitlement).
- Veredicto conjunto: **CONDICIONAL.** Todos exigen un acuerdo de licencia de market
  data escrito (o entitlement de pago) antes de persistencia, derivados o redistribución.
  Son la única vía realista para OHLC/ticks de mercados convencionales, pero ninguno
  tiene texto público que conceda los derechos requeridos.

### 4.4 CryptoDataDownload — tier "Go Pro" (comercial)
- Fuente: https://www.cryptodatadownload.com/data/ indica "Need a commercial-use
  license? Go Pro →" y el tier gratuito es "Attribution-NonCommercial-ShareAlike 4.0
  International" (https://creativecommons.org/licenses/by-nc-sa/4.0/).
- Veredicto: **CONDICIONAL.** La vía comercial es una licencia de pago separada
  ("Go Pro"), no verificable sin contrato. El tier gratuito queda en §5 (rechazado).

---

## 5. Rechazadas / no verificables

### 5.1 FRED (Federal Reserve Bank of St. Louis)
- **Nuevo en esta revisión — hallazgo importante.** FRED **no** es dominio público como
  tal: es una base de datos operada por el St. Louis Fed con términos propios.
- Fuente oficial: https://fred.stlouisfed.org/legal (accedido 2026-11-24; sin número de
  versión/fecha visible; "Terms of Use may be amended ... without notice").
- Cláusulas determinantes:
  - General License: "download or print a copy ... **solely for your personal,
    non-commercial use**."
  - Prohibitions (FAQ y §(p) de Prohibitions): "Don't do any **data mining, scraping or
    extraction** of FRED data"; "You may not ... **Store, cache, or archive any portion
    of the FRED® Services or FRED® Content; provide any stored ... portion ... to any
    third party; or incorporate any FRED® Content in any database, compilation, archive,
    cache, or other medium**."
  - Prohibitions §(j): "use the FRED® Services for any commercial use without the prior
    written consent of the Bank."
- Veredicto: **RECHAZADO para persistencia.** La prohibición expresa de almacenar/archivar/
  incorporar en base de datos bloquea exactamente el requisito de persistencia histórica
  del proyecto, pese a que el resumen del propio FRED permita "internal commercial uses"
  para series etiquetadas Public Domain / Citation-required (esa concesión de display no
  anula la prohibición de almacenamiento en BD).
- **Escape válido:** obtener los mismos datos de la agencia primaria (p. ej. el H.10
  directamente en federalreserve.gov, BEA, BLS, Treasury), cuyas publicaciones sí son
  dominio público / licencia permisiva. FRED es cómodo como índice de descubrimiento,
  no como origen de persistencia.

### 5.2 Stooq
- Fuente: https://stooq.com/terms.html (accedido 2026-11-24; "Terms of Service may be
  changed at any time").
- Cláusulas determinantes:
  - §5.3: "Redistribution of data found on the website is **not allowed without the
    consent of Stooq**."
  - §6.1: datos S&P Dow Jones solo "personal, non-commercial"; prohibido crear productos
    financieros que los trackeen.
  - §6.2: datos LME sin distribución sin consentimiento escrito.
- Veredicto: **RECHAZADO / NO VERIFICABLE.** Los términos no conceden explícitamente
  almacenamiento durable ni uso comercial para el resto de datos, y prohíben
  redistribución. Bajo la regla "unspecified = blocking", no supera persistencia,
  comercial ni redistribución.

### 5.3 CryptoDataDownload — tier gratuito
- Fuente: https://www.cryptodatadownload.com/terms-of-use/ ("last updated 20 Sep 2023").
  - "Users of this website should use the information contained herein for
    **non-commercial uses only**. Cryptodatadownload.com does not consent to any use of
    the information contained herein for **commercial purposes**."
  - La página de datos aplica CC BY-NC-SA 4.0.
- Veredicto: **RECHAZADO** (mismo patrón que Binance Vision: no-comercial + ShareAlike).

### 5.4 Rechazos previos sin evidencia nueva
- **Dukascopy, Binance, Alpha Vantage, Bank of England, Deriv** — se mantienen los
  veredictos de las evaluaciones existentes. No se recomienda ninguno sin evidencia
  nueva verificada. No se re-evaluaron en esta pasada porque no hay indicio de cambio
  en sus términos.

---

## 6. Mercados convencionales incorporables con el dominio actual

### 6.1 Primitivas existentes del dominio (`src/devsoul_quant/domain`)
- **Eventos ordenados:** `Tick(epoch, quote, pip_size)` con secuencia estrictamente
  creciente; `replay_rise_fall`, `replay_digit`, `replay_multiplier` consumen secuencias
  ordenadas de ticks.
- **Contratos/settlement:** `EnterContractIntent` (duración en **ticks**, `DurationUnit.TICKS`),
  `ContractType` = CALL/PUT/DIGITEVEN/DIGITODD/MULTUP/MULTDOWN; `Outcome` (WIN/LOSS) sin
  reclamo monetario; `EconomyProvenance` = OBSERVED/ESTIMATED/UNAVAILABLE.
- **Costs:** `ExecutionCostModel` (spread_fraction relativo) y `BinaryOptionEconomics`
  (payout fijo, break-even).
- **Derechos:** `DataRightsManifest` (storage/derivados/partner/redistribución/comercial/
  geografía/escrito) con `decide_persistent_use` fail-closed; `MarketDataPort.load_ticks`.
- **Features:** `features.py` — familia "momentum-baseline" (lag/rolling windows sobre
  ticks), causal, sin fuga futura.

### 6.2 Qué encaja hoy (sin cambiar el dominio cuantitativo)
| Mercado / dato | Encaje | Estado |
|---|---|---|
| FX diario (ECB, Fed H.10) | fixing diario → `Tick`; `QUOTE_REPLAY_BACKTEST` diario con `ExecutionCostModel` | **YA INTEGRADO** (adapters `ecb/ingest`, `federal_reserve/ingest`; `ecb_backtest`, `fed_h10_confirmation`) |
| Posicionamiento semanal (CFTC COT) | evento programado semanal → feature de flujo | Requiere **nuevo adapter + feature domain** (no existe hoy) |
| Filings/eventos SEC EDGAR | eventos ordenados por timestamp (no precio) | Requiere **nuevo adapter + tipo de evento** distinto de `Tick` |
| OHLC/ticks acciones/futuros | precio intradía → replay direccional | **Bloqueado** sin licencia (Nasdaq/CME/Cboe/Databento: condicional) |

Observación central: el dominio actual es **tick-céntrico** y de **contratos de duración
en ticks**. Los datos aprobables ahora (ECB/H.10) son diarios y ya se mapean a ticks
diarios. Los mercados convencionales intradía (OHLC/ticks reales de acciones/futuros)
siguen sin fuente permisiva — la única vía es licencia comercial escrita (§4.3).

### 6.3 Adaptadores/extensiones que serían necesarios (sin implementar)
1. **Adapter de OHLC/bar → Tick** (para una fuente licenciada): un bar no es un tick;
   se necesita una convención de muestreo (open/high/low/close/volume → secuencia de
   decisiones) o un replay bar-aware. Hoy `replay_rise_fall` asume ticks contiguos y
   duración en ticks.
2. **Extensión `DurationUnit`** (hoy solo `TICKS`): añadir `SECONDS`/`BARS`/`DAYS` para
   contratos temporales de mercados convencionales, con un reloj controlable (ya existe
   `clock` replay/system).
3. **Extensión de settlement/costos por contrato:** `ExecutionCostModel` solo modela
   spread relativo; un mercado convencional necesita comisión, slippage y financiación
   (swap/carry) por contrato — un `SettlementEconomics` más rico (dirección, cantidad,
   comisión, slippage) que hoy no existe.
4. **Adapter de eventos de filings (SEC):** nuevo tipo `Event` (no `Tick`) con
   timestamp, form type, CIK, XBRL; el pipeline de replay no lo consume — requeriría un
   `EventPort` separado y una estrategia dirigida por eventos.
5. **Adapter + feature domain de posicionamiento (CFTC COT):** nuevo `PositioningEvent`
   semanal y features de flujo (net positioning por categoría), fuera de la familia
   "momentum-baseline" actual.
6. **Manifest por fuente nueva:** cada fuente adoptada necesita `DataRightsManifest`
   con `source_kind` correcto (`OPEN_LICENSE` para BCE/CFTC/SEC-EDGAR; `LICENSED_EXTERNAL`
   con `written_authorization_ref` para las condicionales).

Ninguno de estos adaptadores se implementa en esta tarea; se listan solo como diseño
previo a cualquier adopción.

---

## 7. Fuentes y fecha de acceso (registro)

Todas accedidas el **2026-11-24**. Solo fuentes oficiales.

| # | URL | Naturaleza |
|---|---|---|
| 1 | https://www.ecb.europa.eu/services/disclaimer/html/index.en.html | Copyright/uso (ECB) |
| 2 | https://www.federalreserve.gov/disclaimer.htm | Dominio público (Board) |
| 3 | https://www.sec.gov/about/privacy-information | Diseminación SEC ("public information") |
| 4 | https://www.sec.gov/about/developer-resources | Fair access / 10 req/s |
| 5 | https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data | Acceso EDGAR |
| 6 | https://www.cftc.gov/webpolicy/index.htm | Copyright CFTC (dominio público) |
| 7 | https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm | COT |
| 8 | https://www.nasdaq.com/legal | Términos Nasdaq (§6, §7) |
| 9 | https://fred.stlouisfed.org/legal | Términos FRED (prohibición de almacenamiento) |
| 10 | https://stooq.com/terms.html | Términos Stooq (§5.3, §6) |
| 11 | https://www.cryptodatadownload.com/terms-of-use/ | Términos CDD (no-comercial) |
| 12 | https://www.cryptodatadownload.com/data/ | CC BY-NC-SA 4.0 + "Go Pro" |
| 13 | https://www.cmegroup.com/market-data/ | Market data (licencia contractual; 403 a bots) |
| 14 | https://databento.com/pricing | Tick/OHLC (licencia por contrato; app JS) |

---

## 8. Conclusión operativa

- **Persistencia e investigación ya viables** con ECB, Fed H.10 (FX diario) y — si se
  desea ampliar el dominio de eventos — SEC EDGAR y CFTC COT (ambos dominio público).
- **Uso comercial eventual:** ECB exige atribución/aviso; Fed H.10, SEC y CFTC son
  dominio público con atribución. Ninguno bloquea comercialización.
- **OHLC/ticks de mercados convencionales** siguen **bloqueados** sin una licencia
  comercial escrita (Nasdaq Data Link, CME/Cboe/ICE/Databento). La prohibición expresa
  de Nasdaq contra ML/análisis de datos sin permiso escrito refuerza que esta vía exige
  contrato, no un plan de precios.
- **FRED y Stooq no sirven** para persistencia: FRED prohíbe incorporar contenido en
  bases de datos; Stooq no concede almacenamiento/comercial y prohíbe redistribución.
  Para datos equivalentes a FRED, ir a la agencia primaria (dominio público).
- **No se recomienda ninguna fuente previamente rechazada** sin evidencia nueva
  verificada (Dukascopy, Binance, Alpha Vantage, BoE, Deriv).
