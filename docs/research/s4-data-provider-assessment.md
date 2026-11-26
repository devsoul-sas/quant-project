# S4 — Evaluación de proveedores de datos y ejecución (cripto Spot)

Fecha: 2026-11-24
Estado: `ASSESSMENT_ONLY — NO EXECUTION`
Regla de decisión: `unspecified ≠ allowed` (lo no autorizado explícitamente bloquea).

## 1. Corrección de un veredicto previo (evidencia nueva)

El rechazo de Binance de 2026-10-29 confundió **dos instrumentos legales distintos**:

| Instrumento | Qué gobierna | Régimen de datos |
|---|---|---|
| **Binance Vision Dataset Terms** | Portal de descarga masiva `data.binance.vision` | CC BY-NC-SA 4.0; backtesting solo "personal non-production"; Cl. 4.2 prohíbe "live proprietary trading execution / automated commercial order generation" |
| **Binance Exchange ToU + API Keys Product Terms** | Titular de cuenta que opera **vía API** | Cl. 33.7 contempla "constructing automated trading systems"; Cl. 27 licencia para "internal business use" |

El rechazo previo se basó íntegramente en el instrumento equivocado (Vision). La vía
que S4 necesita — operar capital propio por la API de exchange — está gobernada por
los Exchange ToU + API terms, que son **materialmente más favorables**. Este
documento corrige el veredicto con cláusulas verbatim verificadas.

---

## 2. Binance — proveedor recomendado (condicional)

### 2.1 Entidad y disponibilidad Colombia

- Entidades: **ADGM Binance Entities** — NEST Exchange Ltd (NEL), NEST Clearing and
  Custody Ltd (NCCL), NEST Trading Ltd (NTL), reguladas por FSRA (Abu Dhabi).
- Lista de países prohibidos (URL `binance.com/en/about-legal/list-of-prohibited-countries`,
  "Updated: 5 January 2026"): US, Canada, Netherlands, Cuba, North Korea, Iran,
  Crimea, Donetsk (DNR), Luhansk (LNR). **Colombia NO figura.**
- **Pendiente/BLOQUEANTE parcial:** la ausencia de Colombia en la lista prueba que no
  está bloqueada por territorio, pero no confirma positivamente qué entidad/producto
  exacto se ofrece a un residente colombiano. Requiere confirmación en onboarding/KYC.

### 2.2 Comisiones (verificado `binance.com/en/fee/schedule`, 2026-11-24)

| Tier | 30d vol USD | Maker / Taker | Con BNB (25% off) |
|---|---|---:|---|
| VIP0 | < 1M | 0.100% / 0.100% | 0.075% / 0.075% |
| VIP3 | ≥ 20M | 0.040% / 0.060% | 0.030% / 0.045% |
| VIP9 | ≥ 4B | 0.011% / 0.023% | 0.00825% / 0.01725% |

### 2.3 API de market data (spot)

- Endpoint: `GET /api/v3/klines` (base pública `data-api.binance.vision`).
- Granularidad: OHLCV de 1s a 1 mes (intervalo 1s añadido por changelog; enumeración
  exacta a fijar contra catálogo).
- Peso por request: `klines` = 1. Rate limits: `REQUEST_WEIGHT` 6000/min,
  `ORDERS` 10/s, `RAW_REQUESTS` 61000/5min (por IP; órdenes por cuenta).
- Profundidad: **histórico completo paginable** vía `startTime`/`endTime`, sin tope de
  antigüedad documentado. (Contraste: Kraken solo 720 velas, ver §3.)

### 2.4 Simulación

- **Spot Test Network**: `testnet.binance.vision` (HTTP 200), reset ~mensual.
- **Spot Demo Mode** adicional (términos `terms-demo-trading`).

### 2.5 Tamaño mínimo

Sin mínimo global; por símbolo vía `GET /api/v3/exchangeInfo`
(`LOT_SIZE.minQty`, `MIN_NOTIONAL.minNotional`). Ejemplos doc: `minNotional` 10 ó 0.001.

### 2.6 Cláusulas decisivas (verbatim, verificadas contra PDF oficial)

**Exchange ToU** — "ADGM Binance Global Terms of Use", Effective 2026-10-27,
PDF CDN oficial, SHA-256 `f7c3c8a8fbda48eaa272ff503b8c2e54c6c98ad4f0f2a1e5da3667af5962c7de`:

- Cl. 14.1.2(b): *"Your Binance Account can be accessed through: … (b) Binance APIs,
  subject to separate API terms and our approval; or …"*
