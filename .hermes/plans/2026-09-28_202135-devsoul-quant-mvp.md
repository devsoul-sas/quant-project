# DevSoul Quant MVP — Plan maestro de implementación y validación

> **Para Hermes:** ejecutar este plan por bloques con TDD estricto (RED → GREEN → REFACTOR), revisión de cumplimiento y revisión de calidad. No hacer commits, push ni habilitar ejecución real sin autorización explícita del usuario.

> **BLOQUEO P0 — 2026-09-29:** los API Users Terms de Deriv R26|03, cláusulas 2.1–2.4, prohíben almacenar contenido del API —incluido feed data— y solo autorizan caché por hasta 24 horas. ADR-005 reemplaza cualquier paso de este plan que persista ticks, propuestas, payloads, Parquet, backups o derivados de datos Deriv. Los bloques de histórico, backtest real, modelos, evidencia al socio y dashboard quedan condicionados a autorización escrita o a una fuente alternativa con licencia compatible. Mientras tanto solo se implementan bootstrap, dominio, seguridad demo-only, fixtures sintéticas propias y, si es necesaria, caché efímera sin backup con TTL operativo ≤23 horas.

**Objetivo:** construir un laboratorio cuantitativo local, reproducible y auditable que determine con evidencia —sin prometer rentabilidad— si alguna estrategia tiene ventaja estadística fuera de muestra y en ejecución paper/demo sobre Deriv.

**Arquitectura:** monolito modular en Python con varios procesos desplegables (`api`, `collector`, `trader`) que comparten un dominio independiente de Deriv. PostgreSQL conserva únicamente estado propio/autorizado y el ledger; Parquet se usa solo para datos sintéticos propios o fuentes con licencia compatible. El mismo motor determinista de estrategia/riesgo se ejecuta por replay en backtest y en tiempo real para minimizar diferencias entre simulación y demo.

**Stack:** Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PostgreSQL 16+, asyncio/WebSocket, httpx, Polars o pandas (elegir uno mediante spike), PyArrow/Parquet, scikit-learn, pytest, Ruff, mypy, Docker Compose, Prometheus/OpenMetrics y dashboard mínimo local.

---

## 1. Lectura consolidada de los documentos

Los dos documentos están bien alineados en lo esencial:

- El entregable es un sistema de investigación y validación, no una promesa de rentabilidad.
- La secuencia correcta es datos → investigación → backtest → paper → demo → decisión.
- El valor central para DevSoul es la propiedad intelectual: datos, experimentación reproducible, ejecución, riesgo y evidencia auditable.
- La infraestructura debe ser local y de bajo costo mientras no haya evidencia que justifique escalar.
- Dinero real, fondos de terceros, SaaS multiusuario y monetización quedan fuera del MVP.

La especificación técnica convierte la propuesta comercial en componentes concretos, pero todavía no debe tratarse como contrato final de implementación. Antes de programar hay que cerrar varias decisiones que afectan todo el diseño.

## 2. Correcciones y decisiones previas obligatorias

### 2.1 Corregir la semántica de `BUY / SELL / WAIT`

En opciones de Deriv, `buy` compra un contrato propuesto y `sell` puede representar el cierre anticipado de un contrato existente; no equivale necesariamente a abrir una posición bajista. Modelar la estrategia directamente con `BUY/SELL/WAIT` mezclaría intención de mercado con operación de la API.

Modelo recomendado:

```text
StrategyIntent
├── ENTER(contract_spec, direction, duration, barrier, stake_policy)
├── HOLD
└── EXIT(position_id, reason)
```

La UI puede mostrar una etiqueta simplificada `BUY / SELL / WAIT`, pero el dominio y el ledger deben conservar la intención exacta y la traducción al contrato Deriv.

### 2.2 Elegir un universo y una familia de contratos, no “un símbolo” aislado

La rentabilidad depende conjuntamente de:

- símbolo;
- familia/tipo de contrato;
- duración;
- barrera;
- moneda y stake;
- payout/propuesta disponible;
- reglas de entrada y salida.

El primer resultado técnico no será una estrategia: será un inventario reproducible obtenido de `active_symbols`, `contracts_for` y propuestas reales sin compra. Con ese inventario se seleccionará un universo inicial pequeño y explícito.

### 2.3 Resolver la economía histórica de los contratos

Los ticks históricos no garantizan que podamos reconstruir el payout que Deriv habría ofrecido en cada instante. Un backtest con payout supuesto puede producir una ventaja ficticia.

Por ello el collector debe contemplar dos flujos diferenciados:

1. ticks crudos;
2. snapshots de `proposal` para configuraciones de contrato aprobadas, respetando límites de API.

Mientras no exista suficiente historial de propuestas, los resultados deben marcarse como `ECONOMICS_ESTIMATED`, nunca como equivalentes a ejecución real. La reconciliación contra propuestas demo será un gate formal.

### 2.4 Definir el protocolo estadístico antes de mirar el test final

Antes de experimentar se deben registrar:

