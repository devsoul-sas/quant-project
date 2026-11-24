# Darwinex / Tradeslide — Términos de API y market data (derechos de datos)

- Fecha de consulta: 2026-11-05
- Alcance: términos oficiales Darwinex/Tradeslide sobre API, market data y derechos para
  non-display automation, almacenamiento de quotes/histórico, backtesting,
  derivados/features/modelos, uso comercial, display/redistribución y terminación.
- Veredicto: **NOT GRANTED / BLOCKED (fail-closed)**. El acceso API no implica licencia.
  Ningún documento oficial concede por escrito persistencia local reproducible de
  bid/ask EURGBP ni retención de derivados para investigación potencialmente comercial.
- `UNKNOWN/BLOCKING` significa falta de evidencia oficial suficiente; no afirma que la
  actividad esté prohibida. Cuando un documento *prohíbe* expresamente algo, se marca
  `PROHIBITED`.

Esta evaluación distingue tres capas de términos, que no deben mezclarse:

| Capa | Documento | Entidad firmante | Alcance |
|---|---|---|---|
| Website terms | `terms-conditions.pdf` ("Terms of Use") | Tradeslide Trading Tech Ltd (UK, 08061368) | Contenido del sitio www.darwinex.com |
| Platform/broker terms | `client-agreement.pdf` ("TTT TOB – all clients **May 2023**") | Tradeslide Trading Tech Ltd (FCA FRN 586466) | Servicios de corretaje, cuentas, plataformas, market data |
| Data vendor / API terms | `darwin-api-conditions.pdf` ("DARWIN API T&C") | Tradeslide Trading Tech Ltd | DARWIN API (REST + WebSocket) y "Darwinex Data" |

Nota de entidad: la marca Darwinex opera sobre (a) **Tradeslide Trading Tech Ltd**
(FCA FRN 586466, UK 08061368) — broker/plataforma; (b) **Sapiens Markets EU Sociedad de
Valores SA** (CNMV 311) — "Darwinex EU"; (c) **Tradeslide Global Ltd** (FSA Seychelles
SD171) — "Darwinex Global"; (d) **Tradeslide Technologies Ltd** (UK 14398381) — "Darwinex
Zero" (capa de track-record, no venue). Los PDF citados aquí son los del folder FCA
(`d139oolcsxoepg.cloudfront.net/static_content/legal/FCA/`), es decir, la entidad UK.

## Fuentes oficiales (recuperadas 2026-11-05)

| Documento | URL de página | PDF (iframe) | SHA-256 |
|---|---|---|---|
| Terms of Use (website) | https://www.darwinex.com/legal/terms-conditions | `.../FCA/terms-conditions.pdf` | `e45b17a1c38265bb0e7c347c1bc12dbc73587e63bd6144b181fad3105fa4c5d4` |
| Client Agreement (broker) | https://www.darwinex.com/legal/client-agreement | `.../FCA/client-agreement.pdf` | `b81c7d674fc642f079172047b5759135141dbe42795581f5a3a9ad6c41d997b8` |
| DARWIN API T&C (data/API) | https://www.darwinex.com/legal/darwin-api-conditions | `.../FCA/darwin-api-conditions.pdf` | `3cc29b9c7d2b72ce3ff7dc9f97ceeb3e38b9dae78482f76a1514720f7bb48193` |

Corroboración técnica (no son términos, solo describen la oferta):

- `https://www.darwinex.com/data/darwin-data` — Raw DARWIN Data (FTP
  `darwindata.darwinex.com`), "completely free of charge", quotes en resolución de
  segundos + series de tiempo. **Es el índice DARWIN, no el bid/ask EURGBP.**
- `https://help.darwinex.com/raw-darwin-data-user-guide` — estructura FTP.
- `https://api.darwinex.com/store/` — documentación del DARWIN API (referenciada por el
  README oficial `darwinex/darwinexapis`; no accesible desde este entorno, timeout).