- Cl. 33.7: *"… trading technology, web applications, application programme
  interfaces, software, software code, programmes, protocols and displays …
  for trading, analysing trades and markets, **constructing automated trading
  systems** and/or to assist or facilitate the provision, availability or
  connectivity of the Binance Platform …"*
- Cl. 27 (LICENCE OF BINANCE IP): *"We grant to you a non-exclusive licence for the
  duration of the Agreement … to use the Binance IP, excluding the Trade Marks,
  **solely as necessary to allow you to receive the Binance Services for
  non-commercial personal or internal business use**, in accordance with the Agreement."*

**API Keys Product Terms** — "Version 2.0", effective 2026-07-09,
SHA-256 `33c4b5249d6f9155e7b2dd5fa1f50b022be1ce933371bf2b301af5f723b14dad`:

- Cl. 3.1: *"… use the API Key(s) solely to integrate with Binance and to use the
  Binance Platform only in accordance with the intended manner …"*
- Cl. 3.2(h) (única prohibición de conducta de trading): *"… use or exploit the API
  Keys for any illegitimate or nefarious purposes, including … market manipulation,
  insider trading, front running, pump and dump schemes, wash trading and/or
  spoofing …"* — **no** prohíbe trading algorítmico propietario.
- Cl. 3.2(b) (precaución): *"modify, translate, or otherwise **create derivatives**,
  improvements, modifications, enhancements, or extensions **of or relating to the
  API Keys or the API related data** … except as expressly authorized by Binance in
  writing."*

### 2.7 Veredicto Binance

| Cuestión | Veredicto |
|---|---|
| (b) Trading algorítmico propietario vía API | **AUTORIZADO** (Cl. 33.7 contempla "constructing automated trading systems"; Cl. 14.1.2(b) permite API; Cl. 3.2(h) solo prohíbe manipulación) |
| (a) Retención de histórico para backtest interno | **CONDICIONAL** — Cl. 27 licencia "internal business use" (cubre uso interno de una empresa), pero Cl. 3.2(b) restringe "derivatives of API related data" sin autorización escrita → **clarificación escrita recomendada antes de persistir histórico en producción** |
| Colombia (entidad/producto) | **PENDIENTE** — no prohibida, pero sin confirmación positiva |

---

## 3. Kraken — viable como ejecución, no como fuente de datos

### 3.1 Entidad y disponibilidad

- Colombia = Rest of World → **Payward Trading Ltd** (VASP BVI FSC). Spot habilitado.
  (Fuente: `support.kraken.com/articles/where-is-kraken-licensed-or-regulated`,
  "Last updated 2026-11-24".)

### 3.2 Comisiones (verificado `kraken.com/pro/fees`)

Tier 1 = **0.40% / 0.80%**; tier 4 ($25K) = 0.20%/0.35%; tier 12 ($10M) = 0.00%/0.10%.
Stablecoin/FX: tier 1 = 0.20%.

### 3.3 API de market data

- `GET https://api.kraken.com/0/public/OHLC` (público). Granularidad 1/5/15/30/60/240/
  1440/10080/21600 min.