- hipótesis y baseline contra el cual compite;
- variable objetivo e instante exacto de decisión;
- costos/economía contractual;
- ventanas train/validation/test;
- embargo/purga si las etiquetas se solapan;
- métricas primarias y secundarias;
- número mínimo de observaciones y operaciones;
- límite de drawdown;
- criterio de promoción y criterio de descarte;
- tratamiento de múltiples comparaciones.

La prueba de 24 horas valida operación del collector; no valida una estrategia.

### 2.5 Hacer imposible el dinero real por construcción

Para el MVP:

- no implementar `DerivRealBroker` funcional;
- no aceptar `REAL` como valor de configuración ejecutable;
- no incluir secretos reales en el esquema de configuración;
- exigir endpoint demo derivado del flujo OTP actual;
- fallar al arrancar si cuenta/endpoints no se pueden demostrar como demo;
- conservar un `kill_switch` que por defecto impida toda apertura;
- separar las credenciales de market data pública y demo.

### 2.6 Fijar la fuente de verdad de la API

La documentación oficial actual confirma la separación REST + WebSocket y publica esquemas versionados. En implementación:

- descargar `schemas.zip` desde el release oficial;
- registrar versión, URL y SHA-256;
- generar o validar modelos desde esos esquemas cuando sea práctico;
- usar pruebas contractuales contra fixtures versionadas;
- documentar cualquier diferencia con el borrador en un ADR.

No copiar endpoints ni autenticación de tutoriales antiguos.

### 2.7 Adelantar el gate jurídico y contractual mínimo

La revisión jurídica completa del futuro SaaS puede esperar, pero no deben esperar estas decisiones si un socio financiará el I+D o tendrá acceso a resultados:

- naturaleza del aporte: financiación de desarrollo, no capital administrado para trading;
- titularidad del código, modelos, artefactos derivados y resultados negativos;
- diferencia entre datos obtenidos de Deriv y datasets/features derivados por DevSoul;
- derechos de almacenamiento, retención, exhibición y redistribución según los términos vigentes de Deriv;
- jurisdicción, restricciones de marketing financiero y tratamiento aplicable a opciones/productos sintéticos;
- acceso a credenciales, datos de cuenta e informes.

El dashboard y cualquier documento para terceros deben decir permanentemente que los resultados son backtest/paper/demo, no rendimiento real.

### 2.8 Convertir “24/7” en un SLO medible

Una sola máquina local no puede prometer disponibilidad absoluta. La formulación operativa será: **operación continua supervisada, con recuperación automática, disponibilidad medida y registro íntegro de interrupciones**.

Antes de cada corrida se deben fijar:

- SLO de disponibilidad;
- tiempo máximo de recuperación;
- política ante gaps y reloj desfasado;
- clasificación del downtime: upstream, red local, mantenimiento, mercado/producto o fallo interno;
- RPO y RTO de datos/servicio.

---

## 3. Principios de diseño

1. **Replay first:** todo evento de mercado debe poder reproducirse con un reloj controlado.
2. **Un solo núcleo de decisión:** backtest, paper y demo usan las mismas interfaces de features, estrategia y riesgo.
3. **Puertos y adaptadores:** el dominio no importa SQLAlchemy, FastAPI ni tipos de Deriv.
4. **Precisión explícita:** precios, stake, payout y P/L usan `Decimal`; no `float` en contabilidad.
5. **Tiempo explícito:** UTC en almacenamiento; timestamps timezone-aware; orden total definido para eventos empatados.
6. **Append-only donde importa:** señales, decisiones de riesgo, órdenes, contratos, fills/eventos y ajustes no se sobrescriben.
7. **Idempotencia:** reconexiones y reintentos no deben duplicar eventos ni operaciones.
8. **Configuración versionada:** una ejecución referencia hashes de dataset, código, features, estrategia, modelo, contrato y riesgo.
9. **Fail closed:** ante datos incompletos, reloj desfasado, conexión degradada o ledger inconsistente, no abrir posición.
10. **Observabilidad desde el inicio:** no posponer logs, métricas, heartbeat, gaps y correlación hasta el dashboard.
11. **YAGNI:** sin Kubernetes, MLflow, GPU, microservicios, deep learning ni TimescaleDB hasta que una métrica demuestre su necesidad.
12. **Tamper-evident, no magia:** “inmutable” significa append-only bajo controles comprobables y evidencia de alteración, no inmunidad absoluta frente a un administrador del host.
13. **Relojes confiables:** UTC para instantes, reloj monotónico para duraciones y NTP/chrony monitorizado; la definición de “día” del riesgo debe ser explícita.

---

## 4. Estructura objetivo del repositorio

```text
devsoul-quant/
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── compose.yaml
├── Makefile
├── pyproject.toml
├── README.md
├── apps/
│   ├── api/main.py
│   ├── collector/main.py
│   ├── trader/main.py
│   └── dashboard/
├── src/devsoul_quant/
│   ├── config/
│   ├── domain/
│   │   ├── market/
│   │   ├── contracts/
│   │   ├── strategy/
│   │   ├── risk/
│   │   ├── trading/
│   │   └── experiments/
│   ├── application/
│   │   ├── ports/
│   │   └── services/
│   ├── adapters/
│   │   ├── deriv/
│   │   ├── persistence/
│   │   └── paper/
│   ├── datasets/
│   ├── features/
│   ├── strategies/
│   ├── backtesting/
│   ├── evaluation/
│   └── observability/
├── migrations/
├── research/
│   ├── protocols/
│   ├── experiments/
│   └── reports/
├── scripts/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── regression/
│   └── e2e/
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── deriv/
│   ├── research/
│   └── operations/
├── data/                 # ignorado por Git salvo README/.gitkeep
└── artifacts/            # ignorado por Git salvo README/.gitkeep
```

