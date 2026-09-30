# Siguiente etapa provider-agnostic de DevSoul Quant

> **Para Hermes:** implementar este plan por tareas con TDD estricto y revisión independiente. No conectar dinero real ni persistir contenido Deriv.

**Objetivo:** convertir el vertical slice sintético ya aprobado en un núcleo completo, persistente y operable que pueda reutilizarse después con cualquier proveedor licenciado.

**Arquitectura:** mantener el dominio puro y determinista; introducir puertos de aplicación para reloj, broker y ledger; usar adaptadores PostgreSQL únicamente para eventos propios/sintéticos. El slice actual continúa siendo el tracer end-to-end y ningún adaptador real entra en alcance.

**Stack:** Python 3.13.13, Pydantic 2, PostgreSQL 17 local, SQLAlchemy 2/Alembic solo cuando el puerto y sus invariantes estén definidos, pytest, Ruff, mypy strict, uv 0.12.21.

---

## Estado de partida

- `main` limpio y sincronizado con `origin/main` en `043126a`.
- CLI sintética reproducible, riesgo fail-closed, paper broker y ledger verificable.
- 77 pruebas, cobertura 98.73%, build y CI verdes.
- Gate 0 Deriv bloqueado por licencia de retención.
- Prohibido implementar `DerivRealBroker`, `/ws/real`, compra real o persistencia de datos Deriv.

## Orden recomendado

### Tarea 1: reloj inyectable y eventos reproducibles

**Objetivo:** eliminar timestamps derivados implícitamente y preparar replay, expiraciones y políticas temporales sin reloj del sistema dentro del dominio.

**Archivos:**
- Crear: `src/devsoul_quant/application/ports/clock.py`
- Crear: `src/devsoul_quant/adapters/clock/system.py`
- Crear: `src/devsoul_quant/adapters/clock/replay.py`
- Modificar: `src/devsoul_quant/application/demo.py`
- Crear: `tests/application/ports/test_clock.py`
- Modificar: `tests/application/test_demo.py`

**TDD:**
1. Prueba RED: `ReplayClock` devuelve instantes UTC conocidos y avanza únicamente de forma explícita.
2. Prueba RED: rechaza timestamps naive y retrocesos temporales.
3. Implementar `Clock` como `Protocol`, `ReplayClock` determinista y `SystemClock` UTC.
4. Inyectar el reloj en `run_synthetic_demo`; mantener salida byte-a-byte estable con un reloj equivalente.
5. Ejecutar: `uv run pytest tests/application/ports/test_clock.py tests/application/test_demo.py -q`.

### Tarea 2: completar entidades del Gate 2

**Objetivo:** cubrir las invariantes todavía ausentes sin adaptar aún PostgreSQL ni proveedores.

**Archivos:**
- Crear: `src/devsoul_quant/domain/money.py`
- Crear: `src/devsoul_quant/domain/trading.py`
- Crear: `src/devsoul_quant/domain/experiments.py`
- Crear: `tests/domain/test_money.py`
- Crear: `tests/domain/test_trading.py`
- Crear: `tests/domain/test_experiments.py`

**TDD por comportamiento:**
1. `Money` conserva moneda, cuantización y precisión Decimal; rechaza NaN/infinito/float.
2. `Trade` permite solo transiciones legales y nunca cambia eventos históricos.
3. `Adjustment` referencia el evento corregido y no lo reemplaza.
4. `StrategyRelease` queda congelado al iniciar validación.
5. `ValidationRun` congela hashes de dataset, código, features, estrategia, contrato y riesgo.
6. Separar claramente métricas técnicas de evidencia económica.

### Tarea 3: definir puertos de aplicación antes de SQL

**Objetivo:** impedir que dominio y casos de uso dependan de SQLAlchemy o de tipos Deriv.

**Archivos:**
- Crear: `src/devsoul_quant/application/ports/ledger.py`
- Crear: `src/devsoul_quant/application/ports/broker.py`
- Crear: `src/devsoul_quant/application/ports/market_data.py`
- Modificar: `src/devsoul_quant/application/paper.py`
- Modificar: `src/devsoul_quant/application/demo.py`
- Crear pruebas de contrato bajo `tests/application/ports/`.

