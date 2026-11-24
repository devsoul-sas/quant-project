# Evaluación formal de Darwinex como venue de ejecución EURGBP

- Fecha de consulta: 2026-11-05
- Estado: **NOT APPROVED** (`NINGUNO APROBADO` permanece)
- Alcance: broker spot/CFD FX, admisión de residente colombiano, EURGBP, economía
  ejecutable completa y derechos de persistencia/derivados para investigación comercial

`UNKNOWN/BLOCKING` significa falta de evidencia oficial suficiente; no afirma que la
actividad esté prohibida.

## Distinción crítica: entidades separadas

La marca Darwinex opera sobre **cuatro entidades distintas**, y confundirlas invalida la
evaluación:

1. **Tradeslide Technologies Ltd** (Reino Unido, n.º 14398381) — opera el dominio
   `darwinexzero.com` (Darwinex Zero). Es una **capa de track-record sobre capital
   virtual**, no un venue de ejecución. Ver
   [execution-venue-darwinex-zero.md](execution-venue-darwinex-zero.md).

2. **Tradeslide Trading Tech Ltd** (Reino Unido, n.º 08061368) — el broker FCA bajo
   **FRN 586466** ("Darwinex UK"). Su `Client Agreement` y el `DARWIN API T&C` **prohíben
   expresamente** la redistribución del dato (9.1(d)) y exigen consentimiento previo
   escrito para herramientas de trading automático (9.6). Ver
   [darwinex-api-market-data-terms.md](darwinex-api-market-data-terms.md).