No crear repositorios Git anidados. El directorio actual aún no es un repositorio; la inicialización de Git será una acción explícita del bloque 1 y no implica commit.

---

## 5. Plan por bloques y gates

## Bloque 0 — Cerrar el contrato del MVP

**Objetivo:** convertir los borradores en decisiones verificables antes de crear código.

**Crear:**

- `docs/adr/ADR-001-local-first-modular-monolith.md`
- `docs/adr/ADR-002-replay-first-execution-core.md`
- `docs/adr/ADR-003-demo-only-safety-boundary.md`
- `docs/adr/ADR-004-market-intent-and-contract-semantics.md`
- `docs/research/validation-protocol-template.md`
- `docs/deriv/current-api.md`
- `docs/deriv/schema-manifest.json`
- `docs/scope/mvp-in-out.md`
- `docs/legal/early-gate-checklist.md`
- `docs/data/provider-data-policy.md`

**Pasos:**

1. Descargar el release actual de esquemas oficiales de Deriv.
2. Calcular y registrar SHA-256, URL y fecha de consulta.
3. Documentar REST base, autenticación PAT/OAuth, requisito de App ID, obtención de OTP y endpoints WS público/demo.
4. Documentar `active_symbols`, `contracts_for`, `ticks`, `ticks_history`, `proposal`, `buy`, `proposal_open_contract`, `sell`, `forget`, `ping` y límites de API.
5. Definir `StrategyIntent` y su traducción a solicitudes Deriv.
6. Acordar qué significa cada estado de orden/contrato y cuál es la fuente de verdad.
7. Definir formalmente modos permitidos: `BACKTEST`, `PAPER`, `DERIV_DEMO`; rechazar cualquier otro.
8. Convertir las exclusiones del documento en pruebas de arquitectura/configuración.
9. Preparar la plantilla de protocolo estadístico sin fijar aún una estrategia ganadora.
10. Revisar el documento técnico y registrar discrepancias, en vez de corregirlas silenciosamente.
11. Revisar términos de Deriv sobre automatización, límites, almacenamiento, retención, exhibición y redistribución de datos.
12. Definir por escrito la naturaleza del aporte del socio y la titularidad/acceso a código, datos derivados y resultados.
13. Sustituir cualquier promesa “24/7” por un SLO y una taxonomía de downtime medibles.

**Gate 0:**

- los documentos identifican endpoints/esquemas vigentes;
- no quedan ambiguos BUY/SELL, payout, duración ni cierre;
- existe una barrera verificable contra dinero real;
- negocio y técnica comparten una sola definición de éxito.
- el checklist jurídico/contractual temprano está resuelto o tiene bloqueos explícitos;
- los términos científicos ambiguos se convierten en fórmulas/umbrales pre-registrados antes de cada run.

---

## Bloque 1 — Bootstrap reproducible

**Objetivo:** obtener un repositorio que se levante y se verifique desde clon limpio.

**Archivos principales:** `pyproject.toml`, `compose.yaml`, `Makefile`, `.env.example`, `.gitignore`, `.github/workflows/ci.yml`, `README.md`.

**Pasos TDD/infra:**

1. Inicializar Git sin commit y registrar el estado inicial.
2. Crear `pyproject.toml` con versiones acotadas y grupos `dev`/`research`.
3. Crear lockfile reproducible, fijar versión de Python y fijar imágenes por versión/digest.
4. Configurar Ruff, mypy y pytest en modo estricto razonable.
5. Crear una prueba de importación que falle y luego el paquete `src/devsoul_quant` mínimo.
6. Crear configuración tipada con validación que falle si se solicita un modo no permitido.
7. Probar primero que `REAL` es rechazado; implementar la validación mínima.
8. Crear Compose con PostgreSQL, volúmenes, healthcheck y red local no publicada salvo necesidad de desarrollo.
9. Crear migración base vacía y smoke test de Alembic contra PostgreSQL real.
10. Crear targets `make setup`, `make up`, `make migrate`, `make test`, `make lint`, `make typecheck`, `make verify`.
11. Configurar CI sin credenciales, con secret scanning y sin depender de Deriv en vivo.
12. Documentar instalación, límites y política de secretos.
13. Verificar ausencia de `.env`, datasets, artefactos, credenciales y repos anidados.

**Gate 1 — clon limpio:**

```bash
cp .env.example .env
docker compose up -d postgres
make migrate
make verify
```

Esperado: PostgreSQL saludable, migraciones aplicadas, pruebas/lint/typecheck en verde y cero secretos versionados.

---

## Bloque 2 — Dominio, reloj y ledger mínimo