- `github.com/darwinex/darwinexapis` — wrapper oficial: TickData API (FTP
  `tickdata.darwinex.com`) para activos tradicionales (FX, stocks…).
- `github.com/darwinex/DarwinexLabs` — datasets flat-file de DARWIN data **offline desde
  2018-12-21** ("Please contact info@darwinex.com to request DARWIN API access instead").

## Fechas / versión

- **Client Agreement**: título interno del PDF = `TTT TOB - all clients May 2023`. Es la
  versión vigente servida desde el folder FCA a fecha 2026-11-05.
- **Terms of Use** y **DARWIN API T&C**: **no** imprimen versión ni fecha de vigencia ni
  "last updated". Se sirven sin redline ni historial de versiones. Conforme al criterio
  de la skill, la ausencia de fecha de vigencia publicada se registra como
  `UNKNOWN` en cuanto a trazabilidad de cambios, no como "sin cambios".

---

## 1. Website Terms of Use (capa website)

Entidad: Tradeslide Trading Tech Ltd, "whose registered office is Acre House, 11-15
William Road, London NW1 3ER", UK reg 08061368.

- **1.2.1** — copyright/IP del sitio propiedad de TradeSlide o sus licenciantes;
  "any use of extracts from this Website other than in accordance with clause 1.2.2, for
  any purpose is prohibited".
- **1.2.2** — "no part of this Website may be **reproduced or stored** in any other website
  or included in any public or private electronic retrieval system or service without
  TradeSlide's **prior written permission**."
- **1.2.3** — "Any rights not expressly granted in these terms are reserved."
- **6 (Termination)** — 30 días de preaviso; "the respective user account will be deleted".

Lectura: estas cláusulas gobiernan el **contenido del sitio web**, no el feed de mercado.
Aun así, fijan un patrón fail-closed: nada se almacena/reproduce sin permiso escrito.

## 2. Client Agreement (capa platform/broker)

Entidad: Tradeslide Trading Tech Ltd (el "we/us"), FCA FRN 586466. Cobertura: XO Service
(CFDs, FX, etc.), Electronic Services, plataformas.

### 2.1 Market data — cláusula 9 (la cláusula de control para quotes)

- **9.1(c)** — "you will use such data or information **solely for the purposes set out in
  this Agreement**". Es decir, el uso permitido del dato de mercado queda limitado al
  propósito del contrato (operar), no a un corpus de investigación/backtesting.
- **9.1(d)** — "such data or information is **proprietary** to us and any such provider and
  you will **not retransmit, redistribute, publish, disclose or display** in whole or in
  part such data or information **to third parties** except as required by Applicable
  Regulations." → **PROHIBITED** para display/redistribución a terceros (incluye dashboard
  de socio o SaaS).
- **9.1 (in fine)** — para "exchange data" electivo, "you hereby agree to any terms and
  conditions relating to the redistribution and use of such data as set out on our Website
  on the **exchange permissions page**." (Página no localizada en rutas públicas
  `legal/exchange-permissions` / `exchange-permissions` → `404`; se registra como
  `UNKNOWN` en cuanto a los términos del exchange aplicable.)

### 2.2 Automatización (non-display)

- **9.3** — EA/Script/Indicator "as is" y bajo responsabilidad exclusiva del cliente.
- **9.6** — "As a default for your Trading Account, **the use of any Automatic Trading Tool
  is prohibited without our prior written consent.**" El consentimiento es discrecional,
  requiere due diligence y puede revocarse. → La automatización **no** está autorizada por
  defecto: exige consentimiento previo escrito.
- **13.1 (Improper Activity)** — prohíbe "using any electronic device, software, algorithm,
  server or any dealing strategy that aims to manipulate or take unfair advantage of our
  Services", incl. explotar latencias, precios demorados o "high volumes of transactions
  targeting tick fluctuations". → `BLOCKED` para estrategias de arbitraje de latencia /
  caza de ticks.
