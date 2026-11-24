# Darwinex / Tradeslide — Ejecución técnica (evidencia oficial)

Fecha de recuperación: **2026-11-05**. Fuentes exclusivamente oficiales (darwinex.com, help.darwinex.com, github.com/darwinex). Sin probes autenticados ni órdenes.

## 0. Entidad y alcance (delimitar entidades)

- Entidad confirmada (pie legal / Terms & Conditions):
  > "The Darwinex® trademark and the www.darwinex.com domain are commercial names used by **Tradeslide Trading Tech**, a company authorised and regulated by the Financial Conduct Authority (FCA) in the United Kingdom with **FRN 586466**. Our Company number is **08061368** and our registered office is Acre House, 11-15 William Road, London NW1 3ER, UK."
  - URL: https://www.darwinex.com/legal/terms-conditions
- La tabla de spreads/forex citada abajo corresponde a la entidad **Darwinex UK / FCA** (`selectedRegulatedEntity=dx_fca`, `pathPrefix=uk`, `regCo="FCA"`).
  - URL: https://www.darwinex.com/forex-cfds/forex?selectedRegulatedEntity=dx_fca&defaultRegulatedEntity=dx_fca&pathPrefix=uk
- **No se encontró** en fuentes oficiales ningún producto "Darwinex Zero" con condiciones de ejecución separadas. La palabra "Zero" en /trading/platforms aparece solo como "ZeroMQ". → **UNKNOWN** si "Zero" es un producto/pricing distinto; todo lo siguiente aplica a la **cuenta live de trading CFD estándar** (FX/CFDs) bajo Tradeslide (FCA).

## 1. Plataformas y conectividad

Fuente: https://www.darwinex.com/trading/platforms y https://help.darwinex.com/metatrader-on-mac-and-linux

- Plataformas de trading: **MetaTrader 4, MetaTrader 5, TradingView, DXtrade** (FX/índices/commodities CFD). Stocks/ETFs en MT5 (selección limitada en MT4).
- Cita (overview): "Forex, Indices and Commodities CFDs can be traded on TradingView, MetaTrader 4/5, and DXtrade. Stocks and ETFs are available on MetaTrader 5, with a limited selection also supported on MetaTrader 4."
- **FIX API**: "We also have a **FIX API trading offer**." (help.darwinex.com/metatrader-on-mac-and-linux). Conectividad FIX v4.4 — módulos oficiales en Darwinex Labs.
- Conectividad/infra: "Darwinex servers are X-connected to our liquidity providers at the London Equinix LD4 Data Centre." ("no last look" LP + proveedor de liquidez en alta volatilidad; agregador propietario).
- API (DARWIN API): acceso a datos/estrategias DARWIN, no es la vía de ejecución de FX/CFDs. Repos oficiales: https://github.com/darwinex/DarwinexLabs
  - "FIX v4.4 Pricing & Trading Modules (in Python)"
  - "ZeroMQ-enabled Python to MetaTrader Bridge (in Python)"
  - "ZeroMQ-enabled MetaTrader Server EA (in MQL)"
  - "DARWIN API Wrappers in Python & R"
  - Cita (README): "We offer traders a range of platforms, **access to our liquidity via FIX** and a proprietary API offering (DARWIN API)..."
- TradingView/DXtrade comparten un único tipo de cuenta (help: tradingview).

## 2. Automatización / Expert Advisors (EAs)

- **No existe página oficial dedicada a "Expert Advisor / política de trading automatizado"** en help.darwinex.com. → **UNKNOWN/ausencia de documento específico**.
- Evidencia indirecta oficial de que la ejecución automatizada es soportada vía plataformas:
  - MT4/MT5 son las plataformas nativas de MetaQuotes (MQL4/MQL5) → EAs y scripts nativos.
  - Darwinex Labs publica un **"ZeroMQ-enabled MetaTrader Server EA (in MQL)"** (EA oficial que publica datos/ejecuta órdenes desde Python). URL: https://github.com/darwinex/DarwinexLabs
  - Sección oficial "Algorithmic Trading" en help (guías de Zorro, Python R&D, costes de transacción para backtesting).
  - Cita (README ZeroMQ bridge): "...interfacing with MetaTrader 4 for trade execution and management."
- **UNKNOWN**: no hay declaración oficial sobre restricciones específicas de uso de EAs en cuenta live (p. ej., velocidad, número de órdenes). No se afirma ni se niega en las fuentes inspeccionadas.

## 3. Cuenta demo (virtual)

Fuente: https://help.darwinex.com/open-and-use-demo-metatrader-accounts

