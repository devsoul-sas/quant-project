# Candidatos a proveedor de datos

Estado: BCE y Federal Reserve H.10 aprobados para FX diario; ejecución y costos
observados permanecen bloqueados. Esta matriz registra únicamente lo confirmado
contra términos oficiales; las celdas vacías son desconocidas y bloquean la adopción.

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
| Retención de derivados | BLOQUEADO — API Terms 2.1; sin confirmación escrita |
| Presentación comercial | PENDIENTE |
| Redistribución | PROHIBIDA sin permiso escrito (General Terms 16.5–16.6) |
| Revisión de solicitud | PENDING_PROVIDER_REVIEW (última notificación 2026-10-29) |

Deriv no está en el camino crítico. No se asume autorización por accesibilidad del API.
Un probe público efímero del 2026-11-05 confirmó que `frxEURGBP` ofrece CALL/PUT
de 1–365 días. Esto solo valida capacidad contractual, no equivalencia entre `5d`
calendario y cinco observaciones; propuestas y derivados siguen bloqueados. Ver
ADR-009/ADR-010.

## Evaluación de la shortlist

Cada candidato fue evaluado con la [plantilla](provider-evaluation-template.md) contra sus
fuentes oficiales. El BCE (licencia permisiva) y la Reserva Federal H.10 (dominio público)
están aprobados para FX diaria; ninguno desbloquea ticks/opciones. `CONDICIONAL`
tampoco autoriza ingestión.

| Candidato | Subyacentes | Documento oficial a revisar | Estado |
|-----------|-------------|------------------------------|--------|
| BCE (Banco Central Europeo) | forex (fixings diarios frente al euro, ~30 monedas) | [evaluación formal](provider-evaluation-ecb.md) | **APROBADO BAJO LICENCIA PERMISIVA** — free use con atribución; restricción de producto: solo diario, sin bid/ask |
| Reserva Federal (H.10) | forex (noon buying rates diarios contra el USD, ~30 monedas) | [evaluación formal](provider-evaluation-federal-reserve.md) | **APROBADO BAJO DOMINIO PÚBLICO** — 17 U.S.C. § 105; cita al Board; segunda fuente independiente para validar EURGBP |
| Bank of England | forex (daily spot rates against Sterling, GBP base) | [evaluación formal](provider-evaluation-bank-of-england.md) | **CONDICIONAL / BLOQUEADO** — OGL v3.0, pero "selected exchange rate data" excluida (reproducida bajo licencia de terceros) |
| Dukascopy | forex, índices, materias primas, cripto (tick/OHLC) | [evaluación formal](provider-evaluation-dukascopy.md) | **RECHAZADO** — uso personal/no comercial; prohíbe bases de datos y automatización sin consentimiento |
| Binance | cripto (market data pública/histórica) | [evaluación formal](provider-evaluation-binance.md) | **RECHAZADO** — Binance Vision es CC BY-NC-SA; todo uso comercial requiere licencia empresarial escrita y SaaS/feeds comerciales están prohibidos |
| Alpha Vantage | acciones, forex, cripto | [evaluación formal](provider-evaluation-alpha-vantage.md) | **RECHAZADO BAJO TÉRMINOS ESTÁNDAR** — solo personal/no comercial; acuerdo escrito requerido |
| Twelve Data | acciones, forex, cripto | [evaluación formal](provider-evaluation-twelve-data.md) | **CONDICIONAL / BLOQUEADO** — Business/Enterprise posible, pero TTL, modelos y borrado requieren licencia escrita |

**Dukascopy, Binance y Alpha Vantage no sirven bajo sus términos estándar.** Que históricos
o APIs sean accesibles o gratuitos no concede automatización, persistencia y uso comercial.
Twelve Data es el candidato contractual más cercano, pero permanece bloqueado hasta obtener
una orden/licencia escrita que cierre los criterios desconocidos.

## Conclusión operativa

Dos proveedores con derechos explícitos están aprobados para FX diaria: el BCE (licencia
permisiva) y la Reserva Federal H.10 (dominio público). El H.10 sirve como segunda fuente
independiente para validar la señal EURGBP (ADR-008). Para ticks/opciones no existe fuente
permisiva y se mantiene el bloqueo. La adopción de cualquier candidato para redistribución a
socios o uso SaaS exige revisión jurídica previa.
