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

## Decisión

Ningún venue desbloquea el holdout. Prioridad futura de diligencia:

1. IG International, por cercanía técnica;
2. IBKR, solo si se acepta la condición de cuenta financiada y se obtiene permiso
   para non-display/derivados;
3. OANDA, solo al identificar entidad aplicable a Colombia y API compatible.

Mientras tanto, los costos permanecen `ESTIMATED`; no se atribuye economía observada,
no se abren cuentas, no se conservan payloads y no se opera.