- "Learn to create and use demo Metatrader (MT4 / MT5) accounts."
- "For regulatory reasons, demo accounts cannot be opened for clients with tax residence in Spain."
- Apertura: sección "Trading" → "Open an Account" → "OPEN DEMO ACCOUNT" (o página "Open demo trading account").
- Saldo inicial fijado en la apertura; "You cannot add funds to a demo trading account after it has been created."
- Expiración: "Demo accounts are automatically cancelled only if you don't log into them for 20 days. Once cancelled, they cannot be restored."
- Se pueden abrir tantas cuentas demo como se necesite.

## 4. EURGBP — especificación exacta (cuenta live, entidad FCA/UK)

Fuente primaria (machine-readable, misma tabla que renderiza la web):
`GET https://www.darwinex.com/graphics/spreads?dx_platform=DX` → objeto `forex[]`, `asset == "EURGBP"`.
URL visual: https://www.darwinex.com/forex-cfds/forex (tab "Currencies / Forex", entidad Darwinex UK).

Valores crudos recuperados 2026-11-05:

| Campo | Valor EURGBP | Interpretación |
|---|---|---|
| asset / assetContract | EURGBP | ticker |
| description | EUR/GBP | |
| type | CFD_FX | |
| spreadAverage | "0.55" | spread medio indicativo (pips; variable, no fijo) |
| commission | 2.5 | por orden, 1 contrato, en divisa base (EUR) |
| investorCommission | 1.0 | por orden (cuenta inversor) |
| margin (Professional) | 1.0 | 1.00 % (= 100:1) |
| marginRetail (Retail) | 3.33 | 3.33 % (= 30:1) |
| minSize | 0.01 | tamaño mínimo 0.01 contrato (= 0.01 lote) |
| contractSize | 100000 | 1 contrato = 100,000 unidades base (EUR) |
| tickSize | 1e-5 | 0.00001 (5º decimal) |
| tickValue | 10 | valor pip = 10 GBP por 1 contrato |
| currency | GBP | divisa cotizada |
| swapLong | -5.2 | swap por 1 contrato, en GBP |
| swapShort | 1.1 | swap por 1 contrato, en GBP |
| tripleSwapDay | 4 | índice 0=Domingo → 4=Miércoles |
| rolloverSwap | 1 | ver nota UNKNOWN abajo |
| timezone | America/New_York | horarios en hora de Nueva York |
| opentime | 17:05:00 | Apertura (Domingo) |
| opentimeWeekday | 17:04:01 | Apertura entre semana |
| closetimeWeekday | 16:59:50 | Cierre entre semana |
| closetime | 16:55:00 | Cierre (Viernes) |
| platforms | MT4/MT5 | |
| sellShortAvailable | true | venta en corto disponible |

### 4.1 Disponibilidad exacta de EURGBP
- EURGBP está listado explícitamente en la tabla oficial de FX. Darwinex declara **42 pares FX** (help: assets-available). ✓ Disponible.

### 4.2 Tamaño mínimo
- `minSize = 0.01` contratos = **0.01 lote** (= 1,000 EUR nominal). Encabezado de columna: "Min. size (contracts)".

### 4.3 Spread
- Variable (no fijo). `spreadAverage = 0.55` pips (indicativo). La columna "Current spread" de la web se rellena en vivo desde bid/ask (fxblue), por lo que no es un valor estático garantizado.
- Cita help/execution-costs: "Spread is the difference between the BID and the ASK price... a reduced spread means a higher level of liquidity."

### 4.4 Comisión
- "Commission per order (1 Contract)" = **2.5 EUR por orden** → **5 EUR round-trip por lote** (≈0.005% del nominal en divisa base).
- Cita help/execution-costs: "the gross commission would be around 0.005% of the trade's nominal value in the base currency... 1 lot EURUSD = 100.000 € ... total round-trip cost would be 5€ (commissions are displayed per order, a trade would be composed of 2 orders: entry order and close order). Execution commissions will be charged in the base currency of the pair..."
- Diferencias MT4 vs MT5 en cobro de comisión (help: differences-between-mt4-and-mt5): "Commission MT4 => Roundtrip (100% applied at the entry) MT5 => 50% applied at the entry and 50% at the exit."
- Cláusula de comisión mínima: "Darwinex reserves the right to charge 0.01 of the account's base currency on the opening of positions and on the application of swaps when, as a result of the position's size, the commission or swap due would be less than 0.01."

