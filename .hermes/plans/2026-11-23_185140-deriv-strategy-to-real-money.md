# DevSoul Quant — Strategy-to-Real-Money Implementation Plan

> **For Hermes:** Implementar este plan por gates y con TDD RED → GREEN → REFACTOR. No iniciar una tarea de un gate posterior hasta que el gate anterior tenga evidencia verificable. Los commits son checkpoints sugeridos, pero requieren autorización explícita del usuario antes de ejecutarse.

> **SUPERSEDED por ADR-012 (2026-11-23).** El usuario decidió no enviar más solicitudes
> de permiso a Deriv y operar dentro del modelo efímero existente: los ticks solo se
> retienen en memoria durante la operación. En consecuencia, las tareas G1 (preflight
> legal a Deriv) y G3 (dataset legal persistente) de este documento quedan **canceladas**
> para Deriv y NO deben ejecutarse. La ruta activa es el laboratorio operativo efímero de
> `docs/adr/ADR-012-ephemeral-deriv-operation.md`: cada sesión nace sin estado, valida
> forward dentro de su TTL <24 h y elimina todo al cerrar. No se construye histórico ni se
> reclama evidencia longitudinal. Una futura ruta a dinero real requeriría una decisión de
> arquitectura y autorización humana completamente separadas, fuera de este plan.

**Goal:** Construir un programa completo y fail-closed que pueda falsificar o validar por separado Even/Odd y Multipliers, llevar una estrategia aprobada hasta operación paper/demo robusta y, solo tras desbloqueos legales, científicos, operativos y humanos, permitir evaluar un canary con capital real estrictamente limitado.

**Architecture:** Mantener el laboratorio actual como productor de evidencia y nunca como autorizador de dinero real. Separar cuatro planos: investigación, evaluación económica, ejecución demo y autorización operativa externa. `REAL` no se añade al `ExecutionMode` actual durante los gates de investigación; cualquier adaptador real será un componente nuevo y estructuralmente aislado creado únicamente después de G8.

**Tech Stack:** Python 3.13, uv, pytest, Ruff, mypy, `Decimal`, WebSocket Deriv, arquitectura hexagonal existente, reloj inyectable, replay determinista, ledger append-only y schemas Deriv fijados.

---

## 1. Decisión inmediata y estado de partida

El siguiente paso correcto **no es activar dinero real ni ampliar `demo-execute` para que compre repetidamente**. Es congelar un programa de promoción y resolver el bloqueo legal/científico.

Estado inicial del programa:

```text
program_status = NO_GO
profitability_claim = False
promotion_eligibility = NOT_ELIGIBLE
real_money = EXCLUDED
holdout_opened = False
```

Motivos:

1. Deriv permanece `EPHEMERAL_ONLY`; sus términos actuales impiden conservar el histórico y los artefactos derivados necesarios para evidencia longitudinal reproducible.
2. La implementación actual valida software e integración, no demuestra edge.
3. Even/Odd y Multipliers aún no tienen una liberación preregistrada ni evidencia forward legalmente retenible.
4. El risk gate actual solo limita importe por contrato; todavía no modela exposición agregada, drawdown, pérdida diaria/semanal, riesgo de ruina ni posiciones abiertas.
5. El laboratorio, por diseño, solo puede concluir `NO_EDGE`, `INSUFFICIENT_EVIDENCE` o `PAPER_ELIGIBLE`.

La promoción a dinero real será una **decisión humana externa** al laboratorio, nunca una salida automática del modelo.

---

## 2. Gates obligatorios

| Gate | Nombre | Estado inicial | Salida permitida |
|---|---|---:|---|
| G0 | Integridad de baseline | Parcialmente cumplido | Código reproducible y árbol auditado |
| G1 | Derechos, jurisdicción y producto | BLOQUEADO | Autorización escrita y versionada |
| G2 | Preregistro científico | Pendiente | Dos releases de hipótesis congelados |
| G3 | Dataset legal y reproducible | BLOQUEADO | Snapshot legal con manifest y hash |
| G4 | Edge económico fuera de muestra | Pendiente | `NO_EDGE`, `INSUFFICIENT_EVIDENCE` o `PAPER_ELIGIBLE` |
| G5 | Forward paper/shadow | Pendiente | Release paper estable, sin dinero |
| G6 | Ejecución demo reconciliada | Pendiente | Operación demo estable y acotada |
| G7 | Riesgo y producción operativa | Pendiente | Candidato técnico, todavía sin capital real |
| G8 | Revisión independiente y autorización humana | Pendiente | Autorización de canary firmada |
| G9 | Canary real mínimo | Bloqueado | Mantener, reducir o retirar; nunca escalar automáticamente |

