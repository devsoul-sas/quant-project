# Integración efímera de Deriv (Escenario A)

Los adapters para la cuenta demo de Deriv mantienen ticks y estadísticas transitorias en
memoria, con TTL máximo de 23 horas y sin escribir payloads a disco. `demo-execute` habilita
exclusivamente el **Escenario A**: observar una ventana corta, tomar una decisión causal,
ejecutar como máximo un contrato demo, reconciliarlo y eliminar el estado de sesión.

`live-demo` y `live-evaluate` continúan bloqueados porque exportan decisiones o métricas.
`demo-execute` solo imprime un recibo operativo genérico; precios, ticks, payout, identificador
del contrato, P/L y métricas permanecen en memoria y no llegan a stdout.

## Tres escenarios y decisión vigente

### A — Estadísticas transitorias: permitido

Media móvil, distribución de últimos dígitos, volatilidad u otra estadística sobre una ventana
efímera pueden usarse para decidir una operación demo. Ticks, estadísticas y resultados se
eliminan al cerrar la sesión y nunca alimentan un corpus acumulado.

### B — Dataset histórico de características: bloqueado

No se conservan durante meses filas de EMA, RSI, frecuencia de dígitos, variaciones, etiquetas
o probabilidades. Transformar los ticks no demuestra que el resultado quede fuera de API Users
Terms 2.1–2.4.

### C — Pesos de modelos entrenados: bloqueado

No se entrenan ni conservan archivos `.pt`, `.pkl`, checkpoints, embeddings o parámetros con
contenido Deriv. Que un modelo no permita reconstruir fácilmente los ticks no concede derechos
de retención sobre el artefacto derivado.

B y C quedan fuera del alcance: no se esperará autorización futura de Deriv.

## Comportamiento actual de la CLI

Los comandos de exportación siguen devolviendo:

```text
error: Deriv-derived output is disabled outside the <24h ephemeral session
```

El rechazo ocurre antes de resolver credenciales o abrir la red. No existe un flag para omitirlo.

Una única operación demo se arma explícitamente con:

```text
uv run devsoul-quant demo-execute --symbol R_100 --stake 1.00 \
  --minimum-net-payout-ratio 0.75 --maximum-session-loss 1.00 \
  --confirm-demo-only
```

Requiere `DEVSOUL_QUANT_DERIV_TOKEN`, `DEVSOUL_QUANT_DERIV_APP_ID` y, opcionalmente,
`DEVSOUL_QUANT_DERIV_ACCOUNT` en el entorno del proceso. Nunca escriba sus valores en el comando,
repositorio, documentación, logs o chat. La confirmación habilita una sola invocación; no existe
loop autónomo ni modo real.

### Sesión paper efímera (paper-session)

`paper-session` ejecuta una sesión paper-only dentro del mismo marco efímero: descubre contratos
en runtime, recolecta una ventana corta de ticks en memoria, solicita propuestas contemporáneas de
solo lectura, decide causalmente, simula el settlement y elimina todo el estado al cerrar. No
compra ningún contrato; solo observa economía contemporánea.

```text
uv run devsoul-quant paper-session --strategy even-odd --symbol R_10 --confirm-paper-only
uv run devsoul-quant paper-session --strategy multiplier --confirm-paper-only
```

El único output es un veredicto JSON con la conclusión (`NO_EDGE`, `INSUFFICIENT_EVIDENCE` o
`PAPER_ELIGIBLE`) y conteos agregados de la sesión. Nunca imprime ticks, precios, payout, P/L,
propuestas, identificadores de contrato ni la URL demo. Las credenciales se leen únicamente de
variables de entorno, igual que `demo-execute`. Una sesión Multiplier nunca concluye
`PAPER_ELIGIBLE` porque su salida paper es solo una estimación (`ESTIMATED`), no un settlement
observado (`sold`); Even/Odd solo puede emitir `PAPER_ELIGIBLE` cuando su cota conservadora supera
el break-even contemporáneo.

## Protocolo técnico

La ventana de observación usa un OTP demo y se cierra. Si existe una intención, se solicita un
segundo OTP y proposal, buy, lifecycle y forget usan una sola conexión. No se reintenta una
compra ambigua: se consulta portfolio una vez y se falla cerrado. El lifecycle completo de
settlement tiene un deadline monotónico absoluto de una hora; cada mensaje no reinicia el reloj.
El adapter rechaza cualquier configuración superior a 23 horas.

## Credenciales

El PAT, App ID y account ID se leen únicamente de variables de entorno. El OTP lo resuelve la
aplicación y nunca se acepta como argumento ni se imprime. Ninguna credencial debe entrar al
repositorio, reportes o chat.

## Garantías de seguridad (por construcción)

- `validate_demo_websocket_url` rechaza el endpoint real (`/ws/real`) y URLs mal formadas.
- `EphemeralTickCache` aplica TTL de 23 h durante la colección y no tiene I/O a disco.
- La colección tiene límite duro de una hora y tamaño máximo de 10.000 ticks.
- `live-demo` y `live-evaluate` se bloquean antes de leer credenciales o abrir la red.
- `demo-execute` exige confirmación, cuenta demo, stake fijo, payout mínimo, límite de pérdida,
  máximo de un contrato, conciliación y limpieza en `finally`.
- `ExecutionMode` no contiene ningún modo de dinero real; `REAL` se rechaza en el parseo.
- Los casos de uso offline nunca afirman economía ni rentabilidad.

## Límites

- Es una prueba de integración demo, no backtest histórico ni evidencia de rentabilidad.
- El recibo genérico no permite calcular ni afirmar desempeño económico.
- El comando no mantiene una serie de sesiones, dataset, métricas acumuladas o modelo.
- Los índices sintéticos (R_100, etc.) son propietarios de Deriv; su histórico real no
  existe en terceros. Para evidencia estadística histórica véase
  `docs/data/provider-candidates.md`.
