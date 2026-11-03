# Integración efímera de Deriv (preparada, CLI bloqueada)

Los adapters para la cuenta demo de Deriv están preparados para mantener ticks en memoria con
TTL de 23 horas y nunca escribirlos a disco. Sin embargo, la CLI está **bloqueada**: incluso
un reporte agregado enviado a stdout puede redirigirse a almacenamiento sin TTL verificable.
No se habilitará salida derivada de Deriv hasta contar con autorización escrita y un sink
compatible con esos derechos.

`live-demo` y `live-evaluate` devuelven error antes de leer token, resolver OTP, conectarse o
recolectar ticks. Las secciones siguientes describen preparación técnica, no un flujo operativo.

## Comportamiento actual de la CLI

Ambos comandos devuelven únicamente:

```text
error: Deriv-derived output is disabled pending written authorization
```

El rechazo ocurre antes de resolver credenciales, conectarse, recolectar ticks, ejecutar la
estrategia o construir un reporte. No existe un flag local para omitir este gate.

## Preparación técnica offline

Los componentes internos conservan pruebas offline para validación de URL demo, OTP, colector
acotado, caché en memoria, alineación causal, folds purgados y métricas no económicas. Esta
preparación no habilita el uso operativo ni la exportación de resultados derivados de Deriv.

## Credenciales

No se necesita ni se debe configurar PAT, App ID, account ID u OTP mientras el gate esté
bloqueado. Si alguna credencial local de pruebas anteriores sigue exportada, elimínala de la
sesión. Ninguna credencial debe entrar al repositorio, reportes o chat.

## Garantías de seguridad (por construcción)

- `validate_demo_websocket_url` rechaza el endpoint real (`/ws/real`) y URLs mal formadas.
- `EphemeralTickCache` aplica TTL de 23 h durante la colección y no tiene I/O a disco.
- La colección tiene límite duro de una hora y tamaño máximo de 10.000 ticks.
- La CLI bloquea la integración antes de leer credenciales o abrir la red.
- `ExecutionMode` no contiene ningún modo de dinero real; `REAL` se rechaza en el parseo.
- Los casos de uso offline nunca afirman economía ni rentabilidad.

## Límites

- Es preparación técnica offline, no una prueba operativa ni backtest histórico.
- No existe hoy una salida Deriv habilitada para usuarios.
- Los índices sintéticos (R_100, etc.) son propietarios de Deriv; su histórico real no
  existe en terceros. Para evidencia estadística histórica véase
  `docs/data/provider-candidates.md`.