Cualquier gate fallido devuelve el programa a `NO_GO`. No existe “override” por CLI.

---

## 3. Reglas estratégicas congeladas

### 3.1 Hipótesis independientes

- **Even/Odd:** prueba de falsificación sobre paridad del último dígito. Baseline inicial 50/50; volatilidad del precio no implica información del dígito.
- **Multipliers:** detección causal de régimen direccional. No hereda señales, costos ni conclusiones de Even/Odd o EURGBP.
- Los resultados no se agregan para fabricar una “estrategia combinada”. Cada familia recibe release, presupuesto estadístico y conclusión separados.

### 3.2 Prohibiciones permanentes

- martingala, anti-martingala o progresiones de stake;
- duplicar para recuperar pérdidas;
- recargar para recuperar drawdown;
- selección retrospectiva de patrones;
- optimizar con el holdout;
- reintentar ciegamente `buy` o `sell` después de timeout;
- tratar estimaciones como `OBSERVED`;
- ejecutar si falta una propuesta contemporánea o una restricción de `contracts_for`;
- usar capital de vivienda, deuda, educación, emergencia o terceros;
- escalar automáticamente stake o capital.

### 3.3 Universo inicial

- Even/Odd: Volatility 10 estándar, validado en runtime.
- Multipliers: Drift Switching estándar si `active_symbols` y `contracts_for` demuestran soporte completo; fallback único: Volatility 10 estándar.
- Excluidos: variantes `1s`, Volatility 100, Boom/Crash, Jump, DEX, Step y Forex.

---

## 4. Protocolos científicos

### 4.1 Even/Odd

Preregistrar antes de recolectar evidencia:

1. `pip_size` del proveedor como única regla de representación del último dígito.
2. Hipótesis nula: paridad condicional no supera el break-even contemporáneo.
3. Dos contratos observados en cada decisión: `DIGITEVEN` y `DIGITODD`.
4. Break-even por lado: `ask_price / payout`.
5. Una sola familia inicial de features:
   - frecuencia causal de paridad;
   - transición par→par, par→impar, impar→par e impar→impar;
   - rachas, únicamente si se incluyen en el release antes de observar holdout.
6. Tamaño de muestra calculado por potencia estadística, no elegido por conveniencia:
   - alfa familiar corregido por número de hipótesis;
   - potencia mínima 80%;
   - efecto mínimo económicamente útil derivado del payout observado y margen de seguridad;
   - ajuste por tamaño efectivo de muestra/autocorrelación.
7. Evaluación walk-forward por bloques temporales.
8. Criterio económico: el límite inferior conservador de la probabilidad calibrada debe superar el break-even observado más margen preregistrado.
9. Rechazo automático si el edge aparece solo en un lado, sesión, precisión o régimen.

### 4.2 Multipliers

Preregistrar por separado:

1. Regla causal inicial única: retorno absoluto + consistencia direccional con ventana congelada.
2. Multiplicador elegido únicamente del rango común descubierto para `MULTUP` y `MULTDOWN`.
3. Contrato `no_expiry`; no enviar duración ni barrera.
4. Cierre paper explícito y acotado por:
   - stop-loss;
   - take-profit;
   - máximo de ticks/tiempo;
   - stop-out estimado o proveedor observado;
   - venta explícita cuando sea jurídicamente y técnicamente habilitada.
5. P/L estimado:
   `(% movimiento × multiplier × stake) − comisión − slippage`.
