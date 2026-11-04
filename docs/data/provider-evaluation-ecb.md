# Evaluación de proveedor: Banco Central Europeo (euro foreign exchange reference rates)

- Fecha de consulta y verificación: 2026-11-04
- Resultado: **APROBADO BAJO LICENCIA PERMISIVA — con restricción de producto (frecuencia diaria, FX, sin bid/ask)**
- Alcance: euro foreign exchange reference rates (fixings diarios frente al euro, ~30 monedas, desde 1999)
- Regla: lo no autorizado explícitamente se considera bloqueante

Esta evaluación técnica de derechos no sustituye asesoría jurídica. No se usaron credenciales;
la descarga es pública y sin autenticación.

## Conclusión ejecutiva

La política de copyright del BCE concede "free use of the information obtained directly from
it" con tres condiciones (citar fuente, declarar la disponibilidad gratuita si se vende y
declarar modificaciones). A diferencia de Deriv, Dukascopy, Binance y Alpha Vantage, aquí no
hay prohibición de construir/almacenar bases de datos, no hay TTL, no se restringe el uso
comercial y no hay obligación de borrado. Es la **primera fuente de la shortlist que supera
la licencia** para almacenamiento, derivados y uso comercial.

La restricción no es legal, es de producto: los datos son **fixings diarios de tipo de cambio
de referencia** (no ticks ni intradía) y son precios de referencia (sin spread bid/ask), con
la advertencia "for information purposes only; using the rates for transaction purposes is
strongly discouraged". Por tanto habilitan una estrategia FX de frecuencia diaria con costos
modelados, no la estrategia de opciones binarias por ticks explorada con Deriv.

## Fuentes oficiales verificadas

1. Disclaimer & Copyright (política de reproducción):
   https://www.ecb.europa.eu/services/disclaimer/html/index.en.html
   - SHA-256 del HTML: `971b969fd06a2b7ef9a34558a162425fb7987e896350ff595a011d770c226364`
   - Tamaño: 107792 bytes
   - La página no publica número de versión ni fecha efectiva; exige revisión continua.
2. Página de euro reference rates:
   https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html
   - SHA-256 del HTML: `2bb9ff19dfc13855ed40e173d7ddf1c00d0fe6b41a0e66ee396dfc4a50489432`
   - Tamaño: 119491 bytes
3. Serie histórica CSV (descarga directa, sin autenticación):
   https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip
   - SHA-256: `971a5cbf650f9e96663cf1218801c3054249e2bb57070d427db5a44931393f59`
   - Tamaño: 642539 bytes
4. Última referencia CSV:
   https://www.ecb.europa.eu/stats/eurofxref/eurofxref.zip
   - SHA-256: `42c97a9a02cf34eb2599e1634b5b9e289434802d853f5143e37be55b7180ee55`
   - Tamaño: 393 bytes

Los archivos de revisión se mantuvieron únicamente en `/tmp`; la licencia permite conservar el
CSV de forma persistente si el proyecto lo aprueba (ver matriz).

## Evidencia textual determinante

Cláusula de copyright (reproducción y redistribución):

> "Copyright © for the entire content of this website: European Central Bank, Frankfurt am
> Main, Germany. Subject to the exception below, users of this website may make free use of
> the information obtained directly from it subject to the following conditions:"

> "When such information is distributed or reproduced, it must appear accurately and the ECB
> must be cited as the source."

> "Where the information is incorporated in documents that are sold (regardless of the
> medium), the natural or legal person publishing the information must inform buyers, both
> before they pay any subscription or fee and each time they access the information taken from
> this website, that the information may be obtained free of charge through this website."

> "If the information is modified by the user (e.g. by seasonal adjustment of statistical data
> or calculation of growth rates) this must be stated explicitly."

La excepción ("documents that bear the name of their authors, such as ECB Working Papers and
ECB Occasional Papers") exige autorización escrita, pero aplica a publicaciones con autor
nombrado, **no** a los datos de reference rates (datos estadísticos publicados por el BCE).

Advertencia de naturaleza (no es restricción de licencia):

> "The reference rates are published for information purposes only. Using the rates for
> transaction purposes is strongly discouraged."

> "the euro foreign exchange reference rates ... are based on sources which the ECB considers
> to be reliable, the ECB accepts no responsibility or liability for any ... economic loss or
> any indirect or consequential loss or damage ... in connection with the ECB publishing the
> rates."

## Características de los datos

- Frecuencia: diaria (días hábiles TARGET), actualización ~16:00 CET; concertación ~14:10 CET.
- Cobertura: ~30 monedas cotizadas contra el euro (USD, GBP, JPY, CHF, AUD, CAD, etc.).
- Histórico: desde 1999-01-04 (≈27 años), con monedas pre-euro en `N/A` y RUB discontinuado.
- Formato: CSV (columnas `Date` + monedas), también XML y SDMX-ML.
- Naturaleza: fixing de referencia (mid-point), sin spread bid/ask ni costos de ejecución.

## Matriz de derechos

| Criterio | Evidencia | Estado |
|---|---|---|
| Almacenamiento histórico | "free use of the information obtained directly"; sin TTL ni prohibición de bases de datos | **PERMITIDO** |
| Derivados (features/modelos/métricas) | Modificación permitida con declaración explícita; atribución requerida | **PERMITIDO (con atribución)** |
| Uso comercial | Contempla expresamente "documents that are sold"; condición de informar que es gratuito | **PERMITIDO (con aviso)** |
| Redistribución | Permitida con cita al BCE y exactitud | **PERMITIDO (con atribución)** |
| Automatización | Sin restricción expresa; el CSV se descarga directo (no requiere scraping) | **PERMITIDO (descarga directa)** |
| Bid/ask, payout, costos | No disponibles; fixing de referencia sin spread | **NO APLICA (modelar costos)** |
| Granularidad intradía/tick | No existe; solo diaria | **RESTRICCIÓN DE PRODUCTO** |
| Acceso reproducible | URL estable de CSV con hash; histórico completo desde 1999 | **PERMITIDO** |
| Terminación/borrado | Sin obligación de borrado en la política de copyright | **SIN OBLIGACIÓN** |
| Jurisdicción | BCE (UE); sin restricción geográfica para el uso de datos | **PERMITIDO** |

## Decisión

El BCE es una fuente **aprobable** bajo licencia permisiva para una estrategia FX de
frecuencia diaria. Es la primera fuente de la shortlist que desbloquea el `QUOTE_REPLAY_BACKTEST`
con datos observados y derechos compatibles, sin licencia comercial ni contrato escrito.

No desbloquea una estrategia de ticks/opciones: para eso no existe fuente permisiva y se
mantiene el bloqueo (o se requiere una licencia comercial tipo Twelve Data).

## Requisitos operativos al adoptar

1. `DataRightsManifest` con `source_kind=LICENSED_EXTERNAL`, `license_url` al disclaimer del BCE,
   `retention_seconds` persistente y atribución registrada.
2. Atribución al BCE y declaración de modificaciones en todo derivado distribuido.
3. Si se vende un producto que incorpore los datos, informar que están disponibles gratis en el BCE.
4. Modelar costos de transacción (spread/slippage) sobre el fixing de referencia; no tratar el
   fixing como precio ejecutable ("for information purposes only").
5. Re-verificar periódicamente la política de copyright (la página no está versionada).

## Qué cambiaría la decisión

Nada en la licencia para el uso diario-FX descrito. Un cambio del BCE en su política de
copyright, o un intento de usar los fixings como precios ejecutables de opciones, requeriría
re-evaluación.