- **13.2** — sanción: terminación inmediata de cuentas y void de trades.

### 2.3 Derivados / features / modelos

- El Client Agreement **no contiene** cláusula que conceda licencia para retener
  features/modelos/backtests derivados del dato de mercado. La cláusula 9.1(c) restringe
  el uso al propósito del contrato. → `UNKNOWN/BLOCKING` (no concedido).

### 2.4 Terminación

- **28.4** — terminación por el cliente en cualquier momento; por la firma con 30 días de
  preaviso. **28.2** lista Eventos de Default (incl. "unfair advantage", 28.2.10).

## 3. DARWIN API T&C (capa data vendor / API)

Entidad: Tradeslide Trading Tech Ltd. Suplementa las "Terms of Service" del sitio.
Define el DARWIN API (REST + WebSocket) y la documentación en
`https://www.darwinex.com/data/darwin-api`.

- **1.3** — licencia a la documentación: "revocable, non-exclusive, non-sublicensable,
  non-transferrable".
- **1.7** — "suspend or revoke your access to the DARWIN API, **at any time and for any
  reason**".
- **2.1** — "You will not use or access the DARWIN API in any way **not expressly
  permitted**". **2.1.1(5)** prohíbe "replicate or attempt to replace the essential user
  experience of the Services".
- **3.2 (Data That You Collect)** — "Darwinex Data" incluye datos "collected by Darwinex or
  **made available by third parties**". **"You may only use such Darwinex Data for your
  internal purposes or within your Application and will not disclose, sell or transfer any
  Darwinex Data without our prior written consent."**
  → El único permiso es uso "internal purposes" / dentro de la Application; toda
  divulgación/venta/transferencia exige consentimiento escrito. No cubre uso comercial
  externo ni redistribución.
- **3.3** — borrar datos con información personal.
- **3.4 (Deletion of Darwinex Data)** — **"You will immediately delete any and all Darwinex
  Data: (1) upon our request …; (2) when your access to the DARWIN API is suspended or
  revoked; (3) when you deactivate your Application …; or (4) when it is no longer
  reasonably required by you or your Application."**
  → La persistencia local no sobrevive la terminación/revocación/desactivación. Esto rompe
  el requisito de corpus histórico local reproducible.
- **6 (Ownership)** — "All rights (including intellectual property rights) … in and to the
  DARWIN API, the DARWIN API Documentation, Aggregated Statistical Information, Darwinex
  Data and all other materials provided by us hereunder, **and any update, adaptation,
  translation, customization or derivative work thereof, will remain with us** (or our
  third party suppliers, if applicable). … licensed and not 'sold'. **All rights not
  expressly granted … are reserved.**"
  → Los "derivative works" de Darwinex Data quedan en propiedad de Darwinex. **`BLOCKED`**
  para reclamar/retener features o modelos derivados como propios.
- **9 (Change)** — cambios sin preaviso; el uso continuado implica aceptación.

## 4. Oferta de datos (contexto, no licencia)

- **Raw DARWIN Data (FTP `darwindata.darwinex.com`)** — quotes del índice DARWIN
  (indexados a 100) en resolución de segundos + series estadísticas. "Darwinex offers,
  completely free of charge, raw DARWIN data". **No es bid/ask EURGBP** y, por la cláusula
  3.2/6 del DARWIN API T&C, su uso queda limitado a "internal purposes" con derivados
  reservados a Darwinex.
- **TickData API (FTP `tickdata.darwinex.com`)** — activos tradicionales (FX, índices,
  etc.), requiere token de API. **No se encontró un documento de licencia separado** para
  este feed; los términos de control serían el Client Agreement cl. 9 (prohibición de
  redistribución) y el DARWIN API T&C (si se accede vía API). → `UNKNOWN/BLOCKING` en
  cuanto a licencia específica de tick data.