6. El settlement demo autoritativo será el `profit` final con `is_sold == 1`; `status="sold"` es terminal válido.
7. La decisión económica debe incluir comisión, slippage, latencia, stop-out y disponibilidad real del multiplicador.
8. No comparar docenas de ventanas/multiplicadores. Una sola configuración primaria y, como máximo, una sensibilidad preregistrada.
9. Criterio económico: límite inferior del intervalo de expectativa neta > 0 después de todos los costos y positivo bajo el escenario de estrés preregistrado.

### 4.3 Holdout y múltiples pruebas

- Un holdout por familia, sellado por hash y conteo.
- Se abre una sola vez después de congelar el `StrategyRelease`.
- Toda modificación posterior crea un release nuevo y un holdout nuevo; el anterior no vuelve a ser prueba confirmatoria.
- Corrección Holm o Bonferroni sobre el universo preregistrado.
- Bootstrap por bloques cuyo tamaño se derive de dependencia temporal observada en train, nunca del holdout.

---

# Plan de implementación

## Task 1: Aislar el baseline y registrar la decisión condicional

**Objective:** Evitar que cambios históricos de documentación se mezclen con el nuevo programa.

**Files:**
- Inspect: `git status --short`, `git diff --stat`, `git diff`
- Create: `docs/adr/ADR-012-conditional-real-money-program.md`
- Modify: `docs/scope/mvp-in-out.md`
- Modify: `docs/scope/gate-0-status.md`
- Test: `tests/docs/test_policy_documents.py`

**Steps:**

1. Clasificar los cambios actuales en documentación histórica, Even/Odd y Multipliers; no descartar trabajo existente.
2. Escribir primero una prueba documental roja que exija:
   - estado inicial `NO_GO`;
   - `REAL` ausente del laboratorio;
   - promoción real como decisión externa;
   - G1–G9 explícitos.
3. Ejecutar:
   `uv run pytest tests/docs/test_policy_documents.py -q --no-cov`
4. Crear ADR-012 aclarando que no revoca ADR-005/006/011; solo define una ruta condicional si cambian los hechos bloqueantes.
5. Actualizar scope sin afirmar que dinero real está permitido.
6. Repetir test y `git diff --check`.
7. Preparar un checkpoint de commit, pero no ejecutarlo sin autorización.

**Exit criterion:** Los documentos no se contradicen: hoy sigue excluido, pero existe una ruta condicional auditable.

## Task 2: Completar el preflight legal y contractual G1

**Objective:** Convertir términos y jurisdicción en inputs verificables, no notas narrativas.

**Files:**
- Create: `docs/legal/deriv-real-money-preflight.md`
- Create: `docs/data/provider-evaluation-deriv-execution.md`
- Modify: `docs/data/provider-data-policy.md`
- Create: `tests/docs/test_deriv_real_money_preflight.py`

**Preguntas que deben resolverse por escrito:**

- ¿Puede una cuenta colombiana usar cada producto y automatización vía API?
- ¿Se permite conservar ticks, propuestas, settlements, métricas agregadas, features, pesos y logs para investigación/comercialización?
- ¿Durante cuánto tiempo y bajo qué controles?
- ¿Puede almacenarse evidencia de P/L y contract IDs?
- ¿Qué límites, impuestos, KYC, retiros y reglas de cuenta aplican?
- ¿Qué operaciones de API son idempotentes o requieren reconciliación?

**Steps:**

1. Crear tests que exijan URL, versión, fecha, entidad contractual, jurisdicción, derechos de retención y decisión `APPROVED/BLOCKED`.
2. Registrar evidencia oficial o respuesta escrita; blogs y soporte informal no desbloquean G1.
3. Mantener G1 `BLOCKED` si una respuesta es ambigua.
4. No crear código real ni leer credenciales.

**Exit criterion:** Autorización escrita compatible con evidencia longitudinal y automatización; de lo contrario, el programa termina en integración efímera/demo.

## Task 3: Modelar releases y conclusiones sin habilitar `REAL`

**Objective:** Congelar exactamente qué estrategia fue evaluada y evitar promoción implícita.

**Files:**
- Create: `src/devsoul_quant/domain/strategy_release.py`
- Create: `tests/domain/test_strategy_release.py`
- Modify: `src/devsoul_quant/domain/metrics.py`
- Modify: `tests/domain/test_metrics.py`