- **Máx 720 velas** ("older data cannot be retrieved, regardless of the value of
  since"). Sin backfill histórico por API. Histórico largo solo vía CSVs oficiales
  de descarga (canal separado, licencia no contractual).

### 3.4 Simulación / mínimo

- Sin sandbox Spot del exchange; paper trading solo vía `kraken-cli`/MCP.
- Mínimo por par vía `AssetPairs` (`ordermin`).

### 3.5 Cláusulas decisivas (Global ToS, "Last updated 2026-11-18")

- §8 "Our Content": *"… you are permitted to use our services, and Our Content made
  available to you as part of our services, **but only for your own benefit**. …
  You do not have or acquire any rights to Our Content beyond the limited, revocable
  permission in the previous sentence. If you wish to use Our Content for any other
  purpose you must seek prior permission … marketdata@kraken.com."*
- §9 "Restrictions": *"You will not: … copy, modify … reverse engineer Our Content …
  use any web scraping, web harvesting, or data extraction methods to extract any
  data from Our Content … create, use, operate, or employ any bots, robots …
  to engage in any activity on Our Content …"*
- §4: *"Trades in which you submit limit or market buy and sell orders, including
  through Application Programming Interface (API) access to the Kraken Platform, are
  executed by us on an agency basis, on your behalf."* + soporte "Clients are welcome
  to use trading bots."

### 3.6 Veredicto Kraken

| Cuestión | Veredicto |
|---|---|
| (b) Trading algorítmico vía API | **AUTORIZADO** (§4 + "Clients are welcome to use trading bots") |
| (a) Retención de histórico | **BLOQUEADO** — §8 solo "for your own benefit" revocable; §9 prohíbe "copy"/"data extraction"; sin cláusula de retención. Además la API solo devuelve 720 velas (sin backfill) |

---

## 4. Coinbase — evidencia insuficiente (Cloudflare) + fees no verificables

### 4.1 Entidad y disponibilidad

- Routing oficial (endpoint público de onboarding): para `country_code=CO` devuelve
  acuerdo **"Coinbase Bermuda"** (`cbbl_cbsl` / `coinbase_bermuda_2`) → Colombia NO
  es rechazada. Productos Spot efectivamente habilitados: **DESCONOCIDO** (acuerdo no
  legible tras Cloudflare).

### 4.2 Comisiones

**NO VERIFICADO** — `help.coinbase.com` devuelve 403 Cloudflare. No se reporta cifra.

### 4.3 API de market data (verificado en docs oficiales)

- Advanced Trade: `GET /api/v3/brokerage/market/products/{id}/candles` (público), **máx
  350 buckets**, granularidad 1m→1d. Rate limit 10k req/h por key.
- Exchange (institucional): `GET /products/{id}/candles`, **máx 300**, 10–15 req/s.
- Profundidad histórica máxima: **no documentada**; advierte "Historical rate data may
  be incomplete".

### 4.4 Simulación / mínimo

- Exchange sandbox = paper con book subset real; Advanced Trade sandbox = **solo mocks
  estáticos** (sin libro real).
- Mínimo por producto vía `base_min_size`/`quote_min_size`.

### 4.5 Cláusulas decisivas

**No recuperadas** — `coinbase.com/legal/user_agreement` y `help.coinbase.com` tras
Cloudflare (`cf-mitigated: challenge`). Sin cláusulas verbatim.

### 4.6 Veredicto Coinbase

| Cuestión | Veredicto |
|---|---|
| (b) Trading algorítmico vía API | **DESCONOCIDO/BLOQUEANTE** (sin cláusula que autorice bots) |
| (a) Retención de histórico | **BLOQUEANTE** (sin cláusula que autorice retención) |
| Comisiones | **NO VERIFICADO** |

---

## 5. Matriz de derechos consolidada

| Criterio | Binance | Kraken | Coinbase |
|---|---|---|---|
| Disponibilidad Colombia (entidad) | Parcial (no prohibida) | PROBADO (Payward Trading BVI) | Parcial (routing Bermuda) |
| Comisión round-trip (tier base) | **0.20%** (0.15% BNB) | 1.20% | NO VERIFICADO |
| API histórico (profundidad) | **Completo paginable** | 720 velas (sin backfill) | 350 máx |
| Sandbox Spot | **Sí (testnet + demo)** | No (solo CLI paper) | Mock estático / paper institucional |
| (b) Trading algorítmico vía API | **AUTORIZADO** | AUTORIZADO | DESCONOCIDO |
| (a) Retención histórico backtest | **CONDICIONAL** ("internal business use") | BLOQUEADO | BLOQUEANTE |

---

## 6. Recomendación

**Binance es el único candidato simultáneamente viable en economía (0.10–0.20%
round-trip) y jurídicamente favorable para trading algorítmico propietario vía API**
(Cl. 33.7 "constructing automated trading systems" + Cl. 27 "internal business use").
Kraken es viable como venue de ejecución pero no como fuente de datos (720 velas +
retención bloqueada + fees 1.2%). Coinbase queda descartado por evidencia
insuficiente y fees no verificables.

Dos pre-condiciones fail-closed antes de persistir histórico en producción:

1. **Confirmación escrita de Binance** sobre entidad/productos Spot para residente
   colombiano.
2. **Clarificación escrita** del alcance de Cl. 3.2(b) ("derivatives of API related
   data") para un corpus histórico retenido + features derivados internos.

Hasta cerrar ambas, Binance se trata como **CONDICIONAL** (no aprobado pleno), y la
persistencia de histórico queda en `BLOCKED_PENDING_PERMISSION`. El detalle de
mercado/activos/horizonte/costos/esfuerzo está en `s4-market-selection.md`,
`s4-economic-feasibility.md` y en la recomendación final de esta etapa.