- **DarwinexLabs flat-file** — datasets offline desde 2018-12-21; comunidad DARWIN descrita
  como "the Darwinex community's intellectual property".

## 5. Matriz de derechos (fail-closed)

| Dimensión | Hallazgo | Veredicto |
|---|---|---|
| Non-display automation | CA 9.6: Automatic Trading Tool prohibido sin **consentimiento previo escrito**; CA 13.1 prohíbe algoritmos de latencia/ticks; DARWIN API 2.1 "not expressly permitted" | `BLOCKED` (exige permiso escrito) |
| Almacenamiento quotes/histórico | CA 9.1(c) limita uso al propósito del contrato; DARWIN API 3.4 ordena borrar al revocar/desactivar; Website 1.2.2 prohíbe almacenar sin permiso | `NOT GRANTED` / `BLOCKED` |
| Backtesting | DARWIN API 3.2 permite solo "internal purposes"; no hay licencia para backtest comercial | `BLOCKED` (comercial) |
| Derivados / features / modelos | DARWIN API 6: "derivative work" permanece de Darwinex; CA sin cláusula de licencia | `BLOCKED` |
| Uso comercial | DARWIN API 3.2: sin "disclose, sell or transfer" sin consentimiento escrito; CA 9.1(d) | `BLOCKED` |
| Display / redistribución | CA 9.1(d) "not retransmit, redistribute, publish, disclose or display … to third parties"; DARWIN API 3.2 | `PROHIBITED` por defecto |
| Terminación | DARWIN API 3.4 borrado inmediato; CA 28 (30 días / Eventos de Default); Website 6 (cuenta borrada) | La persistencia **no** sobrevive la terminación |

## 6. Veredicto fail-closed

**NOT GRANTED / BLOCKED.** Para el objetivo declarado — persistencia local reproducible de
bid/ask EURGBP y derivados para investigación *potencialmente comercial* — las fuentes
oficiales Darwinex/Tradeslide **no** conceden derecho por escrito:

1. El dato de mercado está protegido por **CA 9.1(d)** (prohibición de retransmitir/
   redistribuir/publicar/mostrar a terceros) y su uso queda limitado al propósito del
   contrato (**9.1(c)**).
2. El **DARWIN API T&C 3.4** obliga a borrar todo "Darwinex Data" al revocar/desactivar/
   dejar de necesitarlo, y la **cláusula 6** reserva a Darwinex toda "derivative work".
3. La automatización no-display exige **consentimiento previo escrito** (CA 9.6) y está
   sujeta a las restricciones de actividad impropia (CA 13).
4. No se localizó ningún **market-data / API supplement** ni "exchange permissions page"
   que autorice almacenamiento durable, derivados ni uso comercial.

Conclusión operativa: Darwinex/Tradeslide **no** desbloquea el gate de datos para el
requisito de persistencia comercial. No se abren cuentas, no se generan tokens, no se
descarga ni conserva ningún payload de mercado. Los PDF se mantienen solo en `/tmp/` con
fines de verificación de cláusulas y **no** entran en Git. Cualquier vía futura exige
confirmación escrita de Darwinex que cubra almacenamiento, derivados, uso comercial y
supervivencia post-terminación.

## Relación con evaluaciones previas

- [execution-venue-darwinex-zero.md](execution-venue-darwinex-zero.md) — Darwinex Zero no
  es venue; cláusulas 1.2.2/3.5 del sitio `darwinexzero.com`.
- [provider-evaluation-darwinex-global.md](provider-evaluation-darwinex-global.md) —
  Tradeslide Global Ltd (Seychelles) como venue de ejecución: NOT APPROVED; el CSA global
  tampoco incluye licencia de market data. Este documento aporta las citas exactas de la
  capa FCA (Client Agreement cl. 9, DARWIN API T&C cl. 3/6) que faltaban en aquella
  evaluación.