**Tipos mínimos:**

```python
class ResearchConclusion(StrEnum):
    NO_EDGE = "NO_EDGE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PAPER_ELIGIBLE = "PAPER_ELIGIBLE"

@dataclass(frozen=True, slots=True)
class StrategyRelease:
    family: Literal["EVEN_ODD", "MULTIPLIER"]
    specification_hash: str
    dataset_hash: str
    code_version: str
    risk_policy_hash: str
    created_at_utc: datetime
```

**Steps:**

1. Test rojo: hashes vacíos, familia desconocida y timestamps naive son rechazados.
2. Implementar value object inmutable y serialización canónica determinista.
3. Test rojo: ningún modo actual puede producir `REAL_MONEY_ELIGIBLE`.
4. Mantener `PromotionEligibility.NOT_ELIGIBLE` para modos proxy actuales.
5. Añadir `PAPER_ELIGIBLE` únicamente para una evidencia económica nueva que todavía dependerá de G1–G4.

**Exit criterion:** El laboratorio puede identificar releases y emitir solo tres conclusiones científicas.

## Task 4: Preregistrar Even/Odd G2

**Objective:** Congelar la hipótesis y su análisis antes de datos elegibles.

**Files:**
- Create: `docs/research/deriv-even-odd-protocol.md`
- Create: `tests/docs/test_deriv_even_odd_protocol.py`
- Modify: `src/devsoul_quant/domain/digit_strategy.py`
- Modify: `tests/domain/test_digit_strategy.py`

**Steps:**

1. Escribir test documental para baseline, payout, potencia, multiplicidad, holdout y criterios terminales.
2. Documentar universo exacto de features y una única política primaria.
3. Añadir un cálculo determinista de tamaño de muestra/potencia si G1 permite dataset.
4. Probar con fixtures sintéticas que una secuencia 50/50 termina `NO_EDGE` o `INSUFFICIENT_EVIDENCE`.
5. Probar que una aparente ventaja que no limpia break-even produce `NO_TRADE`.

**Exit criterion:** Release Even/Odd congelado sin mirar holdout ni ajustar por resultados.

## Task 5: Preregistrar Multipliers G2

**Objective:** Congelar régimen, cierre y economía no binaria.

**Files:**
- Create: `docs/research/deriv-multiplier-protocol.md`
- Create: `tests/docs/test_deriv_multiplier_protocol.py`
- Modify: `src/devsoul_quant/domain/multiplier.py`
- Modify: `tests/domain/test_multiplier.py`
- Modify: `src/devsoul_quant/application/multiplier_lab.py`
- Modify: `tests/application/test_multiplier_lab.py`

**Steps:**

1. Documentar configuración primaria única y sensibilidad máxima permitida.
2. Test rojo para separar `ESTIMATED` de settlement proveedor `OBSERVED`.
3. Modelar razón de cierre (`STOP_LOSS`, `TAKE_PROFIT`, `TIME_LIMIT`, `STOP_OUT`, `EXPLICIT_SELL`).
4. Testear `status="sold"` como terminal válido.
5. Rechazar multiplier fuera del rango runtime y catálogo contradictorio.
6. Mantener `NO_TRADE` ante comisión, slippage o stop-out desconocidos.

**Exit criterion:** Release Multipliers congelado y económicamente completo en papel.

## Task 6: Construir el dataset legal G3 — solo después de G1

**Objective:** Obtener evidencia reproducible sin violar retención.

**Files:**
- Modify: `src/devsoul_quant/domain/datasets.py`
- Modify: `src/devsoul_quant/domain/data_rights.py`
- Create: `src/devsoul_quant/application/prepare_deriv_validation.py`
- Create: `tests/application/test_prepare_deriv_validation.py`
- Create: `docs/data/deriv-dataset-manifest.md`

**Steps:**

