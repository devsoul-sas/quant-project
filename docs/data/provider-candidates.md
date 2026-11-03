# Candidatos a proveedor de datos

Estado: sin proveedor aprobado. Esta matriz registra únicamente lo confirmado contra
términos oficiales; las celdas vacías son desconocidas y bloquean la adopción.

## Hallazgo estructural (verificado por diseño, no por términos)

Los índices sintéticos de volatilidad de Deriv (R_10, R_25, R_50, R_75, R_100) son
**propietarios de Deriv**. Ningún tercero ofrece su histórico. Por tanto, una fuente
histórica "compatible" no es un reemplazo directo del feed Deriv, sino un **cambio de
subyacente** (forex, cripto, índices bursátiles o materias primas de otra fuente). El
pipeline ya es provider-independiente (ADR-006), así que la estrategia se revalida sobre
esos subyacentes y, más adelante, puede mapearse de vuelta a la ejecución demo Deriv.

## Deriv

| Criterio | Estado |
|----------|--------|
| Retención de histórico | BLOQUEADO — API Terms 2.1–2.4; solo caché ≤24 h |
| Retención de derivados | PENDIENTE — sin confirmación escrita |
| Presentación comercial | PENDIENTE |
| Redistribución | PROHIBIDA sin permiso escrito (General Terms 15.5–15.6) |
| Revisión de solicitud | PENDING_PROVIDER_REVIEW (última notificación 2026-10-29) |

Deriv no está en el camino crítico. No se asume autorización por accesibilidad del API.

## Evaluación de la shortlist

Cada candidato fue evaluado con la [plantilla](provider-evaluation-template.md) contra sus
fuentes oficiales. Ninguno está aprobado; `CONDICIONAL` tampoco autoriza ingestión.

| Candidato | Subyacentes | Documento oficial a revisar | Estado |
|-----------|-------------|------------------------------|--------|
| Dukascopy | forex, índices, materias primas, cripto (tick/OHLC) | [evaluación formal](provider-evaluation-dukascopy.md) | **RECHAZADO** — uso personal/no comercial; prohíbe bases de datos y automatización sin consentimiento |
| Binance | cripto (market data pública/histórica) | [evaluación formal](provider-evaluation-binance.md) | **RECHAZADO** — Binance Vision es CC BY-NC-SA; todo uso comercial requiere licencia empresarial escrita y SaaS/feeds comerciales están prohibidos |
| Alpha Vantage | acciones, forex, cripto | [evaluación formal](provider-evaluation-alpha-vantage.md) | **RECHAZADO BAJO TÉRMINOS ESTÁNDAR** — solo personal/no comercial; acuerdo escrito requerido |
| Twelve Data | acciones, forex, cripto | [evaluación formal](provider-evaluation-twelve-data.md) | **CONDICIONAL / BLOQUEADO** — Business/Enterprise posible, pero TTL, modelos y borrado requieren licencia escrita |

**Dukascopy, Binance y Alpha Vantage no sirven bajo sus términos estándar.** Que históricos
o APIs sean accesibles o gratuitos no concede automatización, persistencia y uso comercial.
Twelve Data es el candidato contractual más cercano, pero permanece bloqueado hasta obtener
una orden/licencia escrita que cierre los criterios desconocidos.

## Conclusión operativa

Mientras no exista un proveedor con derechos explícitos, la decisión se mantiene en
`NO_PROVIDER_APPROVED` y la investigación continúa provider-independiente con datos
sintéticos propios (ADR-006). La adopción de cualquier candidato exige revisión
jurídica antes de redistribución a socios o uso SaaS.