**Objetivo:** definir invariantes independientes de Deriv y de la base de datos.

**Archivos previstos:**

- `src/devsoul_quant/domain/market/entities.py`
- `src/devsoul_quant/domain/contracts/entities.py`
- `src/devsoul_quant/domain/strategy/intents.py`
- `src/devsoul_quant/domain/risk/entities.py`
- `src/devsoul_quant/domain/trading/entities.py`
- `src/devsoul_quant/domain/experiments/entities.py`
- `src/devsoul_quant/application/ports/clock.py`
- `src/devsoul_quant/application/ports/broker.py`
- pruebas equivalentes en `tests/unit/domain/`.

**Ciclos TDD, uno por comportamiento:**

1. `MarketTick` rechaza timestamps naive y quotes inválidas.
2. `ContractSpec` expresa tipo, símbolo, duración, barrera y moneda sin nombres internos de Deriv.
3. `StrategyIntent` separa entrada, espera y salida.
4. `Money`/P&L conserva precisión decimal.
5. `Signal` conserva hashes/versiones y no decide stake.
6. `RiskDecision` siempre deja razón explícita, aprobada o rechazada.
7. `Trade` impide transiciones de estado ilegales.
8. `Adjustment` corrige sin mutar el evento original.
9. `StrategyRelease` queda congelado al iniciar validación.
10. `ValidationRun` no permite cambiar estrategia, features, riesgo o universo mientras está activo.
11. `Clock` permite replay determinista sin llamar al reloj del sistema dentro del dominio.
12. `BrokerPort` modela propuesta, apertura, observación y cierre sin tipos Deriv.
13. Eventos cerrados incluyen hash canónico, hash anterior y correlation/causation ID para producir una cadena tamper-evident.

**Gate 2:** pruebas unitarias demuestran invariantes, transiciones, precisión y congelamiento; el dominio no importa FastAPI, SQLAlchemy ni módulos `adapters`. Pruebas de integración demuestran que el rol normal no puede ejecutar `UPDATE/DELETE` sobre eventos cerrados y que una corrección crea un nuevo evento.

---

## Bloque 3 — Investigación contractual y collector vertical

**Objetivo:** probar una ruta end-to-end pequeña desde WS público hasta PostgreSQL antes de generalizar.

**Archivos previstos:**

- `src/devsoul_quant/adapters/deriv/public_ws.py`
- `src/devsoul_quant/adapters/deriv/messages.py`
- `src/devsoul_quant/adapters/deriv/symbol_catalog.py`
- `src/devsoul_quant/adapters/persistence/models.py`
- `src/devsoul_quant/adapters/persistence/tick_repository.py`
- `src/devsoul_quant/application/services/collect_ticks.py`
- `apps/collector/main.py`
- migraciones y pruebas contractuales/integración.

**Pasos:**

1. Congelar fixtures sanitizadas de esquemas/respuestas oficiales.
2. Escribir contract test fallido para `active_symbols`; implementar parsing mínimo.
3. Consultar inventario vivo y persistir el artefacto crudo con timestamp/hash.
4. Escribir contract test para `contracts_for` y producir una matriz símbolo × contrato.
5. Seleccionar por configuración 1–3 símbolos y una familia de contrato para el piloto; no hard-codearlos.
6. Probar parsing de tick válido, campo desconocido y mensaje malformado.
7. Definir idempotency key a partir de campos reales del esquema; no asumir que `(symbol, epoch, quote)` siempre identifica de forma única.
8. Crear migración de ticks e integración con PostgreSQL real.
9. Implementar inserción por lotes con límites de tamaño/tiempo y backpressure.
10. Probar reconexión con backoff, jitter, resuscripción y cierre limpio.
11. Registrar inicio/fin de gaps, latencia de ingestión y estado de suscripción.
12. Añadir heartbeat/liveness/readiness distintos.
13. Implementar retención/configuración inicial y consulta de volumen por símbolo.
14. Ejecutar smoke test vivo opt-in; CI usa fixtures, no la red externa.
15. Multiplexar una conexión con `req_id`, respetar límites mediante rate limiter y limpiar suscripciones con `forget`/`forget_all` según el schema vigente.
16. Registrar provider timestamp, UTC de recepción, reloj monotónico, connection/session ID y secuencia local; rechazar o degradar trading ante clock drift fuera del límite.

**Gate 3 — smoke de 60 minutos:**

- flujo continuo y consultable;
- reinicio sin explosión de duplicados;
- mensaje malformado no tumba el proceso;
- desconexión simulada se recupera;
- métricas y logs permiten reconstruir el incidente.

---

## Bloque 4 — Validación de ingestión por 24 horas y restauración

**Objetivo:** demostrar que los datos son operables antes de investigar modelos. La corrida de 24 horas es el mínimo de ingeniería del borrador; se recomienda extenderla a 72 horas, incluyendo una desconexión inducida, antes de promover el pipeline a investigación formal.

**Crear:**

- `scripts/ingestion_report.py`
- `scripts/backup.sh`
- `scripts/restore.sh`
- `docs/operations/collector-runbook.md`
- `docs/operations/backup-restore.md`
- `research/reports/ingestion-<run-id>.md`