**Criterios:**
- `LedgerPort`: append idempotente, lectura ordenada y verificación.
- `BrokerPort`: propuesta, apertura paper, observación y cierre; nunca `BUY/SELL` genérico.
- `MarketDataPort`: origen y licencia/provenance explícitos.
- Ningún puerto importa `adapters`, SQLAlchemy o Deriv.

### Tarea 4: PostgreSQL append-only para datos propios

**Objetivo:** persistir únicamente eventos propios/sintéticos y demostrar protección contra mutación.

**Prerequisito:** inspeccionar `pyproject.toml`; añadir SQLAlchemy/Alembic solo si todavía no existen.

**Archivos:**
- Crear: `src/devsoul_quant/adapters/persistence/models.py`
- Crear: `src/devsoul_quant/adapters/persistence/ledger_repository.py`
- Crear: `alembic.ini`, `migrations/env.py` y migración inicial (si aún no existen)
- Crear: `tests/integration/persistence/test_ledger_repository.py`
- Modificar: `compose.yaml` solo si hacen falta roles separados.

**TDD/integración:**
1. Insertar cadena y leerla en el mismo orden.
2. Retry exacto devuelve el evento existente; conflicto con mismo ID falla.
3. Rol normal no puede ejecutar `UPDATE` ni `DELETE` sobre eventos cerrados.
4. Una corrección crea un evento `ADJUSTMENT` posterior.
5. Tampering administrativo es detectable por `verify_chain`.
6. Concurrencia real: dos inserts con el mismo ID no duplican eventos.

### Tarea 5: ejecutar el demo contra ambos ledgers

**Objetivo:** probar que el mismo caso de uso funciona con memoria y PostgreSQL sin bifurcar estrategia/riesgo/replay.

**Archivos:**
- Modificar: `src/devsoul_quant/application/demo.py`
- Modificar: `src/devsoul_quant/cli.py`
- Crear: `tests/integration/test_postgres_demo.py`
- Modificar: `README.md`

**Criterios:**
- Backend por configuración explícita: `memory` o `postgres`.
- Default seguro: `memory`.
- Misma semilla produce misma decisión, outcome y envelopes canónicos; la identidad del run puede variar solo si se documenta.
- Fallo de PostgreSQL no degrada silenciosamente a memoria.
- No se imprimen DSN ni credenciales.

### Tarea 6: gates y revisión independiente

1. `uv lock --check`.
2. `docker compose config --quiet`.
3. `./scripts/verify.sh`.
4. Integración PostgreSQL con rol restringido y concurrencia real.
5. Smoke CLI de semillas 42 y 7 para ambos backends.
6. Buscar `REAL`, `/ws/real`, tokens, secretos y afirmaciones de rentabilidad.
7. Construir wheel/sdist e instalar wheel en entorno temporal.
8. Revisión independiente de seguridad, determinismo, idempotencia y límites de licencia.
9. Commit/push únicamente con autorización explícita del usuario.

## Lo que no haremos todavía

- Collector vivo Deriv o captura persistente de ticks/propuestas.
- `QUOTE_REPLAY_BACKTEST` con contenido Deriv.
- ML, optimización o selección de estrategia por rentabilidad.
- Dashboard, API web o despliegue cloud.
- Broker real, OTP, `/ws/real` o uso de los USD 200.

## Condición para abrir la ruta Deriv

Solo después de recibir autorización escrita sustantiva sobre retención, uso derivado, duración, redistribución y uso comercial. La escalación del ticket no equivale a autorización.

## Resultado esperado

Al terminar esta etapa tendremos Gate 2 completo: dominio temporal y experimental congelado, puertos estables, ledger PostgreSQL append-only probado bajo concurrencia y el mismo demo ejecutable en memoria o SQL. Eso permite conectar más adelante un proveedor compatible sin rehacer estrategia, riesgo, replay ni auditoría.
