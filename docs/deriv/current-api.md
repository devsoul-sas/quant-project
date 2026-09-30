# Deriv Options API vigente para DevSoul Quant

Estado: snapshot de investigación
Consultado: 2026-09-29T01:52Z
Fuente normativa técnica: documentación y schemas oficiales de Deriv

## Regla de precedencia

1. Schema oficial fijado por release.
2. Referencia oficial del endpoint.
3. Guías/workflows oficiales.
4. Esta documentación local.
5. Ejemplos de terceros.

Si dos fuentes oficiales se contradicen, no se implementa el flujo afectado hasta comprobarlo contra el schema vigente y una llamada no destructiva o recibir confirmación de Deriv.

## Release de schemas fijado

- Release: `production_v20260901_0`
- Publicado: `2026-09-07T07:41:36Z`
- Release: https://github.com/deriv-com/deriv-api-schemas/releases/tag/production_v20260901_0
- Archivo: https://github.com/deriv-com/deriv-api-schemas/releases/download/production_v20260901_0/schemas.zip
- SHA-256: `adaab0acaf33bd159e45912995af2b78101049f43683d223f0ac11be0a39e7c3`
- Tamaño: 139891 bytes
- Schemas extraídos: 127
- Copia local no destinada a Git: `artifacts/vendor/deriv/schemas-production_v20260901_0.zip`

Ver `docs/deriv/schema-manifest.json`.

## Arquitectura actual

Base REST/upgrade WS documentada:

```text
https://api.derivws.com
```

WebSocket público, sin autenticación:

```text
wss://api.derivws.com/trading/v1/options/ws/public
```

La referencia lo define como canal para market data y metadatos; no permite acciones account-scoped.

WebSocket demo:

```text
GET /trading/v1/options/ws/demo?otp=<one-time-password>
```

La URL autenticada no debe construirse manualmente. El flujo esperado es:

1. Autenticar REST mediante OAuth 2.0 o PAT.
2. Para PAT, enviar `Authorization: Bearer <token>` y `Deriv-App-ID`.
3. Descubrir/seleccionar una cuenta Options demo.
4. Solicitar OTP con `POST /trading/v1/options/accounts/{accountId}/otp`.
5. Leer `data.url` de la respuesta.
6. Conectarse directamente a esa URL.

El schema `websocket_response.schema.json` confirma que la respuesta contiene una URL WS con OTP embebido. Nunca registrar esa URL completa.

## Nota sobre autenticación

La página actual de best practices todavía contiene lenguaje genérico sobre enviar `authorize` por WebSocket, mientras el Overview, los endpoints Options y los schemas del release fijado describen OTP REST + URL WS. Para este MVP prevalece el flujo OTP de Options. La discrepancia debe mantenerse visible y verificarse nuevamente antes de implementar demo.

PAT es apropiado para el laboratorio interno si tiene privilegio mínimo y se mantiene server-side. OAuth 2.0 Authorization Code + PKCE se reserva para una futura aplicación con usuarios; no forma parte del MVP.

## Operaciones públicas

### `active_symbols`

Request mínimo:

```json
{"active_symbols":"full","req_id":1}
```

Devuelve símbolos activos. El schema actual usa `underlying_symbol`, no el campo legacy `symbol`, dentro de cada elemento.

### `contracts_for`

Request:

```json
{"contracts_for":"SYMBOL","req_id":2}
```

Devuelve contratos disponibles, barreras y duraciones. Siempre se consulta antes de asumir que una familia es válida para un símbolo.

### `ticks`

Request de suscripción:

```json
{"ticks":"SYMBOL","subscribe":1,"req_id":3}
```

La respuesta incluye epoch, quote, symbol, pip size y subscription ID. El schema indica frecuencia de hasta un segundo. Liberar con:

```json
{"forget":"<subscription-id>","req_id":4}
```

O por tipo cuando corresponda:

```json
{"forget_all":"ticks","req_id":5}
```

### `ticks_history`

Se usa para snapshots/diagnóstico de gaps donde el producto lo admita. Recuperar historia no borra el hecho de que el stream local estuvo interrumpido.

### `proposal`

No requiere autenticación según el schema fijado. Requiere `proposal`, `contract_type`, `currency` y `underlying_symbol`; también duration/date_expiry y parámetros propios del contrato.

Ejemplo de ingeniería probado, no autorización para operar:

