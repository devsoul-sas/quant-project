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

**Actualización (2026-11-04):** esta decisión de `NO_PROVIDER_APPROVED` fue reemplazada para
FX diaria por ADR-007 (BCE aprobado) y ADR-008 (Reserva Federal H.10 aprobado, dominio público).
Sigue vigente para ticks/opciones y para cualquier otro subyacente sin fuente permisiva.

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

## Evaluación Reserva Federal H.10 (FX diario)

La [evaluación formal de la Reserva Federal](provider-evaluation-federal-reserve.md) concluyó
**APROBADO BAJO DOMINIO PÚBLICO**: el aviso de copyright del Board declara que la información
del sitio "is in the public domain and may be copied and distributed without permission"
(citando al Board), y 17 U.S.C. § 105 excluye del copyright las obras del gobierno federal de
EE.UU. Habilita una segunda fuente independiente (fixing de Nueva York) para validar la señal
EURGBP. Ver ADR-008.

## Evaluación Bank of England (FX diario)

La [evaluación formal del Bank of England](provider-evaluation-bank-of-england.md) concluyó
**CONDICIONAL / BLOQUEADO**: la Database está bajo OGL v3.0, pero excluye expresamente
"selected exchange rate data and series" reproducidas bajo licencia de terceros. Sin confirmar
que la serie de spot rates concreta está cubierta por la OGL, no se adopta.

## Resultado de la shortlist

| Proveedor | Resultado |
|---|---|
| Dukascopy | Rechazado bajo términos públicos |
| Binance | Rechazado bajo términos públicos |
| Alpha Vantage | Rechazado bajo términos estándar |
| Twelve Data | Condicional, bloqueado pendiente de licencia escrita |
| BCE (euro FX reference rates) | Aprobado para FX diario (ver ADR-007) |
| Reserva Federal (H.10 FX rates) | Aprobado para FX diario, dominio público (ver ADR-008) |
| Bank of England (daily spot rates) | Condicional, bloqueado (exclusión OGL de datos FX) |

## Siguiente paso concreto

La señal EURGBP ya fue replicada contra H.10. El siguiente gate es economía
ejecutable y equivalencia temporal según ADR-009/ADR-010. Deriv permanece
bloqueado por retención ≤24 h; IG, IBKR y OANDA fueron evaluados y ninguno quedó
aprobado. Ver [execution-venue-evaluation.md](execution-venue-evaluation.md).

El holdout permanece sellado hasta que un único producto primario tenga derechos,
economía observada y ventana ejecutable equivalentes a la hipótesis congelada.

## Condición de cambio

Esta decisión se reemplaza únicamente con: URL fuente oficial, fecha de consulta, versión
del documento y hash (cuando esté permitido) que cubran por escrito todos los criterios
obligatorios, más revisión humana/jurídica antes de redistribución a socios o uso SaaS.