1. Gate rojo que bloquee ingestión si faltan derechos de almacenamiento, derivados, entrenamiento o uso comercial.
2. Incorporar hash, cobertura temporal, gaps, zona horaria, precisión, schema y provenance.
3. Separar cronológicamente train, validation y holdout.
4. Detectar duplicados, reorder, gaps y precision drift.
5. Prohibir que el adapter de ejecución lea el holdout.
6. Si G1 no se desbloquea, cancelar Task 6 y mantener `INSUFFICIENT_EVIDENCE`.

**Exit criterion:** Dataset legal, hashable, reproducible y no contaminado.

## Task 7: Evaluación económica G4

**Objective:** Evaluar expectativa neta y riesgo sin confundir hit rate con rentabilidad.

**Files:**
- Create: `src/devsoul_quant/domain/economic_evaluation.py`
- Create: `tests/domain/test_economic_evaluation.py`
- Create: `src/devsoul_quant/application/evaluate_strategy_release.py`
- Create: `tests/application/test_evaluate_strategy_release.py`

**Métricas mínimas:**

- expectativa neta por operación y su intervalo por bloques;
- intervalo de hit rate frente a break-even para Even/Odd;
- profit factor y distribución de P/L para Multipliers;
- drawdown máximo y distribución bootstrap de drawdown;
- longest loss streak;
- turnover y exposición;
- costos, slippage y latencia por cuantiles;
- probabilidad de ruina bajo el risk budget propuesto;
- estabilidad por folds y regímenes.

**Criterio `PAPER_ELIGIBLE`:**

Todas deben cumplirse:

1. economía `OBSERVED`, no proxy;
2. límite inferior del intervalo de expectativa neta > 0;
3. criterio específico de familia superado;
4. todos los folds principales no negativos después de costos;
5. escenario de estrés preregistrado no destruye la expectativa;
6. riesgo de ruina bajo el límite congelado;
7. holdout abierto una sola vez y positivo;
8. ningún incidente de calidad o leakage.

**Exit criterion:** Una de las tres conclusiones permitidas, con explicación verificable.

## Task 8: Forward shadow y paper G5

**Objective:** Probar causalidad y economía contemporánea sin comprar.

**Files:**
- Create: `src/devsoul_quant/application/deriv_shadow_session.py`
- Create: `tests/application/test_deriv_shadow_session.py`
- Modify: `src/devsoul_quant/adapters/deriv/research_session.py`
- Modify: `tests/adapters/deriv/test_research_session.py`

**Steps:**

1. Integrar ticks → catálogo → propuestas → decisión → settlement paper en una sesión.
2. Exigir proposal posterior a la última feature y anterior a la decisión.
3. Añadir límites de sesión: ticks, decisiones, propuestas, latencia, duración y zeroización.
4. Simular disconnect, stale quote, catálogo cambiante y reloj que cruza TTL.
5. Rechazar cualquier resultado que no pueda conservarse legalmente.
6. Ejecutar forward durante el mínimo temporal preregistrado; no sustituir días por más ticks correlacionados.

**Exit criterion:** Release estable forward, sin leakage y sin compras.

## Task 9: Ejecución demo reconciliada G6

**Objective:** Validar lifecycle real del proveedor con fondos virtuales, no descubrir edge.

**Files:**
- Refactor: `src/devsoul_quant/application/demo_execution.py`
- Modify: `src/devsoul_quant/adapters/deriv/demo_execution.py`
- Create: `src/devsoul_quant/application/multiplier_demo_execution.py`
- Create: `tests/application/test_multiplier_demo_execution.py`
- Modify: `tests/adapters/deriv/test_demo_execution_gateway.py`
- Create: `docs/runbooks/deriv-demo-operations.md`

**Steps:**

1. Separar propuestas fixed-payout de propuestas Multiplier; no aplicar payout ratio binario a Multipliers.
2. Añadir `sell` explícito solo para contratos con `is_valid_to_sell == 1`.
3. Mantener buy/sell sin retries ciegos; reconciliar una vez.
4. Añadir deadline absoluto y cierre de emergencia antes de TTL.
5. Testear disconnect antes/después de buy, settlement duplicado, contract ID distinto y estado `sold`.
6. Ejecutar primero una operación demo manualmente armada; luego sesiones demo limitadas.