3. **TRADESLIDE GLOBAL LTD** (Seychelles, n.º 8433817-1) — el broker regulado por la
   Financial Services Authority (FSA) de Seychelles bajo **licencia SD171** ("Darwinex
   Global"). Firma el `Client Services Agreement` (`client-services-agreement-global.pdf`).
   Un tercero, Tradeslide Trading Tech Ltd (FCA FRN 586466), figura como afiliado al que se
   pueden externalizar funciones (cláusula 1.3 del CSA).

4. **Sapiens Markets EU, Sociedad de Valores SA** (España, CNMV n.º 311) — "Darwinex EU".
   No se ofrece para residentes fiscales de Colombia.

Para Colombia, el formulario de registro ofrece **dos** entidades: "Darwinex UK" (FCA) y
"Darwinex Global" (FSA Seychelles); no ofrece "Darwinex EU". Esta evaluación se centra en
la ruta Global (**TRADESLIDE GLOBAL LTD, SD171**); la ruta UK se cubre en
[darwinex-api-market-data-terms.md](darwinex-api-market-data-terms.md).

## Matriz de gates

| Gate | Hallazgo | Veredicto |
|---|---|---|
| Admisión Colombia | "Colombia" aparece como opción de "Country of tax residence"; el selector ofrece "Darwinex UK" (FCA) y "Darwinex Global" (Seychelles), no EU. Lista de aplicación ≠ aprobación garantizada (cláusula 3.5: la eligibilidad se determina tras KYC/due diligence) | CONDITIONAL |
| Producto/par | Tabla oficial de spreads lista `EURGBP` (spread 0.7 pips, contrato 100 000 EUR, pip value 10 GBP, comisión 2.5 EUR por orden, swap long −5.20 GBP, swap short +1.10 GBP) | PROVED (par y economía publicada) |
| Demo/paper | Documentación oficial "How to open and use demo trading accounts" (MT4/MT5) + página "plataforma virtual, no una demo" de Zero | PROVED (demo MT4/MT5 disponible) |
| Automatización | Cláusula 12.6 reconoce explícitamente "expert advisor"; página Zero lista EAs (MT4/MT5) y Pine Script (TradingView) | PROVED (EA permitido, bajo descargo de responsabilidad) |
| Datos históricos/retorno | El CSA (cláusula 2.2.d) califica el dato histórico como no predictivo, pero **no concede** derecho a extraer/persistir/redistribuir | UNKNOWN/BLOCKING |
| Extracción/API | No hay API pública de mercado documentada para descargar/retener histórico bid/ask; MT4/MT5 es el canal. Derechos de retención no especificados | UNKNOWN/BLOCKING |
| Derivados/backtest | El CSA no cubre licencia para retener features/modelos/backtests derivados con fines comerciales | UNKNOWN/BLOCKING |
| Redistribución/comercial | No hay cláusula que autorice redistribución del feed; los términos Zero (cláusula 3.5) prohíben "systematic extraction" del sitio | UNKNOWN/BLOCKING |

## Economía publicada (EURGBP, entidad Global, fuente oficial 2026-11-05)

Tabla oficial de spreads de la entidad Global (`https://www.darwinex.com/global/...` →
"Forex & CFDs Overview" → fila `EURGBP`):

| Campo | Valor |
|---|---|
| Spread actual | 0.7 pips |
| Tamaño de contrato | 100 000 EUR |
| Pip value (1 contrato) | 10 GBP |
| Swap long (1 contrato) | −5.20 GBP |
| Swap short (1 contrato) | +1.10 GBP |
| Rollover | 1 día (miércoles ×3) |
| Comisión por orden (1 contrato) | 2.5 EUR |

Lectura de costos a 5 observaciones (7 días calendario, ~5 sesiones de rollover
efectivas + triple rollover de miércoles), convertido a pips GBP con spot ~0.833:

- Comisión round-trip ≈ 2.5 EUR ×2 = 5 EUR ≈ 0.42 pips.
- **Posición larga (long) ≈ 0.7 + 0.42 + 3.64 ≈ 4.76 pips** (swap es costo neto negativo).
- **Posición corta (short) ≈ 0.7 + 0.42 − 0.77 ≈ 0.35 pips** (swap es crédito neto).

Esto es `ESTIMATED` y orientativo: no incorpora slippage, horarios exactos de
entrada/salida ni el carácter variable del spread ("may change without prior notice").
No debe tratarse como una especificación de costo congelada.

## Datos de mercado y retención: el bloqueo central

- El CSA no incluye un anexo de market-data/licencia de uso que autorice almacenar el
  histórico bid/ask, construir un corpus, retener features/modelos derivados ni
  redistribuir el feed.
- La cláusula 12.6 permite el uso de un EA, pero bajo "as is" y descargo de
  responsabilidad; **no** es una licencia de datos de mercado.
- Los términos de Darwinex Zero (cláusulas 1.2.2 y 3.5) restringen la reproducción y la
  extracción sistemática del contenido del sitio.

Consecuencia: acceder al producto y publicar spreads no equivale a derecho de retención
reproducible. El proyecto exige persistencia local de bid/ask OBSERVED y derivados para
investigación potencialmente comercial; **nada en las fuentes oficiales concede ese
derecho por escrito**.

## Conclusión

**NOT APPROVED.** Darwinex Global (TRADESLIDE GLOBAL LTD, FSA SD171):

- **Sí** admite a Colombia como opción de registro bajo la entidad Global (CONDITIONAL:
  sujeta a KYC/due diligence, cláusula 3.5).
- **Sí** lista `EURGBP` con economía publicada (spread/swap/comisión/rollover).
- **Sí** dispone de cuentas demo MT4/MT5 y soporta Expert Advisors.
- **No** concede por escrito derechos de retención/extracción de histórico bid/ask,
  persistencia de derivados/features/modelos, ni redistribución comercial.

Faltan exactamente dos evidencias para desbloquear:

1. un **market-data / API supplement** oficial (o confirmación escrita) que autorice
   almacenar histórico bid/ask EURGBP y retener derivados/backtests para investigación
   comercial; y
2. confirmación de que el fill simulado en demo reproduce slippage/latencia/depth
   comparables a producción (la página Zero dice "slippage, latencia y volatilidad" pero
   no hay especificación de equivalencia de fill).

Hasta obtenerlas, Darwinex Global permanece `UNKNOWN/BLOCKING` en datos y no es venue
aprobado. El holdout permanece sellado (BCE). No se abren cuentas, no se conservan
payloads y no se opera.

## Fuentes oficiales consultadas (2026-11-05)

- `https://www.darwinex.com/global/` — selector de entidad (UK / EU / Global) y oferta.
- `https://www.darwinex.com/global/legal/terms-conditions` — terms of use (iframe FCA).
- `https://www.darwinex.com/global/legal/service-agreement` — `Client Services Agreement`
  (PDF `client-services-agreement-global.pdf`, CloudFront `d139oolcsxoepg.cloudfront.net`).
- `https://www.darwinex.com/forex-cfds/forex` — tabla de spreads/swaps/comisión (fila EURGBP).
- `https://www.darwinex.com/register` — formulario: "Country of tax residence" incluye
  "Colombia"; selector de entidad muestra "Darwinex Global".
- `https://help.darwinex.com/open-and-use-demo-metatrader-accounts` — demo MT4/MT5.
- `https://help.darwinex.com/assets-transaction-costs-in-zorro-for-algorithmic-trading` —
  costos de transacción para algorithmic trading (Zorro/AssetsFix).
- `https://help.darwinex.com/quant-workflow-algorithmic-trading-strategy-rd-in-python` —
  workflow cuantitativo en Python.
- `https://www.darwinexzero.com/es/activos` — "plataforma virtual, no una demo".
- `https://www.darwinexzero.com/es/plataformas-de-trading` — TradingView / MT4 / MT5.

## Registro de hash (artefactos efímeros, no versionados)

| Archivo | SHA-256 |
|---|---|
| client-services-agreement-global.pdf | 29ea7c211a98e8d217e75d7892ed181598e6537caa9d6c235b558304ab3e84de |
| terms-fca.pdf | e45b17a1c38265bb0e7c347c1bc12dbc73587e63bd6144b181fad3105fa4c5d4 |

Los PDF se conservan solo en `/tmp/darwinex-dd/` con fines de verificación de cláusulas;
no entran en Git y no contienen cotizaciones de mercado.
