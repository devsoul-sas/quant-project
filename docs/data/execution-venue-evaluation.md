# Evaluación de venues de ejecución EURGBP

- Fecha de consulta: 2026-11-05
- Estado: **NINGUNO APROBADO**
- Alcance: spot/CFD FX, API demo/paper, residente en Colombia, EURGBP y economía
  ejecutable reproducible

`UNKNOWN/BLOCKING` significa falta de evidencia oficial suficiente; no afirma que la
actividad esté prohibida.

## Criterios obligatorios

1. admisión verificable de un residente colombiano bajo la entidad evaluada;
2. API demo/paper para EURGBP;
3. spread, comisión, slippage y financiación long/short —incluido triple rollover—;
4. derechos para investigación local, persistencia y derivados;
5. semántica ejecutable compatible con ADR-010.

## Matriz

| Venue | Colombia | Demo/paper API | EURGBP | Economía | Datos/derivados | Veredicto |
|---|---|---|---|---|---|---|
| IG International | UNKNOWN/BLOCKING | Sí | Sí | spread específico; swap/slippage incompletos | UNKNOWN/BLOCKING | mejor candidato técnico; no aprobado |
| Interactive Brokers | Sí, en lista oficial | Sí, tras cuenta aprobada y financiada | Sí | comisión; rollover/slippage incompletos | BLOCKING para non-display/derivados sin aclaración | no aprobado |
| OANDA | UNKNOWN/BLOCKING para entidad aplicable | Sí | UNKNOWN para esa entidad | financiación BVI no combinable con API v20 excluida allí | UNKNOWN/BLOCKING | no aprobado |
| Darwinex Zero | UNKNOWN/BLOCKING | virtual (capital virtual, mercado real); no es un venue | UNKNOWN (par no confirmado en catálogo) | n/a — no ejecuta | restringe extracción comercial del sitio (3.5) | **NO ES UN VENUE**; capa de track-record/capital |
| Darwinex Global (Tradeslide Global Ltd, FSA SD171) | CONDITIONAL (Colombia en registro; sujeta a KYC, CSA 3.5) | Sí (demo MT4/MT5) | Sí (spread 0.7 pips) | publicada (spread/swap/comisión/rollover) | UNKNOWN/BLOCKING sin licencia de datos | no aprobado (datos) |

## IG International

Evidencia oficial:

- API demo: https://labs.ig.com/gettingstarted
- EURGBP CFD: https://www.ig.com/en/forex/markets-forex/eur-gbp
- fees/product details: https://www.ig.com/en/help-and-support/collections/1114915-fees-and-charges
- cargos generales: https://www.ig.com/en/charges

La tabla EURGBP consultada reporta spread mínimo 0.9 puntos, promedio 1.83 durante
00:00–21:00 y promedio total 2.51; el spread es variable. No se verificaron de forma
completa Colombia, swap long/short, triple rollover, slippage demo ni derechos de
persistencia/derivados. No se retuvieron cotizaciones.

## Interactive Brokers

Evidencia oficial:

- países: https://www.interactivebrokers.com/en/accounts/open-account-country-list.php
- requisitos API: https://www.interactivebrokers.com/docs/tws-api/doc/notes-limitations/requirements
- paper API: https://www.interactivebrokers.com/docs/tws-api/doc/notes-limitations/tws-api-limitations
- EURGBP IDEALPRO: https://www.interactivebrokers.com/docs/tws-api/contracts/fx-pairs
- comisión FX: https://www.interactivebrokers.com/en/pricing/commissions-spot-currencies.php
- términos de market data: https://www.interactivebrokers.com/en/accounts/forms-and-disclosures-market-data.php

Colombia y EURGBP están documentados, pero paper requiere una cuenta IBKR Pro
aprobada y financiada. El acuerdo GFIS 2026-05-01 restringe non-display y derived data
sin consentimiento, y falta resolver el Market Data API Supplement. No se verificó
rollover/triple swap completo ni equivalencia de slippage paper.

## OANDA

Evidencia oficial:

- v20/practice: https://developer.oanda.com/rest-live-v20/introduction/
- guía v20: https://developer.oanda.com/rest-live-v20/development-guide/
- financiación OGM/BVI: https://www.oanda.com/bvi-en/cfds/financing-costs/

La API v20 excluye OANDA Global Markets, mientras la regla de financiación encontrada
pertenece a esa entidad BVI. No se mezclan especificaciones de entidades distintas.
Colombia, EURGBP, spread/slippage y licencia de persistencia siguen sin prueba
suficiente para una misma entidad.

## Darwinex Zero

Darwinex Zero **no es un venue de ejecución**: es una capa de track-record sobre capital
virtual que monitoriza la actividad en un broker subyacente. Ver
[execution-venue-darwinex-zero.md](execution-venue-darwinex-zero.md). Sus términos de uso
restringen la reproducción/almacenamiento del sitio (cláusula 1.2.2) y el uso
comercial/extracción sistemática (cláusula 3.5). La ejecución y los datos de mercado
residen en el broker subyacente (Tradeslide Trading Tech Ltd, FCA FRN 586466, o un Third
Party Broker), cuya admisión colombiana, `EURGBP`, economía y derechos de persistencia
siguen sin evaluar. No resuelve el gate g5.

## Decisión

Ningún venue desbloquea el holdout. Prioridad futura de diligencia:

1. IG International, por cercanía técnica;
2. IBKR, solo si se acepta la condición de cuenta financiada y se obtiene permiso
   para non-display/derivados;
3. OANDA, solo al identificar entidad aplicable a Colombia y API compatible.

Darwinex Zero se evalúa por separado como **capa de monetización** (track-record →
capital inversor), no como venue: no sustituye la necesidad de un broker spot/CFD.

## Darwinex Global (broker subyacente)

El broker real de la ruta "Global" es **Tradeslide Global Ltd** (Seychelles, FSA SD171).
Su [evaluación formal](provider-evaluation-darwinex-global.md) concluye **NOT APPROVED**:
Colombia aparece como opción de registro (CONDITIONAL, sujeta a KYC según CSA 3.5),
`EURGBP` está listado con economía publicada (spread 0.7 pips, swap/comisión/rollover) y
hay demo MT4/MT5 con Expert Advisors, pero **no hay licencia por escrito** para
persistir histórico bid/ask ni derivados con fines comerciales. Bloqueo central en
datos; no desbloquea el holdout.

Mientras tanto, los costos permanecen `ESTIMATED`; no se atribuye economía observada,
no se abren cuentas, no se conservan payloads y no se opera.