**Exit criterion:** Cero posiciones huérfanas, conciliación exacta y runbook probado.

## Task 10: Extender el risk engine G7

**Objective:** Limitar riesgo agregado y detener el sistema antes de daño significativo.

**Files:**
- Modify: `src/devsoul_quant/domain/risk.py`
- Modify: `tests/domain/test_risk.py`
- Create: `src/devsoul_quant/domain/portfolio_risk.py`
- Create: `tests/domain/test_portfolio_risk.py`
- Create: `src/devsoul_quant/application/risk_supervisor.py`
- Create: `tests/application/test_risk_supervisor.py`

**Política canary propuesta — debe congelarse y aprobarse:**

- capital asignado totalmente prescindible y segregado;
- stake por contrato ≤ 0.10% del capital asignado;
- si el mínimo del proveedor excede 0.10%, resultado `NO_GO`;
- máximo una posición abierta;
- pérdida diaria máxima 0.50%;
- pérdida semanal máxima 1.00%;
- drawdown máximo del canary 2.00%;
- sin recarga ni reset de drawdown;
- kill switch por latencia, catálogo, reconciliación, propuesta stale o estado ambiguo;
- stake fijo durante todo el canary; no Kelly y no compounding.

**Steps:**

1. Tests rojos para cada límite y combinación de exposición.
2. Evaluar riesgo antes de propuesta, antes de buy y después de cada evento.
3. Hacer el kill switch monotónico: una vez activado requiere intervención humana.
4. Rechazar startup si no puede reconstruirse de forma legal y autoritativa el estado de posiciones.
5. Probar crash/restart con una posición abierta usando fixtures, nunca endpoint real.

**Exit criterion:** Toda ruta insegura termina en rechazo o cierre controlado.

## Task 11: Seguridad, observabilidad y runbooks G7

**Objective:** Operar como servicio crítico sin exponer secretos ni datos restringidos.

**Files:**
- Create: `docs/security/deriv-real-money-threat-model.md`
- Create: `docs/runbooks/kill-switch.md`
- Create: `docs/runbooks/reconciliation.md`
- Create: `docs/runbooks/incident-response.md`
- Create: `tests/security/test_real_money_boundaries.py`

**Controles:**

- token con privilegios mínimos; sin permiso de retiro si el proveedor lo permite;
- secretos solo en keyring/secret manager, nunca CLI, stdout, repo o logs;
- release hash y risk-policy hash obligatorios al arrancar;
- reloj sincronizado y health checks;
- métricas operativas sin payloads restringidos;
- alertas por posición ambigua, kill switch, latencia y reconciliación;
- backup solo de artefactos cuya licencia lo permita;
- procedimiento manual de cierre desde UI del proveedor.

**GCP cost impact:** por defecto local-only y costo adicional USD 0. Si posteriormente se propone Cloud Run/Secret Manager/Monitoring, crear una estimación separada antes de desplegar; no introducir nube por defecto.

**Exit criterion:** threat model revisado y simulacro de incidentes aprobado.

## Task 12: Autorización externa G8

**Objective:** Evitar que el mismo software que genera evidencia se autorice a sí mismo.

**Files:**
- Create: `docs/releases/real-money-authorization-template.md`
- Create: `src/devsoul_quant/domain/deployment_authorization.py`
- Create: `tests/domain/test_deployment_authorization.py`

**Campos obligatorios:**

- StrategyRelease hash;
- código/tag exacto;
- dataset y protocolo;
- conclusión `PAPER_ELIGIBLE`;
- revisión legal vigente;
- capital máximo;
- límites diarios/semanales/drawdown;
- fecha de expiración de autorización;
- aprobador humano;
- checklist y firma/hash.

**Regla:** El laboratorio no produce esta autorización. Sin archivo firmado y vigente, un adaptador real ni siquiera puede construirse.

**Exit criterion:** revisión independiente de ciencia, seguridad y riesgo, más autorización explícita del usuario.

## Task 13: Adaptador real aislado — únicamente después de G8

**Objective:** Implementar el mínimo adaptador necesario sin reutilizar accidentalmente credenciales demo ni ampliar scope.

