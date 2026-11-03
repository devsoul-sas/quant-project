# Dashboard demo para usuarios y socios — Plan de implementación

> **Para Hermes:** implementar este plan por tareas con TDD estricto y revisión de seguridad/validez cuantitativa después de cada bloque. El usuario autoriza cambios locales, pero no commit, push, despliegue, migraciones remotas ni dinero real.

**Objetivo:** reemplazar la experiencia principal por consola con una aplicación web local usable que ejecute evaluaciones Deriv demo efímeras, muestre progreso y estadísticas honestas, y permita presentar la viabilidad técnica a socios sin persistir market data restringida ni afirmar rentabilidad.

**Arquitectura:** conservar el núcleo Python actual como única fuente de verdad. Añadir una capa web local (`127.0.0.1`) que invoque servicios de aplicación, mantenga cada ejecución en memoria y renderice un dashboard server-side. La UI nunca implementará estrategia, riesgo o métricas por su cuenta. Los reportes compartibles usarán únicamente datos sintéticos propios mientras no exista licencia escrita para persistir derivados de Deriv.

**Stack propuesto:** Python 3.13, FastAPI, Uvicorn, Jinja2, HTML/CSS accesible y SVG generado localmente; sin CDN ni framework JavaScript pesado. SSE para progreso de ejecución. Tests con pytest y cliente ASGI.

---

## 1. Decisiones de producto

### Usuario operador

Flujo objetivo:

1. Abrir `DevSoul Quant` desde un lanzador local o `uv run devsoul-quant dashboard`.
2. Ver estado de configuración sin revelar secretos: App ID configurado, PAT configurado, cuenta demo detectada.
3. Elegir símbolo, cantidad de ticks, duración y folds mediante controles con límites seguros.
4. Pulsar **Iniciar evaluación demo**.
5. Ver progreso: autenticación, cuenta demo, OTP, conexión, ticks recibidos, evaluación y cierre.
6. Ver un resumen comprensible y luego los detalles técnicos.
7. Comparar ejecuciones solo durante la sesión actual.
8. Cerrar la sesión y descartar automáticamente ticks, OTP y resultados derivados no autorizados.

### Socio potencial

El modo presentación debe mostrar:

- estado demo-only y ausencia estructural de dinero real;
- salud de integración y tiempo de ejecución;
- tamaño de muestra y decisiones válidas;
- tasa de acierto direccional, tasa de no-trade y racha máxima de pérdidas;
- resultados por fold temporal y dispersión entre folds;
- intervalo block-bootstrap marcado como descriptivo/no inferencial;
- integridad y versión del motor;
- límites visibles: sin P/L, ROI, payout ni afirmación de rentabilidad;
- origen y derechos de cada evidencia.

No mostrar como evidencia comercial persistente:

- ticks o precios Deriv;
- series temporales reconstruibles;
- URLs OTP, PAT, App ID completo o account ID;
- capturas/exportaciones con datos derivados de Deriv sin autorización escrita;
- una tasa direccional como si fuera retorno económico.

Para una presentación compartible o enviada por correo se usará el pipeline sintético propio. La sesión Deriv demo puede mostrarse en vivo y desaparecer al cerrar.

---

## 2. Arquitectura propuesta

```text
Browser local
    │ HTTP/SSE en 127.0.0.1
    ▼
FastAPI web adapter
    │ DTOs sin secretos ni ticks
    ▼
DemoEvaluationService
    ├── OTP resolver demo-only
    ├── bounded ephemeral collector
    ├── live evaluation core
    └── in-memory session registry

Synthetic partner evidence
    └── export permitido desde pipeline propio
```

Reglas:

- bind exclusivo a `127.0.0.1` por defecto;
- sin autenticación remota porque no se expone a red; si se habilita red, debe diseñarse un proyecto de seguridad separado;
- PAT/App ID permanecen en variables del proceso o keyring; nunca se envían al HTML, JavaScript, logs o almacenamiento del navegador;
- registro de sesión con TTL corto y `clear()` explícito;
- una sola evaluación activa por sesión para evitar consumo y estados ambiguos;
- cancelación siempre envía `forget` o cierra el socket;
- CSP sin scripts remotos; gráficos SVG/HTML locales;
- modo real y `/ws/real` ausentes por construcción.

---

## 3. Tareas de implementación

### Tarea 1: Contrato de vista seguro

**Objetivo:** definir DTOs del dashboard que no puedan contener ticks, precios ni secretos.