**Pasos:**

1. Crear `IngestionRun` con configuración y timestamps congelados.
2. Ejecutar collector durante al menos 24 horas.
3. Medir runtime, uptime, símbolos, ticks, duplicados, gaps, reconexiones, mensajes inválidos, p50/p95/p99 de latencia y crecimiento de DB.
4. Contrastar conteos entre stream, buffer y registros persistidos.
5. Reiniciar deliberadamente collector y PostgreSQL en una ventana controlada.
6. Verificar recuperación e identificación del gap.
7. Crear backup consistente.
8. Restaurar en una base desechable y comparar conteos/checksums.
9. Estimar almacenamiento diario/mensual con observaciones reales, no con supuestos.
10. Corregir y repetir si hay pérdida silenciosa, duplicación no acotada o incapacidad de restaurar.
11. Definir y comprobar RPO/RTO; cifrar la copia fuera del host y verificar que no contenga PAT, OTP ni secretos de logs.
12. Cuando `ticks_history` sea aplicable, usarlo para diagnosticar/reconciliar gaps sin ocultar que el stream estuvo interrumpido.

**Gate 4:** informe firmado por hash, SLO/RPO/RTO definidos antes de la corrida, cero terminaciones no recuperadas, cero pérdida silenciosa conocida, gaps clasificados, idempotencia sin eliminar ticks legítimos y restore drill exitoso. No empezar ML antes de aprobarlo.

---

## Bloque 5 — Snapshots inmutables y pipeline de features

**Objetivo:** transformar datos sin perder trazabilidad ni introducir futuro.

**Archivos previstos:**

- `src/devsoul_quant/datasets/snapshot.py`
- `src/devsoul_quant/datasets/manifest.py`
- `src/devsoul_quant/features/base.py`
- `src/devsoul_quant/features/transparent_v1.py`
- `src/devsoul_quant/evaluation/splits.py`
- `research/protocols/<hypothesis-id>.yaml`

**Pasos:**

1. Probar snapshot con rango temporal cerrado, orden determinista y misma salida byte/hash cuando entradas/configuración coinciden.
2. Exportar Parquet y un manifiesto JSON con consulta, schema, filas, min/max time, código y SHA-256.
3. Probar rechazo de snapshots incompletos o rutas fuera del almacén permitido.
4. Definir interfaz `FeatureSet` con versión y lookback explícitos.
5. Implementar una sola feature transparente mediante TDD.
6. Probar que al modificar ticks futuros no cambia ninguna feature pasada.
7. Repetir verticalmente para retornos rezagados, rolling mean/std, momentum y dirección.
8. Definir temporal holdout y walk-forward expanding/rolling.
9. Probar fronteras, ventanas vacías, warm-up y etiquetas solapadas.
10. Incorporar purga/embargo si la duración del contrato hace que muestras vecinas compartan información.
11. Registrar dataset, features, split, semilla y SHA de código en `Experiment`.

**Gate 5:** misma entrada + configuración + commit produce mismos hashes y métricas; una suite adversarial de no-lookahead permanece verde.

---

## Bloque 6 — Propuestas y economía contractual observable

**Objetivo:** evitar backtests basados en payouts inventados.

**Archivos previstos:**

- `src/devsoul_quant/adapters/deriv/proposals.py`
- `src/devsoul_quant/domain/contracts/proposal.py`
- `src/devsoul_quant/adapters/persistence/proposal_repository.py`
- migración `contract_proposals`.

**Pasos:**

1. Seleccionar un conjunto pequeño de `ContractSpec` aprobado en el protocolo.
2. Probar request/response de propuesta con fixtures del esquema actual.
3. Persistir request canónica, respuesta cruda, payout, ask price, spot, validez y latencia.
4. Evitar secretos y datos privados en payload/log.
5. Diseñar muestreo que respete límites oficiales y mida throttling.
6. Correlacionar propuesta con tick y reloj sin suponer simultaneidad perfecta.
7. Detectar expiración, rechazo y cambio de propuesta.
8. Versionar el método de estimación cuando falte una propuesta histórica.
9. Etiquetar toda simulación como `OBSERVED`, `ESTIMATED` o `UNAVAILABLE` en su economía.
10. Nombrar explícitamente los modos de evidencia: `TICK_PROXY_BACKTEST` para economía inferida y `QUOTE_REPLAY_BACKTEST` para propuestas capturadas.

**Gate 6:** existe suficiente evidencia para calcular P/L con propuesta observada en el piloto, o el informe declara explícitamente que aún no puede validar rentabilidad contractual. Ningún resultado exclusivamente `TICK_PROXY_BACKTEST` puede promover una estrategia a demo.

---

## Bloque 7 — Backtester determinista y ledger de simulación

**Objetivo:** simular el ciclo completo usando el mismo núcleo de decisión/riesgo que tiempo real.

**Archivos previstos:**

- `src/devsoul_quant/backtesting/engine.py`
- `src/devsoul_quant/backtesting/events.py`
- `src/devsoul_quant/adapters/paper/broker.py`
- `src/devsoul_quant/evaluation/metrics.py`
- fixtures congeladas en `tests/regression/fixtures/`.

