# Evaluación de proveedor: Bank of England (daily spot exchange rates)

- Fecha de consulta y verificación: 2026-11-04
- Resultado: **CONDICIONAL / BLOQUEADO — OGL v3.0 con exclusión expresa de "selected exchange rate data"**
- Alcance: daily spot exchange rates against Sterling (4pm London), GBP base
- Regla: lo no autorizado explícitamente se considera bloqueante

Esta evaluación técnica de derechos no sustituye asesoría jurídica. No se usaron credenciales;
la consulta fue pública.

## Conclusión ejecutiva

El Bank of England declara que "la reproducción de los datos de la Database está sujeta a la
UK Open Government Licence, que permite y fomenta la reutilización libre y flexible de los
datos". Sin embargo, acto seguido añade una excepción que impide la aprobación limpia:

> "selected exchange rate data and series are excluded from this licence as they are reproduced
> by the Bank under licence from third parties. In these instances, you are advised to contact us
> directly for permission."

Dado que el objetivo es validar EURGBP con tipos de cambio, y la página de spot rates avisa que
estos "no son tipos oficiales y no son más autoritativos que los de cualquier banco comercial del
mercado de Londres", no está claro si la serie de spot rates diarios está dentro de la OGL o en la
categoría excluida. Por la regla fail-closed del proyecto, esto es **CONDICIONAL**: no se adopta
sin confirmar por escrito que la serie específica (spot rates GBP/EUR, GBP/USD) está bajo OGL v3.0.

No aporta nada sobre el Fed (que es dominio público) ni sobre el BCE (ya aprobado): su único valor
sería una tercera fuente independiente de fijación GBP, que no justifica el riesgo de ambigüedad.

## Fuentes oficiales verificadas

1. Página legal del Bank of England (copyright y licencia de la Database):
   https://www.bankofengland.co.uk/legal
   - SHA-256 del HTML: `9b79559d2d405fedd434281520dcc7a009e924181046644217b6b26949c2c5ad`
   - Tamaño: 79881 bytes
2. Página de daily spot exchange rates:
   https://www.bankofengland.co.uk/boeapps/database/Rates.asp
   - SHA-256 del HTML: `83c563ad0f60bd3296182a514acc553e9cf2b1540c5a5f4014ffa375883e2f23`
   - Tamaño: 40675 bytes

## Evidencia textual determinante

Licencia (página legal):

> "The information made available via the Database is the copyright of the Governor and Company
> of the Bank, unless otherwise stated. Reproduction of data in the Database is subject to the
> terms of the UK Open Government Licence, allowing and encouraging free and flexible data reuse."

Exclusión (misma página):

> "Please note that selected exchange rate data and series are excluded from this licence as they
> are reproduced by the Bank under licence from third parties. In these instances, you are advised
> to contact us directly for permission if you wish to reproduce this information."

Naturaleza de los spot rates (página Rates):

> "The exchange rates are not official rates and are no more authoritative than that of any
> commercial bank operating in the London foreign exchange market."

## Matriz de derechos

| Criterio | Evidencia | Estado |
|---|---|---|
| Almacenamiento histórico | OGL v3.0 para la Database, PERO exclusión de "selected exchange rate data" | **AMBIGUO / CONDICIONAL** |
| Derivados | Depende de la serie; exclusión aplica a "selected exchange rate data" | **AMBIGUO** |
| Uso comercial | OGL permite uso comercial, pero la exclusión lo limita para ciertas series | **AMBIGUO** |
| Redistribución | OGL con atribución, salvo series excluidas | **AMBIGUO** |
| Automatización | Descarga directa (endpoint CSV), sin prohibición expresa | **PERMITIDO** |
| Bid/ask | No disponibles; spot rate de referencia | **NO APLICA** |
| Granularidad | Diaria | **RESTRICCIÓN DE PRODUCTO** |
| Acceso reproducible | Endpoint estable, sin auth | **PERMITIDO** |
| Terminación/borrado | OGL sin obligación de borrado | **SIN OBLIGACIÓN** |
| Jurisdicción | Reino Unido (OGL v3.0) | **PERMITIDO** |

## Decisión

**CONDICIONAL / BLOQUEADO.** La OGL v3.0 es permisiva, pero la cláusula que excluye "selected
exchange rate data and series" (reproducidas bajo licencia de terceros) hace que los spot rates
diarios no puedan adoptarse sin confirmar por escrito que la serie concreta está cubierta por la
OGL. No se descargaron datos de mercado; solo se consultó la página pública.

El Fed (dominio público) cubre la necesidad de una segunda fuente independiente, así que el BoE
queda registrado como opción de tercer fixing, no como dependencia del camino crítico.

## Qué cambiaría la decisión

Una confirmación oficial de que la serie de spot rates diarios (GBP/EUR y GBP/USD) está cubierta
por OGL v3.0 y no entra en la categoría excluida la convertiría en aprobable. Sin esa
confirmación escrita, permanece bloqueada.