```json
{
  "proposal": 1,
  "amount": 1,
  "basis": "stake",
  "contract_type": "CALL",
  "currency": "USD",
  "duration": 5,
  "duration_unit": "t",
  "underlying_symbol": "SYMBOL",
  "req_id": 2001
}
```

Campos operativos necesarios durante la caché autorizada: request canónica, ask price, payout, proposal ID, spot, spot time, date start/expiry, longcode, timestamps locales y schema release. Los IDs de propuesta son efímeros. No persistir la respuesta cruda ni estos campos por más del plazo autorizado; actualmente, máximo 24 horas y con margen operativo de 23 horas según ADR-005.

## Operaciones autenticadas demo

### `buy`

Requiere scope `trade`. Recibe proposal ID o parámetros y `price` como precio máximo. Una compra no es idempotente: si se pierde la respuesta, reconciliar posición/portfolio antes de reintentar.

### `proposal_open_contract`

Usar suscripción para seguir el lifecycle. Persistir todas las transiciones y liberar la suscripción al liquidarse.

### `sell`

Cierra un contrato identificado por `contract_id`; `price=0` representa sell at market. Solo usar cuando el estado del contrato indique que está vendible. No representa abrir una posición bajista.

## Lifecycle WS obligatorio

- una conexión reutilizada y multiplexada;
- `req_id` único y correlation ID local;
- suscripciones en vez de polling;
- ping periódico para detectar conexión silenciosa;
- backoff exponencial con jitter;
- inspección de `error` en toda respuesta;
- `forget`/`forget_all` al terminar;
- cola/rate limiter compartido por presupuesto;
- reconciliación antes de reintentar operaciones no idempotentes;
- persistencia de connection/session ID y secuencia local.

## Límites observados en documentación

Los límites pueden cambiar y son configuración externa versionada.

### WebSocket: presupuestos compartidos

| Grupo | Por minuto | Por hora |
|---|---:|---:|
| `proposal`, `proposal_open_contract`, `buy`, `sell` | 360 | 14400 |
| `balance`, `statement` | 100 | 2000 |
| `portfolio`, `profit_table` | 30 | 1500 |
| demás calls | 220 | 14400 |

`ping` queda fuera de esos presupuestos; la página consultada permite 10 pings/segundo por conexión. El sistema usará una frecuencia mucho menor.

### REST

| Contador | Ventana | Límite |
|---|---:|---:|
| IP | 1 minuto | 300 |
| IP | 10 minutos | 1000 |
| usuario autenticado | 1 minuto | 80 |

No diseñar al límite. Reservar capacidad para reconciliación y recuperación.

## Prueba pública de compatibilidad

El 2026-09-29 UTC se ejecutó una prueba efímera, únicamente con llamadas públicas, sin credenciales y sin compra. Se comprobaron `active_symbols`, `contracts_for`, `proposal`, `ticks`, correlación y liberación de suscripciones mediante `forget`.

Los payloads, inventario y market data se eliminaron el mismo día tras confirmar que API Users Terms 2.1–2.4 solo permiten cachearlos durante un máximo de 24 horas. No se conservan valores de mercado ni hashes de esos payloads.

Véase `docs/deriv/api-storage-blocker.md`.

## Fuentes oficiales

- https://developers.deriv.com/docs/intro/api-overview/
- https://developers.deriv.com/docs/intro/authentication/
- https://developers.deriv.com/docs/options/websocket/
- https://developers.deriv.com/docs/options/ws-demo/
- https://developers.deriv.com/docs/options/ws-public/
- https://developers.deriv.com/docs/data/active-symbols/
- https://developers.deriv.com/docs/data/contracts-for/
- https://developers.deriv.com/docs/data/ticks/
- https://developers.deriv.com/docs/data/ticks-history/
- https://developers.deriv.com/docs/trading/proposal/
- https://developers.deriv.com/docs/trading/buy/
- https://developers.deriv.com/docs/trading/sell/
- https://developers.deriv.com/docs/trading/proposal-open-contract/
- https://developers.deriv.com/docs/limits/
- https://developers.deriv.com/docs/best-practices/
- https://github.com/deriv-com/deriv-api-schemas/releases
- https://deriv.com/terms-and-conditions/api-users

## Revalidación

Repetir esta investigación antes de implementar el adaptador demo y cada vez que cambie el release de schemas. Un cambio de schema debe fallar visiblemente en pruebas contractuales.