**Pasos:**

1. Crear una secuencia mínima conocida y escribir el resultado esperado antes del motor.
2. Implementar cola determinista con regla de orden para timestamps iguales.
3. Hacer pasar un tick → feature → intent → risk decision → paper contract → settlement.
4. Probar que no se puede actuar con datos posteriores al decision time.
5. Probar máximo de posiciones, cooldown, rechazo y expiración.
6. Probar P/L, balances antes/después y conservación contable con `Decimal`.
7. Probar que una pérdida no puede eliminarse ni reescribirse.
8. Implementar métricas una por una con fixtures calculables a mano.
9. Definir explícitamente unidades y anualización de Sharpe/Sortino; no aplicar fórmulas de retornos diarios ciegamente a contratos discretos.
10. Implementar drawdown, EV, profit factor, wait rate, exposición, rachas e intervalos bootstrap apropiados para dependencia temporal.
11. Crear golden report y test de regresión; cualquier cambio exige explicación/versionado.
12. Comparar Always-WAIT, decisión aleatoria, momentum y mean reversion antes de ML.

**Gate 7:** resultados deterministas, reconciliación contable exacta, suite de leakage verde y métricas separadas por split/fold/modo.

---

## Bloque 8 — Protocolo científico y modelos baseline

**Objetivo:** buscar evidencia sin sobreajustar ni convertir el test final en validación iterativa.

**Pasos:**

1. Registrar una hipótesis en `research/protocols/` antes de abrir el test.
2. Definir baseline, métrica primaria, límites de riesgo y tamaño mínimo de muestra.
3. Ejecutar baseline aleatorio con múltiples semillas y Always-WAIT como control.
4. Ejecutar reglas simples congeladas.
5. Añadir regresión logística mediante un ciclo TDD sobre una fixture sintética.
6. Añadir árbol pequeño/random forest solo si responde una hipótesis concreta.
7. Ajustar exclusivamente con train; decidir con validation.
8. Ejecutar walk-forward y reportar todos los folds, incluyendo los malos.
9. Corregir por múltiples búsquedas/modelos o declarar el riesgo de selección.
10. Congelar `StrategyRelease` antes de abrir test.
11. Evaluar test una sola vez por release.
12. Publicar resultados positivos o negativos con hashes y limitaciones.
13. Usar intervalos adecuados para dependencia temporal (por ejemplo, block bootstrap cuando proceda), no bootstrap IID por defecto.
14. Publicar análisis de sensibilidad a payouts/costos adversos razonables y los supuestos del cálculo de riesgo de ruina.

**Gate A — Research:** experimento reproducible, sin leakage, mejora al baseline y EV de validación positivo bajo el criterio pre-registrado.

**Gate B — Holdout:** release congelado y, como regla base, límite inferior del intervalo de confianza pre-registrado de EV OOS por encima del umbral definido, mejora sobre baseline económico, drawdown dentro del límite y tamaño efectivo de muestra mínimo. El protocolo puede justificar otra regla, pero debe congelarla antes de abrir el holdout.

**Gate C — Walk-forward:** evidencia OOS no concentrada en un único fold/régimen y ausencia de fold catastrófico según umbral registrado.

Si falla un gate, no “arreglar” el mismo test: crear una hipótesis/release nueva y conservar el fracaso anterior.

---

## Bloque 9 — Realtime paper trading

**Objetivo:** probar el sistema completo sin depender aún de autenticación/ejecución demo.

**Archivos previstos:**

- `src/devsoul_quant/application/services/realtime_engine.py`
- `src/devsoul_quant/domain/risk/engine.py`
- `src/devsoul_quant/adapters/paper/broker.py`
- `apps/trader/main.py`

**Pasos:**

1. Reproducir en streaming una fixture que ya pasó por backtest y comparar decisiones exactas.
2. Implementar estado incremental de features con warm-up explícito.
3. Hacer que datos stale/gaps bloqueen nuevas entradas.
4. Implementar riesgo con límites versionados, no constantes ocultas.
5. Probar kill switch, pérdida diaria, drawdown, exposición, posiciones y racha de pérdidas.
6. Persistir señal e intento antes de ejecutar; correlacionar todos los eventos.
7. Implementar outbox/idempotencia para sobrevivir caída entre decisión y registro.
8. Reconciliar posiciones al reiniciar antes de aceptar nuevos eventos.
9. Registrar downtime e intervención manual en `ValidationRun`.
10. Ejecutar paper sin supervisión por el periodo y número de decisiones definidos en el protocolo.
11. Comparar paper con replay/backtest sobre el mismo intervalo y explicar divergencias.

**Gate D — Paper:** estabilidad operativa, trazabilidad 100 %, reconciliación contable, divergencias explicadas y métricas dentro del protocolo pre-registrado.

---

## Bloque 10 — Adaptador Deriv demo

**Objetivo:** ejecutar y reconciliar contratos exclusivamente en cuenta demo.

**Prerrequisitos:** Gates A–D aprobados, aplicación Deriv registrada, credencial demo disponible localmente y revisión vigente de esquemas/límites.