**Archivos:**
- Crear: `src/devsoul_quant/application/dashboard.py`
- Crear: `tests/application/test_dashboard.py`

**TDD:**

1. Escribir pruebas que construyan `DashboardRunView` desde `LiveEvaluationReport`.
2. Exigir campos de estado, métricas agregadas, advertencias y versiones.
3. Comprobar que `to_dict()` no contiene `tick`, `quote`, `otp`, `token`, `url`, `profit`, `roi`, `payout` ni `balance`.
4. Ejecutar la prueba y confirmar RED.
5. Implementar el mapeo mínimo e inmutable.
6. Ejecutar focalizadas y suite de aplicación.

### Tarea 2: Servicio de ejecución con progreso y cancelación

**Objetivo:** sacar la orquestación de la CLI para que consola y web compartan exactamente la misma ruta.

**Archivos:**
- Crear: `src/devsoul_quant/application/demo_evaluation_service.py`
- Modificar: `src/devsoul_quant/cli.py`
- Crear: `tests/application/test_demo_evaluation_service.py`
- Modificar: `tests/test_cli_live.py`

**TDD:**

1. Definir estados `PENDING`, `AUTHENTICATING`, `COLLECTING`, `EVALUATING`, `COMPLETED`, `FAILED`, `CANCELLED`.
2. Probar transiciones válidas y rechazo de saltos inválidos.
3. Probar que los errores públicos son genéricos y no incluyen secretos.
4. Probar cancelación y liberación del colector.
5. Implementar servicio inyectando OTP, colector y reloj.
6. Refactorizar CLI para usar el servicio sin cambiar su JSON público.

### Tarea 3: Registro efímero de sesiones

**Objetivo:** permitir que la web consulte progreso/resultados sin base de datos.

**Archivos:**
- Crear: `src/devsoul_quant/adapters/web/session_store.py`
- Crear: `tests/adapters/web/test_session_store.py`

**TDD:**

1. Probar IDs aleatorios no predecibles.
2. Probar TTL de sesión y borrado explícito.
3. Probar que solo admite DTOs agregados, nunca `Tick`.
4. Probar máximo de sesiones y fail-closed al excederlo.
5. Implementar almacenamiento en memoria con lock.

### Tarea 4: Aplicación FastAPI local-only

**Objetivo:** exponer configuración, inicio, progreso, resultado y cancelación.

**Archivos:**
- Modificar: `pyproject.toml` y `uv.lock` para FastAPI, Uvicorn, Jinja2 y dependencias de prueba ASGI.
- Crear: `src/devsoul_quant/adapters/web/app.py`
- Crear: `tests/adapters/web/test_app.py`

**Endpoints mínimos:**

- `GET /` — dashboard.
- `GET /api/config-status` — booleanos, nunca valores.
- `POST /api/runs` — inicia una evaluación con límites server-side.
- `GET /api/runs/{id}` — estado/resultados agregados.
- `GET /api/runs/{id}/events` — SSE de progreso.
- `DELETE /api/runs/{id}` — cancela y limpia.
- `GET /healthz` — salud local.

**Pruebas obligatorias:**

- binding documentado a localhost;
- `/ws/real`, modo real y valores fuera de límites rechazados;
- respuestas sin secretos/ticks;
- cabeceras CSP, `nosniff`, `no-store`, frame deny;
- errores 4xx/5xx sin detalles internos;
- no endpoint de exportación para una sesión Deriv.

### Tarea 5: UI usable y accesible

**Objetivo:** ofrecer un flujo de un clic y métricas comprensibles.

**Archivos:**
- Crear: `src/devsoul_quant/adapters/web/templates/dashboard.html`
- Crear: `src/devsoul_quant/adapters/web/static/dashboard.css`
- Crear: `src/devsoul_quant/adapters/web/static/dashboard.js`
- Crear: `tests/adapters/web/test_dashboard_html.py`

**Componentes:**

- encabezado con insignias `DEMO`, `PAPER`, `SIN DINERO REAL`;
- estado seguro de credenciales: configurado/no configurado;
- formulario con presets seguros;
- barra de progreso y botón cancelar;
- tarjetas de muestra, decisiones, hit rate, no-trade y loss streak;
- gráfico SVG por folds y banda descriptiva del bootstrap;
- panel “Qué significa / qué no significa” siempre visible;
- sección técnica colapsable con versión, provenance, purge y block size;
- botón **Nueva evaluación** que limpia la anterior.

**Accesibilidad:** labels reales, navegación por teclado, `aria-live` para progreso, contraste AA, no depender solo del color.