### 4.5 Swaps / financiación y triple rollover
- Definición (help/execution-costs): swap/rollover = coste/abono por posición abierta overnight, diferencia de tipos interbancarios base vs cotizada; "swaps are not symmetrical since our liquidity providers may apply a markup"; "daily swap rates are subject to change and may vary each day".
- EURGBP: **swap Long (compra) = −5.2 GBP/día**; **swap Short (venta) = +1.1 GBP/día** (por 1 contrato = 1 lote).
- Momento de cargo (pie de tabla web): "**Swap rates may change without prior notice. Swaps are charged daily at 17:00 NY City time. Wednesday swaps are charged in triple size.**"
- Confirmación machine-readable: `tripleSwapDay = 4` (Miércoles) para EURGBP.
- Excepción general (no aplica a EURGBP): USDCAD cobra triple en **jueves** (`tripleSwapDay=5`); NZD pairs cierran 1 min a las 7:00 hora NZ.
- Cláusula de ajuste (pie de tabla): los swaps mostrados son "the indicative amounts of the liquidity provider for the end of the day"; Darwinex se reserva el derecho de modificarlos al aplicarlos si difieren sustancialmente de lo publicado.
- **UNKNOWN**: el campo `rolloverSwap` (EURGBP = 1; USDCAD = 3; USDSGD = 2) se muestra en la web como "Swap Rollover … day/s" sin documentación que explique su semántica exacta. Se reporta el valor crudo; no se interpreta.

## 5. Horarios (trading hours)

- EURGBP (entidad FCA): Apertura **Domingo 17:05 (NY)**; entre semana **17:04:01–16:59:50 (NY)**; cierre **Viernes 16:55 (NY)**. Timezone de la tabla: **New York**.
- Hora del servidor MetaTrader (help/metatrader-time): "Time in MetaTrader terminals is set to New York Close. When connecting to a Darwinex MT4/MT5 account, the respective terminal will display GMT +3 charts during US summertime and GMT +2 charts when DST ends in the US. Time is set on our MetaTrader server and cannot be modified."
- Implicación para barras diarias: el límite de día (cierre New York, 17:00 NY) es el criterio que fija la barra diaria y el momento del swap/triple rollover. La "hora" diaria del swap coincide con el cierre New York (17:00 NY), no con medianoche UTC.

## 6. Universo FX (contexto)

- help/assets-available: "We currently offer 42 currency pairs. For retail clients, the maximum leverage is 30:1 for major currency pairs with all other pairs having a maximum leverage of 20:1... Professional Client... up to 200:1."
- **DISCREPANCIA a señalar**: el artículo (más antiguo) dice 20:1 (5%) para pares no-major; sin embargo la tabla live actual devuelve `marginRetail = 3.33%` (30:1) para EURGBP. La tabla machine-readable es la autoritativa para EURGBP. No se resuelve aquí; se reporta la diferencia.

## 7. Resumen de URLs oficiales usadas

- https://www.darwinex.com/forex-cfds/forex (tabla FX/CFDs, entidad FCA)
- https://www.darwinex.com/graphics/spreads?dx_platform=DX (JSON machine-readable de la misma tabla)
- https://www.darwinex.com/trading/platforms (plataformas/conectividad/FIX)
- https://github.com/darwinex/DarwinexLabs (FIX v4.4, ZeroMQ bridge, Server EA, DARWIN API)
- https://www.darwinex.com/legal/terms-conditions (entidad Tradeslide, FCA FRN 586466)
- https://help.darwinex.com/open-and-use-demo-metatrader-accounts
- https://help.darwinex.com/open-and-use-live-metatrader-accounts
- https://help.darwinex.com/metatrader-time
- https://help.darwinex.com/execution-costs
- https://help.darwinex.com/differences-between-mt4-and-mt5
- https://help.darwinex.com/assets-available
- https://help.darwinex.com/metatrader-on-mac-and-linux
- https://help.darwinex.com/swaps-xtiusd-xngusd (nota "3-days swap" / Wednesday)

## 8. BLOCKING / UNKNOWN

1. **"Darwinex Zero"**: no existe página oficial de condiciones de ejecución separadas para un producto "Zero". Todo lo anterior es cuenta live CFD estándar (Tradeslide/FCA). Si el target es "Zero", las condiciones específicas son **UNKNOWN**.
2. **Política explícita de Expert Advisors / trading automatizado en cuenta live**: no hay documento oficial dedicado → **UNKNOWN**. (EAs soportados de facto vía MT4/MT5 + Server EA oficial de Darwinex Labs.)
3. **Semántica del campo `rolloverSwap`** ("Swap Rollover" = "1 day/s" para EURGBP): no documentada → **UNKNOWN** (se reporta valor crudo).
4. **Margen retail de EURGBP**: tabla live (3.33%) difiere del texto general de help (20:1 para no-majors) → discrepancia no resuelta; la tabla es la fuente autoritativa.
5. **Spread exacto en el momento de una orden**: variable y "Current spread" es en vivo; `spreadAverage=0.55` es solo indicativo. Para economía por operación hay que capturar bid/ask en el instante (fuera de alcance sin credenciales).