**Archivos previstos:**

- `src/devsoul_quant/adapters/deriv/auth.py`
- `src/devsoul_quant/adapters/deriv/demo_broker.py`
- `src/devsoul_quant/adapters/deriv/reconciliation.py`
- `tests/contract/deriv/`
- `tests/e2e/test_demo_trade_opt_in.py`

**Pasos:**

1. Probar que configuración real/endpoint no-demo impide arrancar.
2. Implementar PAT/OAuth + App ID según documentación actual, sin imprimir secretos.
3. Obtener URL demo/OTP mediante REST actual; no construir manualmente una URL legacy.
4. Probar propuesta demo y su expiración.
5. Implementar compra idempotente dentro de lo permitido por la API.
6. Suscribirse a `proposal_open_contract` y persistir cada transición cruda.
7. Implementar cierre solo cuando el contrato lo permita.
8. Reconciliar ledger interno con contrato, payout, profit y balance externos.
9. Ante timeout ambiguo, consultar/reconciliar antes de reintentar compra.
10. Probar reconexión con posición abierta.
11. Probar kill switch: bloquea nuevas entradas y define claramente qué ocurre con posiciones existentes.
12. Ejecutar una operación e2e opt-in con stake demo mínimo permitido y aprobación humana explícita para la prueba.
13. Ejecutar validación continua demo según protocolo congelado.

**Gate E — Demo:** lifecycle externo completo persistido, cero duplicación por retries, reconciliación exacta o diferencias explicadas, economía observada compatible con el modelo y dinero real técnicamente inaccesible.

---

## Bloque 11 — API y dashboard de evidencia

**Objetivo:** permitir que un socio entienda qué se probó, cuándo, en qué modo y con qué resultado, sin editar el pasado.

**Pasos:**

1. Implementar `/health/live` y `/health/ready` separados.
2. Implementar estado del collector, conexión, último tick, gaps y run activo.
3. Exponer endpoints de solo lectura para experimentos, validation runs, señales, decisiones de riesgo, contratos y métricas.
4. Excluir mutaciones de trades históricos.
5. Crear dashboard mínimo server-rendered o Streamlit; decidir mediante spike de un día y escoger la opción con menor superficie operativa.
6. Mostrar de forma prominente `BACKTEST`, `PAPER` o `DERIV DEMO` en cada vista.
7. Mostrar periodo, universo, contrato, release, dataset y Git SHA.
8. Graficar equity, drawdown, P/L diario y operaciones acumuladas.
9. Mostrar resultados negativos, downtime y runs invalidados, no solo el mejor run.
10. Probar accesibilidad básica, rangos vacíos, timezone y datasets grandes.
11. Mantener bind local por defecto y documentar acceso remoto privado (VPN/Tailscale equivalente).
12. Generar un informe estático mínimo desde el primer gate de datos; el dashboard interactivo no debe bloquear evidencia temprana.

**Gate 11:** una persona no técnica puede identificar modo, periodo, estrategia, riesgo, tamaño de muestra y limitaciones; nunca puede confundir demo con dinero real.

---

## Bloque 12 — Hardening, operación y cierre del MVP

**Objetivo:** demostrar que el laboratorio es recuperable, seguro y mantenible.

**Pasos:**

1. Threat model local: secretos, dashboard, DB, backups, supply chain y ejecución accidental.
2. Rotación de credenciales demo y verificación de redaction de logs.
3. Escaneo de dependencias/secretos y SBOM.
4. Backup automático cifrado fuera del equipo y segundo restore drill.
5. Runbooks de caída WS, DB llena, disco lleno, datos stale, clock skew y posición huérfana.
6. Alertas locales para collector caído, gap, DB lenta, posición no reconciliada y kill switch.
7. Prueba de soak y reinicios controlados.
8. Medir CPU, RAM, I/O, almacenamiento y latencias con carga real.
9. Estimar costo local y documentar qué evidencia justificaría cloud, TimescaleDB, GPU o mayor hardware.
10. Revisión independiente de seguridad, leakage, contabilidad y reproducibilidad.
11. Crear informe final que incluya también estrategias fallidas.
12. Congelar release MVP v0.1 solo si todos los gates técnicos aplicables están aprobados.

**Gate final MVP:** ingestión continua, datasets y experimentos reproducibles, backtest resistente a leakage, paper automatizado, demo reconciliada, ledger íntegro, dashboard entendible y una conclusión honesta sobre la existencia o ausencia de ventaja estadística.

---

## 6. Matriz de pruebas mínima

| Capa | Prueba obligatoria | Evidencia |
|---|---|---|
| Dominio | invariantes, estados y `Decimal` | unit tests |
| Deriv | mensajes contra schemas/fixtures versionadas | contract tests |
| Persistencia | migraciones, constraints, idempotencia y concurrencia | PostgreSQL real |
| Collector | reconnect, gaps, malformed, backpressure | integración + soak |
| Features | causality/no-lookahead y warm-up | unit + property tests |
| Splits | límites temporales, purga/embargo | unit tests |
| Backtester | reloj, orden, P/L y golden fixtures | regression tests |
| Riesgo | cada rechazo y kill switch | unit + integración |
| Paper | replay equivalente y recuperación | integration/e2e |
| Demo | propuesta-compra-seguimiento-reconciliación | e2e opt-in |
| API | contratos, filtros, errores, solo lectura | integration |
| Dashboard | etiquetas de modo y rangos | browser smoke |
| Operación | backup/restore y restart | drill documentado |

