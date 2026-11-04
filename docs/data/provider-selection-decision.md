# Decisión de selección de proveedor

- Fecha: 2026-10-29
- Estado: aceptada

## Decisión

**NO_PROVIDER_APPROVED.**

Ningún proveedor externo cumple hoy los criterios obligatorios por escrito:

- retención explícita de datos históricos;
- retención de features/modelos/métricas derivadas;
- presentación comercial o a socios internos;
- restricciones de redistribución documentadas;
- acceso histórico reproducible con semántica de timestamps;
- campos económicos apropiados al producto.

Deriv permanece en `PENDING_PROVIDER_REVIEW` y no está autorizado para persistencia.

## Consecuencias

- La investigación continúa provider-independiente con datos sintéticos propios (ADR-006).
- Ningún payload de proveedor entra en persistencia.
- La integración demo Deriv se limita a la vía efímera (caché ≤24 h, sin persistencia).
- Los índices sintéticos Deriv son propietarios: el histórico real exige cambiar de
  subyacente (forex/cripto/índices de otra fuente), no un reemplazo del feed Deriv.

## Evaluación Dukascopy

La [evaluación formal de Dukascopy](provider-evaluation-dukascopy.md) concluyó
**RECHAZADO**: los términos públicos limitan la descarga a uso personal no comercial,
prohíben construir/almacenar bases de datos con el contenido del sitio y exigen
consentimiento escrito para automatización. No se descargaron datos de mercado.

## Evaluación Binance

La [evaluación formal de Binance](provider-evaluation-binance.md) concluyó **RECHAZADO** para
investigación potencialmente comercial, proprietary production y SaaS. Binance Vision aplica
CC BY-NC-SA 4.0, limita el backtesting a investigación personal no productiva y exige una
licencia empresarial escrita para cualquier utilización comercial; incluye expresamente
charts, models e indicadores derivados y prohíbe feeds/productos/bots comerciales. Para la
market data API pública fuera del alcance claramente definido por Vision no se encontró una
licencia separada que conceda persistencia o redistribución comercial. No se descargaron datos
de mercado.

## Evaluaciones Alpha Vantage y Twelve Data

- [Alpha Vantage](provider-evaluation-alpha-vantage.md): **RECHAZADO BAJO TÉRMINOS
  ESTÁNDAR**. La licencia es personal/no comercial y el uso corporativo o acceso indirecto
  por terceros requiere acuerdo escrito. Persistencia, modelos y borrado no están cubiertos.
- [Twelve Data](provider-evaluation-twelve-data.md): **CANDIDATO CONDICIONAL, BLOQUEADO**.
  Reconoce planes Business y Derived Data no reversible, pero no hay un TTL público suficiente
  para corpus históricos ni reglas claras para modelos, backups y retención post-terminación.

## Evaluación BCE (FX diario)

La [evaluación formal del BCE](provider-evaluation-ecb.md) concluyó **APROBADO BAJO
LICENCIA PERMISIVA** para una estrategia FX de frecuencia diaria: la política de copyright
concede "free use of the information obtained" con atribución, sin TTL, sin prohibición de
bases de datos y sin contrato escrito. No desbloquea la vía de ticks/opciones. Ver ADR-007.

## Resultado de la shortlist

| Proveedor | Resultado |
|---|---|
| Dukascopy | Rechazado bajo términos públicos |
| Binance | Rechazado bajo términos públicos |
| Alpha Vantage | Rechazado bajo términos estándar |
| Twelve Data | Condicional, bloqueado pendiente de licencia escrita |
| BCE (euro FX reference rates) | Aprobado para FX diario (ver ADR-007) |

## Siguiente paso concreto

Consolidar el backtest diario sobre datos observados del BCE (ya aprobado) y establecer los
criterios de promoción fuera de muestra y de holdout. Twelve Data queda como opción futura
de pago si se requiere intradía/cripto; su consulta comercial no se envía automáticamente.

## Condición de cambio

Esta decisión se reemplaza únicamente con: URL fuente oficial, fecha de consulta, versión
del documento y hash (cuando esté permitido) que cubran por escrito todos los criterios
obligatorios, más revisión humana/jurídica antes de redistribución a socios o uso SaaS.
