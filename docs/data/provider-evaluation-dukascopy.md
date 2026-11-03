# Evaluación de proveedor: Dukascopy

- Fecha de consulta: 2026-10-29
- Resultado: **RECHAZADO PARA EL USO PROPUESTO**
- Alcance: datos históricos descargables desde el sitio web de Dukascopy
- Regla: lo no autorizado explícitamente se considera bloqueante

Esta evaluación técnica de derechos no sustituye asesoría jurídica.

## Fuentes oficiales verificadas

1. Historical Data Export:
   https://www.dukascopy.com/swiss/english/marketwatch/historical/
   - SHA-256 del HTML consultado: `06c28e70def4b6238919345d3de0ed80025c7a17eed7ec31ae7af35a0fba9d37`
   - Tamaño: 165647 bytes
2. Terms of Use:
   https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/
   - SHA-256 del HTML consultado: `d21f71e8cdd394be21031f2db7bcafde1f2d75598f67bf267f8a496a79159e15`
   - Tamaño: 39676 bytes
   - La página no publica un número de versión ni fecha efectiva visible; el contenido puede
     modificarse en cualquier momento y exige revisión continua.

Los HTML usados para calcular los hashes se mantuvieron únicamente en `/tmp` durante la
revisión y no forman parte del repositorio ni de un corpus de datos.

## Evidencia textual relevante

### Restricciones on Use

Los términos limitan el sitio a uso propio no comercial, salvo acuerdo escrito:

> "solely for your own non-commercial use and benefit"

También prohíben construir una base de datos con el sitio y almacenar el sitio o partes de
él en bases de datos:

> "may not be used to construct a database of any kind"

> "may [not] be stored (in its entirety or in any part) in databases"

La automatización requiere consentimiento escrito previo:

> "shall not use or attempt to use any 'scraper,' 'robot,' 'bot,' ... or any other
> automate device ... without the prior express written consent of DUKASCOPY"

### License

La descarga tiene una licencia limitada al uso personal y no comercial:

> "ONLY for your own personal, non-commercial use"

### Termination

Al terminar el uso, se deben destruir los materiales obtenidos y sus copias:

> "destroy promptly all materials obtained from the WEBSITE and any copies thereof"

## Matriz de derechos

| Criterio obligatorio | Evidencia | Estado |
|---|---|---|
| Retención histórica | Prohibición explícita de construir/almacenar una base de datos del sitio | **DENEGADO** |
| Features, modelos y métricas derivadas | No existe autorización explícita; además se prohíben derivative works salvo lo permitido | **DESCONOCIDO / BLOQUEANTE** |
| Presentación comercial o a socios | La licencia es personal y no comercial; transferencia/beneficio de terceros restringidos | **DENEGADO** |
| Redistribución | Recirculación, redistribución y publicación exigen consentimiento escrito previo | **DENEGADO** |
| Acceso histórico reproducible | La página ofrece exportación de Forex, commodities e índices, pero no fija contrato/versionado reproducible | **PARCIAL** |
| Campos económicos | Exportador visible de precios; no se confirmó que incluya payout ni economía de opciones Deriv | **NO APLICA / INSUFICIENTE** |
| Automatización y límites | Los bots/scrapers requieren consentimiento escrito previo; no se encontró cuota contractual para el exportador | **DENEGADO SIN CONSENTIMIENTO** |
| Precio | La página pública no establece una licencia comercial ni precio de derechos de datos | **DESCONOCIDO / BLOQUEANTE** |
| Jurisdicción/producto | Los términos señalan restricciones por ley/jurisdicción y contenido de terceros, sin autorización específica para Colombia/SaaS | **DESCONOCIDO / BLOQUEANTE** |
| Terminación/borrado | Destrucción de materiales obtenidos y copias al terminar | **OBLIGACIÓN EXPLÍCITA** |

## Decisión

Dukascopy **no puede ser la fuente histórica del proyecto bajo los términos públicos
actuales**. El uso pretendido requiere automatización, persistencia reproducible,
derivados/features y posible presentación comercial; los términos solo conceden descarga
personal no comercial y bloquean bases de datos y automatización sin consentimiento.

No se descargaron precios ni datos de mercado durante esta evaluación.

## Qué podría cambiar la decisión

Solo una licencia o autorización escrita de Dukascopy que cubra expresamente:

1. descarga automatizada y límites;
2. retención histórica y backups;
3. features, métricas, modelos y resultados derivados;
4. uso comercial interno y presentación a socios;
5. redistribución/exportación permitida y prohibida;
6. terminación, borrado y campos de auditoría retenibles;
7. entidad/jurisdicción colombiana y subyacentes autorizados.