Comando de gate esperado al madurar el proyecto:

```bash
make verify             # unit, static checks y pruebas sin red
make test-integration   # PostgreSQL real en Compose
make test-contract      # fixtures del schema oficial
make test-regression    # resultados congelados
make smoke-deriv-public # opt-in, sin credenciales
make e2e-demo           # opt-in, credencial demo y guardas
```

---

## 7. Secuencia de entregas demostrables al socio

1. **Evidencia 1 — Laboratorio reproducible:** clon limpio, Compose y suite verde.
2. **Evidencia 2 — Datos propios:** inventario de instrumentos y reporte de ingestión de 24 h.
3. **Evidencia 3 — Investigación auditable:** snapshot, protocolo y baselines reproducibles.
4. **Evidencia 4 — Backtest creíble:** no-lookahead, economía etiquetada y folds visibles.
5. **Evidencia 5 — Paper en vivo:** run congelado, decisiones completas y downtime visible.
6. **Evidencia 6 — Demo reconciliada:** contratos externos enlazados al ledger.
7. **Evidencia 7 — Decisión:** continuar, rediseñar o detener con criterios previamente acordados.

Cada entrega debe incluir: versión, periodo, hashes, comandos de reproducción, resultado, limitaciones y decisión del gate.

---

## 8. Riesgos principales y mitigación

### Científicos

- **Sobreajuste por probar muchas ideas:** protocolo previo, test sellado, registro de todos los experimentos y ajuste por múltiples comparaciones.
- **Leakage temporal:** reloj inyectado, features causales, purga/embargo y fixtures adversariales.
- **Muestra insuficiente/no estacionaria:** criterios por operaciones y duración; walk-forward y análisis por régimen.
- **Métrica inadecuada:** EV/P&L/riesgo como primarias; accuracy solo como diagnóstico.

### De mercado/ejecución

- **Payout histórico no observable:** capturar propuestas y etiquetar estimaciones.
- **Divergencia backtest-demo:** mismo core, reconciliación y gate específico.
- **Reintento duplica compra:** idempotencia y reconciliación antes de reintentar.
- **Semántica contractual incorrecta:** inventario `contracts_for`, schemas fijadas y ADR.

### Técnicos

- **Pérdida/duplicación de ticks:** claves basadas en schema real, batch transaccional, gap ledger.
- **Estado corrupto tras reinicio:** outbox, replay y reconciliación.
- **Disco/DB crecen sin control:** medición 24 h, retención, Parquet y alertas.
- **Dependencia de notebooks:** toda lógica productiva vive en `src/`; notebooks solo consumen APIs.

### Seguridad/regulación

- **Ejecución real accidental:** ausencia de adaptador real, allowlist demo y fail-closed.
- **Exposición del dashboard:** bind local y acceso privado.
- **Secretos en Git/log:** scanning, redaction y `.env` ignorado.
- **Interpretación como oferta financiera:** disclaimers, demo claramente etiquetada y revisión jurídica antes de SaaS/terceros.

---

## 9. Decisiones que no bloquean el bootstrap pero sí gates posteriores

Estas preguntas deben resolverse con datos, no por intuición:

1. ¿Qué familia de contratos inicial tiene economía observable y suficiente frecuencia?
2. ¿Qué símbolos quedan en el universo piloto tras inventario y calidad de datos?
3. ¿Cuál es la unidad exacta de cada observación/label y cuándo se conoce el resultado?
4. ¿Cuántas operaciones y cuánto tiempo exige el protocolo para cada gate?
5. ¿Qué umbral de drawdown y riesgo de ruina acepta DevSoul antes de ver resultados?
6. ¿Polars o pandas ofrece mejor equilibrio para el volumen observado?
7. ¿Dashboard FastAPI server-rendered o Streamlit minimiza complejidad operativa real?
8. ¿Qué mecanismo de backup externo cifrado está disponible en el hardware local?
9. ¿Qué revisión jurídica se requiere antes de mostrar resultados fuera del equipo o discutir un SaaS?

---

## 10. Orden inmediato recomendado

No empezar por modelos ni dashboard. El orden de trabajo inmediato es:

1. Bloque 0 completo: contrato del MVP y schemas Deriv vigentes.
2. Bloque 1: bootstrap verificable.
3. Bloque 2: dominio/reloj/guardas demo-only.
4. Bloque 3: tracer vertical de un símbolo configurado.
5. Bloque 4: corrida real de 24 h y restore drill.
6. Solo después: snapshots, economía contractual, backtester y estrategias.

Los commits convencionales son checkpoints recomendados, pero Hermes no debe crear ninguno sin autorización explícita. Después de cada bloque se debe presentar diff, resultados de comandos y evidencia del gate antes de continuar.
