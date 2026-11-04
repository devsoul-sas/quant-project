# Evaluación de proveedor: Junta de Gobernadores de la Reserva Federal (H.10 Foreign Exchange Rates)

- Fecha de consulta y verificación: 2026-11-04
- Resultado: **APROBADO BAJO DOMINIO PÚBLICO — con restricción de producto (frecuencia diaria, USD base, sin bid/ask)**
- Alcance: H.10 "Foreign Exchange Rates" (noon buying rates diarios contra el USD, ~30 monedas, desde 1971)
- Regla: lo no autorizado explícitamente se considera bloqueante

Esta evaluación técnica de derechos no sustituye asesoría jurídica. No se usaron credenciales;
la descarga es pública y sin autenticación.

## Conclusión ejecutiva

La Junta de Gobernadores de la Reserva Federal declara, en su aviso oficial de copyright,
que "la información del sitio web del Board está en el dominio público y puede copiarse y
distribuirse sin permiso", pidiendo únicamente citar al Board como fuente. Al ser una obra del
gobierno federal de EE.UU., sus publicaciones carecen de protección de copyright (17 U.S.C.
§ 105). Es la licencia más limpia posible de toda la shortlist: más permisiva que el BCE
(que exige tres condiciones de atribución/aviso) y sin las restricciones de Deriv, Dukascopy,
Binance o Alpha Vantage.

Es una fuente **independiente** del BCE: fixing de la Reserva Federal de Nueva York (noon
buying rates en Nueva York, certificados a efectos aduaneros) frente a los fixings del BCE
(concertación ~14:10 CET, publicados ~16:00 CET). Sirve como segunda fuente para contrastar
la señal de mean-reversion observada en EURGBP sin depender de un único fixing.

La restricción es de producto, no legal: los datos son **diarios** (no ticks) y son precios de
referencia sin spread bid/ask. No desbloquean ticks/opciones.

## Fuentes oficiales verificadas

1. Disclaimer y copyright del Board (declaración de dominio público):
   https://www.federalreserve.gov/disclaimer.htm
   - SHA-256 del HTML: `b6c5edb9ac87c102968d2b5aad4ed315d0c9c7a754262041d707b74e8ce2ff86`
   - Tamaño: 85306 bytes
2. Página "About" del H.10 (naturaleza de los datos):
   https://www.federalreserve.gov/releases/h10/about.htm
   - SHA-256 del HTML: `2662b50c9e669f709d904489eaf0fd40e8066167538c84105682ec45e0586823`
   - Tamaño: 85020 bytes
3. Histórico H.10 (índice): https://www.federalreserve.gov/releases/h10/hist/default.htm
   - SHA-256 del HTML: `84af4cdae84c766a4d852f987ef531aeb81de5eb3bb8ab797de1e7285edc8e73`
4. Serie histórica GBP (dat00_uk.htm) y EUR (dat00_eu.htm):
   - `5edc10c44c078d118c9886865e5272bb5a68b3fa8b77c4202a583f45bf9516cd` (UK)
   - `e929a43cf99b131389759a3c23fdf0632bf28b6f474c25666dd6bb482521564c` (EUR)
   - ~1.13 MB cada uno.

Los archivos de revisión se mantuvieron únicamente en `/tmp`.

## Evidencia textual determinante

Cláusula de dominio público (disclaimer del Board):

> "Copyright/trademark — Unless otherwise indicated, information on Board's website is in the
> public domain and may be copied and distributed without permission. Please cite to the Board
> as the source of the information."

> "For any photo, graphic, or other material that is identified as being associated with a
> non-Board (such as materials with a copyright or trademark) permission to copy and distribute
> such photo, graphic, or material must be obtained from the non-Board source."

> "The use of the Board seals, logos and other official insignia is protected by federal law and
> may not be used or reproduced without the Board's written permission."

Marco legal: 17 U.S.C. § 105 — "Copyright protection under this title is not available for any
work of the United States Government." La Reserva Federal es una agencia del gobierno de EE.UU.

Naturaleza de los datos (H.10 "About"):

> "The H.10 weekly release contains daily rates of exchange of major currencies against the
> U.S. dollar. The data are noon buying rates in New York for cable transfers payable in the
> listed currencies. The rates have been certified by the Federal Reserve Bank of New York for
> customs purposes."

## Características de los datos

- Frecuencia: diaria (noon buying rates, Nueva York); histórico desde 1971 (~55 años).
- Base: USD (unidades de moneda extranjera por USD, o USD por moneda según convención).
- Cobertura: GBP, EUR, JPY, CHF, CAD, AUD y ~20 monedas más.
- Formato: HTML por moneda (dat00_XX.htm) + Data Download Program (CSV/XML) sin autenticación.
- Naturaleza: fixing de referencia (mid-point), sin spread bid/ask ni costos de ejecución.
- Independencia: fixing de Nueva York (EE.UU.) vs fixing del BCE (UE); fechas y horas distintas.

## Matriz de derechos

| Criterio | Evidencia | Estado |
|---|---|---|
| Almacenamiento histórico | Dominio público ("may be copied and distributed without permission") | **PERMITIDO** |
| Derivados (features/modelos/métricas) | Dominio público; sin restricción de modificación | **PERMITIDO** |
| Uso comercial | Dominio público; sin restricción | **PERMITIDO** |
| Redistribución | "copied and distributed without permission"; cita al Board como fuente | **PERMITIDO (citar)** |
| Automatización | Descarga directa (HTML/DDP), sin autenticación ni prohibición | **PERMITIDO** |
| Bid/ask, payout, costos | No disponibles; noon buying rate de referencia | **NO APLICA (modelar costos)** |
| Granularidad intradía/tick | No existe; solo diaria | **RESTRICCIÓN DE PRODUCTO** |
| Acceso reproducible | URL estable, sin auth; histórico completo desde 1971 | **PERMITIDO** |
| Terminación/borrado | Dominio público; sin obligación de borrado | **SIN OBLIGACIÓN** |
| Jurisdicción | EE.UU.; dominio público global (17 U.S.C. § 105) | **PERMITIDO** |

## Decisión

El H.10 de la Reserva Federal es una fuente **aprobable** bajo dominio público para una
estrategia FX de frecuencia diaria, con la licencia más limpia de la shortlist. Es la segunda
fuente independiente (tras el BCE) que habilita `QUOTE_REPLAY_BACKTEST` con datos observados.
Su papel principal es la **validación cruzada** de la señal EURGBP: la serie EURGBP derivada
del fixing de Nueva York (USD/GBP y USD/EUR) es independiente del fixing del BCE.

No desbloquea ticks/opciones; se mantiene el bloqueo para esa vía (o se requiere licencia
comercial tipo Twelve Data).

## Requisitos operativos al adoptar

1. `DataRightsManifest` con `source_kind=OPEN_LICENSE`, `license_url` al disclaimer del Board,
   `retention_seconds` persistente y atribución registrada ("Federal Reserve Board (H.10)").
2. Citar al Board como fuente en todo derivado distribuido (requisito del aviso).
3. No usar los sellos/logos del Board (protegidos por ley federal).
4. Modelar costos de transacción sobre el noon buying rate; no tratarlo como precio ejecutable.
5. Derivar EURGBP como cross de USD/GBP y USD/EUR, documentando la convención de cómputo.

## Qué cambiaría la decisión

Nada en la licencia para el uso diario-FX descrito. Solo materiales de terceros señalados en el
sitio (fotos/gráficos con copyright de no-Board) quedan fuera del dominio público; los datos H.10
no son de terceros. No hay restricción de redistribución, comercialización ni automatización.