**Files:**
- Create: `src/devsoul_quant/adapters/deriv/real_execution.py`
- Create: `tests/adapters/deriv/test_real_execution.py`
- Create: `src/devsoul_quant/application/real_canary.py`
- Create: `tests/application/test_real_canary.py`
- Modify: `src/devsoul_quant/domain/execution_mode.py` solo después de aprobación ADR + G8.

**Steps:**

1. Test rojo: el adaptador no importa ni acepta URLs demo y viceversa.
2. Exigir account attestation real, autorización vigente y release hash exacto.
3. Implementar propuesta, buy/sell y reconciliación mínima sin loops autónomos.
4. No copiar `demo-execute`; extraer únicamente puertos neutrales ya probados.
5. Añadir dry-run que llega hasta proposal y se detiene.
6. Hacer una revisión de seguridad externa/read-only antes de cualquier llamada de compra.

**Exit criterion:** Adaptador probado offline y dry-run real sin compra. La primera compra todavía requiere una acción humana separada.

## Task 14: Canary G9 y política de escala

**Objective:** Validar operación, no “probar” una estrategia con pérdidas reales.

**Secuencia:**

1. Dry-run real read-only.
2. Una operación manualmente armada al stake mínimo que respete ≤0.10%.
3. Pausa y reconciliación completa.
4. Canary con una posición máxima y stake fijo.
5. Evaluación tras un mínimo de 30 días calendario y tamaño de muestra preregistrado; se aplica el criterio más largo.
6. Cualquier incidente severo, breach de límite o divergencia con demo detiene el canary.
7. No escalar antes de 60 días adicionales y 100 settlements sin incidentes, y solo con nueva autorización humana.
8. Escala máxima por etapa: nunca más de 2× el stake anterior y siempre respetando el porcentaje del capital; no es recuperación de pérdidas.

**Resultados posibles:**

- `RETIRE`: edge desapareció, costos cambiaron o hubo incidente crítico.
- `HOLD`: evidencia insuficiente; mantener stake o detener.
- `CONTINUE_CANARY`: desempeño y operación dentro de release.

No existe `AUTO_SCALE`.

---

## 5. Gates de rechazo inmediato

El programa se detiene si ocurre cualquiera:

- G1 no prueba derechos de retención/derivados/automatización;
- no hay dataset legal reproducible;
- holdout contaminado o abierto antes del release;
- límite inferior de expectativa ≤ 0;
- el edge depende de una única sesión/régimen;
- costos o slippage `UNAVAILABLE`;
- multiplicador o contrato no aparece en runtime;
- riesgo de ruina excede el presupuesto congelado;
- mínimo de stake viola el límite porcentual;
- posición ambigua o reconciliación incompleta;
- credenciales expuestas;
- drift de schema/términos sin revisión;
- drawdown o loss limit alcanzado;
- intento de martingala, recarga o cambio de release durante canary.

---

## 6. Verificación global por bloque

Después de cada bloque de código:

```bash
uv run pytest <test-focal> -q --no-cov
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy
uv run pytest -q
scripts/verify.sh
git diff --check
```

Antes de cada checkpoint:

```bash
git status --short
git diff --stat
git diff
```

Revisar explícitamente:

- ausencia de secretos;
- ausencia de datos Deriv retenidos sin permiso;
- ausencia de endpoint real antes de G8;
- cobertura ≥95%;
- ninguna afirmación de rentabilidad basada en fixtures;
- documentos y tests sin contradicciones.

No hacer commit, push, deploy, migración remota ni `terraform apply` sin autorización explícita del usuario.

---

## 7. Próximo bloque recomendado

Ejecutar únicamente Tasks 1–5 en esta etapa:

1. ADR-012 y matriz de gates.
2. Preflight legal G1.
3. Modelo `StrategyRelease` y conclusiones permitidas.
4. Preregistro Even/Odd.
5. Preregistro Multipliers.

Después se revisa G1. Si sigue bloqueado, no se construye el dataset ni una ruta real: se mantiene el laboratorio efímero y se concluye `INSUFFICIENT_EVIDENCE`. Si G1 se aprueba con evidencia escrita, se continúa a G3.