### Tarea 6: Comando de lanzamiento

**Objetivo:** que la consola no sea la experiencia cotidiana.

**Archivos:**
- Modificar: `src/devsoul_quant/cli.py`
- Crear: `tests/test_cli_dashboard.py`
- Crear opcional: `scripts/start-dashboard.sh`

**Comportamiento:**

```bash
uv run devsoul-quant dashboard
```

- inicia en `127.0.0.1` con puerto configurable y seguro;
- abre el navegador local opcionalmente;
- no imprime secretos;
- rechaza `0.0.0.0` salvo una futura decisión explícita de seguridad;
- cierra limpiamente y borra sesiones al recibir SIGINT/SIGTERM.

Después puede añadirse un `.desktop` local para abrirlo desde el menú de Fedora sin terminal.

### Tarea 7: Modo presentación para socios

**Objetivo:** separar demostración en vivo de evidencia compartible.

**Archivos:**
- Crear: `src/devsoul_quant/application/partner_view.py`
- Crear: `tests/application/test_partner_view.py`
- Modificar: `docs/partner/demo-evidence-guide.md`

**Dos fuentes visualmente distintas:**

1. **Deriv demo efímera:** visible solo en la sesión, marcada `LIVE DEMO / NON-PERSISTENT / NON-ECONOMIC`.
2. **Evidencia sintética propia:** exportable y reproducible, marcada `SYNTHETIC / OWNED / ENGINEERING EVIDENCE`.

No debe existir botón “Exportar” para Deriv hasta que un manifest de derechos aprobado lo autorice. El paquete sintético sí puede generar HTML/PDF sin datos de terceros.

### Tarea 8: Revisión y gates

**Comandos:**

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run mypy src
uv build
uv run pytest
./scripts/verify.sh
./scripts/verify-research.sh
```

**Revisión independiente:**

- secretos y URL OTP;
- CSP y exposición de red;
- persistencia accidental en browser/server/logs;
- causalidad y validez de métricas;
- ausencia estructural de ejecución real;
- UX con una persona no técnica.

---

## 4. Métricas del dashboard

### Permitidas en Deriv demo efímera

- ticks recibidos y expirados;
- duración de la ejecución;
- decisiones totales;
- entradas y no-trades;
- tasa direccional;
- racha de pérdidas;
- métricas por fold purgado;
- intervalo block-bootstrap descriptivo;
- estado de integración, ledger y versión;
- `profitability_claim=false` y `NOT_ELIGIBLE`.

### Bloqueadas hasta disponer de economía observada/licenciada

- P/L y balance;
- ROI;
- payout;
- expected value;
- drawdown monetario;
- Sharpe/Sortino monetario;
- afirmaciones de edge o rentabilidad;
- proyecciones de crecimiento.

### Siguiente nivel económico demo

Si se necesita mostrar economía con saldo virtual de Deriv, debe abrirse un bloque separado:

1. revalidar documentación y términos actuales de proposal/buy/open-contract;
2. implementar solo cuenta demo y `/ws/demo`;
3. máximo stake virtual y confirmación explícita;
4. registrar provenance `DERIV_DEMO_OBSERVED`, no “real”;
5. no persistir propuestas/contratos sin derecho escrito;
6. nunca usar estos resultados como prueba de rentabilidad sin protocolo y muestra suficiente.

---

## 5. Riesgos y decisiones abiertas

- **Persistencia de agregados Deriv:** mantener bloqueada hasta aclaración contractual; sesión en memoria solamente.
- **Credenciales entre reinicios:** elegir keyring del sistema antes que archivo; si se usa archivo local, `0600`, ignorado por Git y nunca servido al navegador.
- **Charts:** preferir SVG propio para no depender de CDN ni `unsafe-inline`.
- **Compartir con socios remotamente:** usar export sintético; no exponer el servidor local ni desplegar el feed Deriv.
- **Economía demo:** es una fase posterior y no sustituye evidencia histórica licenciada.
- **Producto final:** una app web local-first es el camino recomendado; una interfaz de escritorio nativa no aporta suficiente valor en esta etapa.

## 6. Criterio de éxito

Una persona no técnica puede iniciar una evaluación demo, entender el resultado y sus límites sin usar comandos ni ver JSON. Un socio puede observar viabilidad técnica, controles de riesgo, causalidad y disciplina científica, pero no puede confundir el dashboard con evidencia de rentabilidad. Ningún secreto, tick, precio, OTP o URL autenticada queda persistido o expuesto.