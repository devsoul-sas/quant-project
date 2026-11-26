# S3 — Protocolo de descubrimiento de estructura estadística en series temporales de mercado

- **Fecha de diseño:** 2026-11-24
- **Estado inicial:** `DRAFT_TEMPLATE`
- **Ámbito:** documentación científica; no implementa modelos ni autoriza ejecución
- **Decisión recomendada:** ejecutar primero un estudio de estructura y predictibilidad **no económico**, con hipótesis pocas y preregistradas, inferencia compatible con dependencia temporal y réplica independiente. Sólo después, y en otro protocolo, evaluar economía contractual observable.

> **Regla epistemológica central:** dependencia estadística, predictibilidad probabilística y edge económico son tres afirmaciones distintas. Rechazar un null de independencia no demuestra capacidad de pronóstico; mejorar un score predictivo no demuestra valor económico; y ninguna de las dos cosas demuestra rentabilidad después de precio, payout, spread, slippage, latencia, rollover, límites o selección de operaciones.

Los términos **DEBE**, **NO DEBE** y **BLOQUEA** son normativos. Todo `TBD` en un campo marcado como bloqueante impide cambiar el estado a `FROZEN`.

---

## 1. Independencia de investigaciones anteriores

Este protocolo abre una familia científica nueva y **no** continúa ni rescata las hipótesis Even/Odd o Multipliers:

1. Even/Odd y Multipliers se consideran hipótesis cerradas/rechazadas dentro de su alcance anterior.
2. No se permite seleccionar retrospectivamente una variante, horizonte, target, stop, feature o régimen de esas familias y presentarlo como confirmación S3.
3. Las semillas sintéticas **61–80 permanecen selladas**. S3 no puede generarlas, inspeccionarlas, reasignarlas ni usarlas como datos de desarrollo, calibración, potencia, prueba o demostración.
4. S3 tendrá identificadores de datasets, periodos, fuentes, releases, semillas estadísticas y hashes propios. Las semillas de bootstrap/permutación no convierten datos ya observados en evidencia independiente.
5. Una similitud accidental con una regla anterior debe declararse y contabilizarse como hipótesis previamente explorada, no como réplica independiente.

Un test de integridad documental previo al freeze debe confirmar:

```yaml
prior_families_excluded: [EVEN_ODD, MULTIPLIERS]
reserved_seed_cohort_61_80_status: SEALED_NOT_GENERATED_NOT_REUSED
independence_rationale: TBD  # bloqueante
```

---

## 2. Preguntas científicas y niveles de afirmación

### 2.1 Preguntas permitidas

S3 puede responder, por unidad de análisis y horizonte:

1. ¿Existe dependencia lineal temporal fuera de la explicada por el null preregistrado?
2. ¿Queda dependencia no lineal después de remover estructura lineal y heterocedasticidad condicional especificadas **antes** del holdout?
3. ¿La información mutua o la entropía difieren de surrogates que conservan las propiedades relevantes del null?
4. ¿Hay cambios de distribución o parámetros reproducibles, y fueron detectables de forma causal?
5. ¿Una probabilidad emitida fuera de muestra mejora un benchmark y está calibrada?
6. ¿La evidencia sobrevive corrección por búsquedas múltiples, dependencia temporal, sensibilidad y réplica independiente?

### 2.2 Escalera de afirmaciones

| Nivel | Afirmación máxima | Evidencia mínima | Lo que no permite afirmar |
|---|---|---|---|
| S0 | Descripción | gráficos y estadísticos con incertidumbre | dependencia, predicción o edge |
| S1 | Estructura estadística | test preregistrado, null adecuado y FWER controlado | pronóstico útil |
| S2 | Predictibilidad probabilística | evaluación causal OOS, score propio, calibración y réplica | rentabilidad |
| S3 | Candidato a evaluación económica | S2 + estabilidad temporal + datos/licencia aptos | edge económico |
| E1 | Edge económico bajo un contrato concreto | protocolo económico separado con quotes/fills/costos observables | rentabilidad futura garantizada |

La salida máxima de este documento es `ECONOMIC_EVALUATION_ELIGIBLE`; nunca `PROFITABLE`, `PAPER_ELIGIBLE`, `DEMO_ELIGIBLE` ni autorización de capital.

---

## 3. Objeto de estudio y unidades de análisis

No se mezclan frecuencias, instrumentos o relojes sin modelar explícitamente su jerarquía.

### 3.1 Unidades

- **Unidad de observación:** un evento o barra causalmente disponible en tiempo `t`, con timestamp de evento, timestamp de recepción cuando exista, fuente, instrumento y política de gaps.
- **Variable primaria de serie:** retorno/log-retorno, cambio, duración, volatilidad realizada u otra transformación preregistrada. El nivel de precio no se trata como estacionario por defecto.
- **Unidad de predicción:** un origen `t` y un target definido sobre `(t, t+h]`.
- **Unidad de puntuación:** una pérdida propia por origen de predicción, por ejemplo Brier o log score. Si targets se solapan, esas pérdidas no son IID.
- **Unidad experimental/inferencial:** el bloque temporal suficientemente largo para representar la dependencia; si hay varios instrumentos, la unidad puede ser bloque-tiempo × instrumento, con clustering explícito.
- **Unidad de réplica:** periodo futuro no tocado o segunda fuente/mercado con construcción equivalente. Otra ventana solapada o una nueva seed de remuestreo no es réplica.

### 3.2 Reglas de muestreo

1. Fijar reloj (event time o clock time), zona `UTC`, calendario, cierres, duplicados, revisiones y gaps antes del análisis.
2. No rellenar precios o targets atravesando cierres/gaps salvo regla preregistrada; cualquier imputación debe ser causal y ajustada dentro de train.
3. Congelar universo mediante una regla ex ante, incluida supervivencia/listado. No seleccionar instrumentos porque “se ven predictivos”.
4. Registrar cambios de microestructura, proveedor, precisión, timezone y metodología de fixing como posibles intervenciones.
5. La disponibilidad legal para conservar y derivar datos es un gate anterior a S3; datos efímeros no pueden sostener una afirmación longitudinal reproducible.

---

## 4. Pre-registro y registro del espacio de búsqueda

Antes de consultar validation final y, obligatoriamente, antes de abrir confirmation:

- congelar hipótesis primaria y signo/dirección si corresponde;
- definir todos los instrumentos, transformaciones, lags, horizontes, filtros, regímenes, estimadores, hiperparámetros y métricas;
- definir la **familia de multiplicidad**: cada combinación realmente inspeccionada cuenta, aunque no llegue al informe;
- publicar hashes de protocolo, código/release, manifest de datos y fronteras temporales;
- declarar resultados previos relacionados y decisiones humanas ya influidas por los datos;
- fijar nulls, surrogates, método de remuestreo, block length, alpha/q, potencia, MDE y regla de parada;
- definir qué es primario, confirmatorio, secundario y puramente exploratorio;
- congelar política de desviaciones e invalidación.

Se mantiene un **ledger de búsqueda** append-only:

```text
analysis_id | timestamp | hypothesis_family | instrument | transform | lag/horizon
| regime_rule | estimator | parameters | dataset_partition | analyst/release | result_status
```

No reportar una prueba ejecutada equivale a ocultar multiplicidad. Una modificación posterior al freeze crea `protocol_version + 1` y una nueva confirmación futura; no reabre el mismo holdout.

---

## 5. Partición temporal y control de leakage

### 5.1 Particiones mínimas

Las fronteras se fijan por fechas/calendario, no mediante shuffle aleatorio:

1. **Discovery/train:** especificación, estimación, diagnóstico y elección limitada.
2. **Validation:** comparación y descarte; puede informar una única especificación congelada.
3. **Confirmation holdout:** se abre una sola vez para la prueba confirmatoria preregistrada.
4. **Réplica:** periodo posterior o fuente independiente; no se usa para reoptimizar la hipótesis confirmada.

Una asignación inicial orientativa es 50–60% / 20–25% / 20–25%, pero las fechas deben satisfacer potencia, diversidad de regímenes y duración mínima. Si no lo hacen, se recolectan más datos; no se reduce el estándar.

### 5.2 Walk-forward interno

Dentro de discovery/validation se usa expanding o rolling walk-forward, congelado antes de puntuar:

```text
[train_i] [purge] [warm-up_i][score_i] [embargo]
```

- Toda normalización, discretización, selección de bins, reducción de dimensión, estimador de MI/entropía, régimen, calibrador y modelo se ajusta sólo con `train_i`.
- `warm-up_i` está dentro del bloque futuro y no se puntúa; no se inicializa con un tail previo a la purga.
- La **purga** elimina observaciones de entrenamiento cuya ventana de feature/label toca el bloque de score.
- El **embargo** impide que observaciones demasiado próximas vuelvan al siguiente train cuando existe solapamiento o memoria.
- Mínimo técnico sugerido, a justificar: `purge >= max_feature_lookback + label_horizon - 1` observaciones y `embargo >= max(label_horizon - 1, dependence_horizon)`. Si el reloj es irregular, se expresa también en tiempo real.
- Cualquier feature revisada, centrada, filtrada bilateralmente o calculada con el dataset completo está prohibida.

### 5.3 Audit de leakage

Antes de abrir confirmation deben pasar pruebas de:

- invariancia de features/decisiones pasadas al anexar datos futuros;
- ajuste fold-local de todos los transformadores;
- ausencia de timestamps futuros en features y labels;
- lineage de revisiones e imputaciones;
- conteo esperado de predicciones tras warm-up/purge/embargo;
- separación física/lógica del holdout y denegación de acceso por defecto.

Acceso accidental, resumen, gráfico o metadato revelador del holdout invalida la confirmación.

---

## 6. Nulls y surrogates: jerarquía obligatoria

No existe un único “random shuffle” válido para series temporales. Cada prueba debe declarar qué propiedades conserva el null.

| Pregunta | Null confirmatorio | Surrogate/remuestreo recomendado | Propiedades preservadas / destruidas |
|---|---|---|---|
| Dependencia lineal de retornos | no autocorrelación hasta `L` bajo el modelo de media preregistrado | wild/block bootstrap de residuales o simulación del modelo nulo | conserva heterocedasticidad/bloques según diseño; rompe correlación de media |
| Dependencia no lineal residual | proceso lineal estocástico con misma distribución marginal y espectro | AAFT/IAAFT; preferir IAAFT con tolerancia y convergencia registradas | aproxima marginal y autocorrelación lineal; rompe fase/no linealidad |
| MI entre `X_t` y `X_{t-l}` | independencia al lag `l` condicionada a estructura preservada | circular shift con offsets mayores que zona de exclusión, block permutation o surrogates model-based | preserva estructura interna de cada serie; rompe alineación entre series |
| Transferencia dirigida | no información incremental de X sobre Y dada la historia preregistrada | shift/block permutation de X respecto de Y; simulación del null condicional | evita confundir autocorrelación propia con transferencia |
| Entropía/complejidad | estadístico compatible con el proceso nulo especificado | IAAFT/model-based, mismos `n`, marginal, espectro y missingness | la entropía aislada no tiene null universal |
| Cambio de régimen | parámetros/distribución estables bajo un modelo entrenado en train | bootstrap paramétrico/block bootstrap bajo estabilidad | calibra máximos/búsqueda de breakpoints |
| Mejora predictiva | diferencia esperada de pérdida OOS `E[d_t] >= 0` frente al benchmark | bootstrap de bloques **pareado** sobre `d_t`; SPA/Reality Check si se buscaron modelos | conserva contemporaneidad y dependencia de diferencias de score |
| Calibración | `P(Y=1 | p)=p` y/o intercepto 0, slope 1 | intervalos por bloques/cluster; simulación calibrada | respeta dependencia y tamaños de bins |

### 6.1 Requisitos de surrogates

- Número confirmatorio recomendado: al menos `B=9,999` para resolución cercana a `10^-4`; se fija antes del run.
- Usar p-value de Monte Carlo `(1 + # extremos)/(B + 1)`, nunca cero.
- Para prueba bilateral, definir estadístico y regla bilateral antes del run.
- Validar que cada surrogate reproduce las propiedades que afirma preservar (marginal, ACF/espectro, volatilidad, gaps y longitud). Si falla, el test es `INVALID`.
- No usar permutación de puntos IID ni bootstrap IID cuando existe dependencia apreciable.
- Un circular shift sólo es válido con estacionariedad/periodicidad defendible y una zona de exclusión que evite alineaciones casi originales; de lo contrario usar bloques o null model-based.
- Si se selecciona un modelo/lag dentro del pipeline, esa selección debe repetirse **dentro de cada remuestra** cuando la inferencia pretenda cubrir el pipeline completo.

---

## 7. Batería de análisis, en orden

El orden evita interpretar complejidad como evidencia cuando basta una explicación simple.

### Fase A — Calidad y descripción, sin inferencia de edge

- lineage, duplicados, gaps, timestamps, precisión/redondeo, revisiones, outliers y cambios de proveedor;
- distribución por periodo y sesión; ACF de nivel, retorno, `|r|` y `r²`;
- missingness y actividad como series propias;
- gráficos sólo sobre discovery.

**Salida:** `DATA_VALID` o `DATA_INVALID`. Ningún p-value rescata datos inválidos.

### Fase B — Estacionariedad y transformaciones

1. Aplicar ADF/PP (null: raíz unitaria) y KPSS (null: estacionariedad) como evidencia complementaria, no como sello binario.
2. Incluir constante/tendencia y lags elegidos sólo con train y regla congelada.
3. Evaluar breaks conocidos o detectados en discovery; tests de raíz unitaria sin breaks pueden engañar.
4. Examinar estabilidad local por rolling windows y por periodos económicos; distinguir estacionariedad débil, local y de distribución.
5. Si ADF y KPSS son inconclusos o contradictorios, clasificar `AMBIGUOUS` y usar métodos robustos/locales; no escoger el test favorable.
6. No diferenciar repetidamente hasta obtener significancia. Toda transformación cambia la pregunta y debe registrarse.

### Fase C — Dependencia lineal

- ACF/PACF y Ljung–Box en lags primarios congelados;
- correlación Pearson y, como robustez, Spearman/Kendall cuando proceda;
- ACF de `|r|`/`r²` para clustering de volatilidad;
- modelo simple de media/varianza sólo como null nuisance, ajustado en train;
- intervalos y tests robustos a heterocedasticidad/dependencia o bootstrap por bloques.

No interpretar muchos lags individuales sin corrección. El test portmanteau responde a una familia de lags; inspeccionar varias elecciones de `L` crea otra familia.

### Fase D — Dependencia no lineal e información

Aplicar a residuos estandarizados de un null lineal/volatilidad congelado:

- BDS como diagnóstico global, con dimensiones y radios preregistrados;
- información mutua por lag con estimador, parámetros y sesgo fijados; la discretización se aprende en train;
- información condicional/transfer entropy sólo si existe una hipótesis direccional concreta y suficientes datos;
- entropía muestral (SampEn) o medida equivalente con `m`, tolerancia `r`, escala y normalización congeladas;
- comparar contra IAAFT/model-based surrogates, no contra una tabla IID genérica.

**Cautelas:** MI/TE son no negativas y sesgadas en muestra finita; la entropía depende de escala, ruido, longitud y estimador; BDS rechaza por cualquier mala especificación y no identifica mecanismo. Ninguna es una métrica de rentabilidad.

### Fase E — Cambios de régimen

1. En discovery, usar tests de breaks múltiples/modelos de cambio con número máximo, trimming, mínima permanencia y variables fijadas.
2. Distinguir:
   - **segmentación retrospectiva**, que usa el futuro y es sólo descriptiva;
   - **detector online/filtrado**, que puede alimentar una predicción causal.
3. Un HMM/Markov-switching se ajusta por fold; sus labels se alinean sin usar confirmation. Estados no son realidades económicas por sí mismos.
4. Evaluar estabilidad de parámetros y score, no sólo cambio de media.
5. Efectos “en régimen” requieren una interacción preregistrada y corrección conjunta; no hacer subgroup mining.
6. Exigir observaciones y duración mínima por régimen. Si un estado aparece sólo en train o confirmation, reportar `REGIME_SUPPORT_FAILURE`.

### Fase F — Predicción y calibración probabilística

- Definir evento, horizonte y benchmark antes de modelar.
- Benchmarks mínimos: climatología entrenada, persistencia cuando tenga sentido y modelo lineal simple.
- Métricas primarias propias: Brier para binario y/o log score con clipping preregistrado sólo por estabilidad numérica. Accuracy/AUC son secundarias y no prueban calibración.
- Reportar descomposición/reliability, calibration-in-the-large (intercepto), slope, curvas con bins definidos en train e incertidumbre por bloques.
- ECE es descriptivo: depende de bins y puede ser sesgado; no debe ser único gate.
- Cualquier Platt/isotonic/otro calibrador se ajusta en train, se elige en validation y queda congelado antes de confirmation.
- Comparar pérdidas por origen de forma pareada. Reportar media de `d_t = loss_candidate - loss_benchmark`, intervalo por bloques y estabilidad por fold/periodo.
- Un clasificador selectivo debe puntuar también cobertura/abstención y compararse en las mismas oportunidades. El hit rate sólo entre entradas puede ocultar selección.

---

## 8. Dependencia temporal, tamaño efectivo e incertidumbre

### 8.1 Tamaño efectivo

Para una media de una serie aproximadamente estacionaria `z_t` (idealmente la diferencia de score primaria):

```text
n_eff = n / (1 + 2 * sum_{k=1..K} rho_z(k))
```

`K` y la regla de truncamiento se fijan usando sólo train (por ejemplo, initial-positive/monotone sequence o un horizonte de dependencia preregistrado). Requisitos:

- reportar `n` bruto, `n_eff`, ACF de `z_t`, `K` y sensibilidad;
- no truncar autocorrelaciones negativas oportunistamente para inflar `n_eff`;
- targets de horizonte `h` solapados imponen dependencia mecánica; como chequeo conservador reportar también `floor(n / h)` cuando las oportunidades son regulares;
- con clusters (día, sesión, instrumento), reportar número de clusters y el mínimo soporte por cluster;
- usar como soporte operativo conservador el menor entre estimaciones defendibles; `n_eff` no corrige sesgo, leakage ni drift.

### 8.2 Bootstrap por bloques

Método primario recomendado: **stationary bootstrap** o moving/circular block bootstrap, pareado cuando se comparan modelos.

- Elegir longitud media de bloque `ell` sólo con train mediante regla automática preregistrada o rango fijo basado en horizonte/dependencia.
- Sensibilidad obligatoria: por ejemplo `ell/2`, `ell`, `2ell`, respetando `ell >= label_horizon` cuando hay solapamiento.
- Remuestrear vectores conjuntos (target, predicciones, benchmark, régimen), no columnas por separado.
- Con paneles, preservar dependencia cross-sectional remuestreando bloques de tiempo comunes y, si procede, cluster por instrumento.
- Usar al menos 5,000 remuestras para intervalos de desarrollo y 9,999 para el gate final, salvo justificación de precisión Monte Carlo.
- Si resultados cambian materialmente con block length razonable, concluir `INFERENCE_UNSTABLE`.

### 8.3 Permutación por bloques

Se usa para tests de independencia/alineación cuando el null admite intercambiabilidad de bloques. La longitud, bordes, circularidad y zona de exclusión se preregistran. La permutación no es válida si mezcla regímenes que el null exige conservar; en ese caso se estratifica con reglas ex ante o se usa simulación model-based.

---

## 9. Comparaciones múltiples y data snooping

### 9.1 Definición de familia

La familia confirmatoria incluye todas las variantes inspeccionadas de:

```text
instrumentos × frecuencias × transformaciones × features × lags × horizontes
× estimadores × hiperparámetros × reglas de régimen × targets × benchmarks
```

También cuentan pruebas manuales, notebooks descartados y resultados anteriores que motivaron la selección.

### 9.2 Política

- **Confirmación primaria:** controlar FWER a `alpha=0.05` mediante Holm para pocas hipótesis o maxT/stepdown basado en bloques para tests dependientes. Bonferroni es válido pero potencialmente conservador.
- **Descubrimiento secundario:** BH con `q=0.05` puede priorizar leads si las condiciones de dependencia son defendibles; bajo dependencia arbitraria usar Benjamini–Yekutieli o un método resampling adecuado. Todo hallazgo FDR es `LEAD_ONLY` y requiere confirmación nueva.
- **Búsqueda de muchos modelos:** White Reality Check o Hansen SPA sobre pérdidas OOS y bootstrap temporal, además del ledger completo. No elegir el mejor modelo y aplicarle después un test individual ingenuo.
- Reportar p-values crudos y ajustados, tamaño de familia, método, alpha/q y número total de análisis.
- No redefinir familias pequeñas por narrativa (“por indicador”, “por activo”) después de ver resultados.

**Convención S3:** el gate primario requiere FWER; FDR nunca basta para promoción.

---

## 10. Potencia, precisión y mínimo efecto relevante

No existe un número universal de ticks/trades. Antes del freeze:

1. Definir un **mínimo efecto estadístico y práctico** (`MES/MDE`) en unidades de la métrica: por ejemplo, reducción mínima de Brier/log loss frente al benchmark. No usar rentabilidad si aún no hay economía observable.
2. Estimar potencia mediante simulación que preserve longitud, missingness, marginal, autocorrelación, volatilidad, solapamiento, splits, selección y corrección múltiple.
3. Simular bajo null para comprobar tasa de falso positivo del pipeline completo; objetivo `FWER_empírica <= 0.05` dentro de error Monte Carlo.
4. Inyectar efectos de magnitud MDE y medir rechazo/promoción; objetivo mínimo `power >= 0.80`, preferible 0.90 para una decisión costosa.
5. Repetir sobre escenarios de drift/regímenes y longitudes de bloque plausibles.
6. Predefinir duración calendario mínima además de `n_eff`; muchos ticks de una sola sesión no sustituyen diversidad temporal.
7. Congelar regla de parada por información/fecha. No detener por un p-value favorable. Un diseño secuencial requiere alpha-spending/e-value explícito desde el inicio.

Si la potencia es insuficiente, la salida es `INSUFFICIENT_EVIDENCE`, no `NO_EDGE`. Si el MDE detectable es mayor que cualquier efecto útil, el estudio no es informativo y no debe abrir confirmation.

---

## 11. Gates y estados de decisión

### Gate G0 — Integridad y derechos

Todos obligatorios:

- derechos de retención/derivación/reporte compatibles;
- dataset y release con hashes; reloj/gaps/revisiones definidos;
- no uso de familias rechazadas ni semillas 61–80;
- holdout inaccesible y audit de leakage aprobado.

Fallo → `INVALID_STUDY` o `DATA_RIGHTS_BLOCKED`.

### Gate G1 — Estructura estadística

Todos obligatorios:

- hipótesis/null/surrogates preregistrados;
- estadístico primario supera FWER 0.05;
- efecto e intervalo compatibles con el MDE;
- n_eff y duración mínimos;
- surrogates validados;
- estabilidad a block length, periodos y especificaciones adversas preregistradas;
- sin un único fold/activo/régimen catastrófico según definición congelada.

Fallo de significancia con potencia suficiente → `NO_REPLICABLE_STRUCTURE_WITHIN_SCOPE`.
Fallo de potencia/soporte → `INSUFFICIENT_EVIDENCE`.

### Gate G2 — Predictibilidad y calibración

Todos obligatorios:

- predictions causales y OOS para cada origen;
- mejora de score propio frente al benchmark con intervalo FWER-compatible;
- calibración aceptable según intercepto/slope/reliability preregistrados;
- cobertura/abstención suficiente;
- estabilidad por fold y ningún criterio catastrófico;
- confirmation abierto una sola vez sin cambios posteriores.

Fallo → `STATISTICAL_STRUCTURE_ONLY` o `NO_PREDICTIVE_ADVANTAGE`.

### Gate G3 — Réplica independiente

Todos obligatorios:

- mismo signo y definición de efecto;
- segunda fuente o periodo futuro verdaderamente no tocado;
- especificación única, sin nuevo grid search;
- FWER/potencia y calidad de datos aprobadas;
- heterogeneidad explicada sin eliminar retrospectivamente subperiodos.

Aprobación → `ECONOMIC_EVALUATION_ELIGIBLE`.

### Gate G4 — Economía, fuera de este protocolo

Requiere un documento separado y congelado con producto/contrato exacto, quotes/proposals/fills, payout, spread, slippage, comisiones, rollover, latencia, disponibilidad, capacidad y riesgo. Debe comparar EV neto contra no operar y una alternativa ejecutable, con inferencia temporal y nueva evidencia sellada.

Hasta G4 aprobado:

```yaml
profitability_claim: false
paper_eligibility: false
demo_eligibility: false
real_money_eligibility: false
```

### Criterios de parada inmediata

- leakage o acceso al holdout;
- surrogate inválido;
- pérdida de lineage o cambio de definición no versionado;
- derechos de datos incompatibles;
- FWER empírica fuera de control;
- resultado dependiente de una única elección no preregistrada;
- calibración degenerada, soporte de régimen insuficiente o economía inferida indebidamente.

Los resultados negativos no se borran; se registran con el mismo nivel de detalle.

---

## 12. Plantilla concreta de preregistro S3

Copiar, completar y congelar este bloque. Los `TBD` son bloqueantes salvo marca contraria.

```yaml
identity:
  protocol_id: S3-TBD
  version: 1
  status: DRAFT  # DRAFT | FROZEN | COMPLETED | INVALIDATED
  created_at_utc: 2026-11-24T00:00:00Z
  frozen_at_utc: null
  owners: [DevSoul]
  git_commit: TBD
  protocol_sha256: TBD
  prior_families_excluded: [EVEN_ODD, MULTIPLIERS]
  reserved_seed_cohort_61_80: SEALED_NOT_GENERATED_NOT_REUSED

claim:
  research_question: TBD
  claim_level_requested: S1  # S1 structure | S2 prediction | S3 econ-eval candidate
  primary_hypothesis: TBD
  primary_null: TBD
  minimum_relevant_effect: TBD
  prohibited_claims: [PROFITABLE, PAPER_ELIGIBLE, DEMO_ELIGIBLE, REAL_MONEY_ELIGIBLE]

data:
  provider: TBD
  licence_or_permission_ref: TBD
  retention_and_derivative_rights: TBD
  dataset_id: TBD
  dataset_sha256: TBD
  schema_version: TBD
  source_start_utc: TBD
  source_end_utc: TBD
  universe_rule: TBD
  instruments: TBD
  clock: TBD
  frequency_or_event_rule: TBD
  timezone: UTC
  gap_policy: TBD
  duplicate_policy: TBD
  revision_policy: TBD
  outlier_policy: TBD
  row_count: TBD

unit_of_analysis:
  observation: TBD
  prediction_origin: TBD
  target: TBD
  horizon: TBD
  score_unit: TBD
  inferential_block: TBD
  replication_unit: TBD
  clustering: TBD

search_space:
  transforms: TBD
  features: TBD
  lags: TBD
  horizons: TBD
  estimators: TBD
  hyperparameters: TBD
  regime_rules: TBD
  benchmarks: TBD
  total_confirmatory_hypotheses: TBD
  total_exploratory_hypotheses: TBD
  ledger_path_and_hash: TBD

splits:
  discovery: {start: TBD, end: TBD}
  validation: {start: TBD, end: TBD}
  confirmation: {start: TBD, end: TBD, access: SEALED}
  replication: {source_or_period: TBD, access: UNTOUCHED}
  walk_forward: {type: TBD, folds: TBD, train_window: TBD, score_window: TBD}
  max_feature_lookback: TBD
  label_horizon: TBD
  purge: TBD
  embargo: TBD
  warmup_per_fold: TBD

stationarity:
  primary_series_transform: TBD
  adf_spec: TBD
  kpss_spec: TBD
  break_policy: TBD
  rolling_stability_windows: TBD
  ambiguous_result_policy: USE_ROBUST_LOCAL_METHODS

primary_test:
  domain: TBD  # LINEAR | NONLINEAR | MI | ENTROPY | REGIME | CALIBRATION
  statistic: TBD
  parameters: TBD
  null_generator: TBD
  preserved_properties: TBD
  surrogate_validation_tolerances: TBD
  monte_carlo_replicates: 9999
  monte_carlo_seed: TBD  # no usar 61..80
  alternative: TBD

inference:
  alpha: 0.05
  primary_multiplicity: HOLM_OR_BLOCK_MAXT
  discovery_fdr_q: 0.05
  fdr_findings_are_leads_only: true
  bootstrap: STATIONARY_OR_MOVING_BLOCK
  bootstrap_replicates_final: 9999
  block_length_rule_fit_on_train: TBD
  block_length_sensitivity: [0.5x, 1x, 2x]
  effective_sample_size_rule: TBD
  minimum_effective_n: TBD
  minimum_calendar_duration: TBD
  raw_n: TBD
  number_of_independent_clusters: TBD

power:
  effect_injection_model: TBD
  null_scenarios: TBD
  drift_and_regime_scenarios: TBD
  simulation_replicates: TBD
  target_empirical_fwer_max: 0.05
  target_power_min: 0.80
  achieved_power_at_mde: TBD
  stopping_rule: FIXED_DATE_OR_INFORMATION_TBD

prediction_if_applicable:
  event_definition: TBD
  benchmark: TBD
  primary_score: BRIER_OR_LOG_SCORE_TBD
  calibration_method: TBD
  calibration_intercept_bounds: TBD
  calibration_slope_bounds: TBD
  reliability_bins_fit_on_train: TBD
  minimum_coverage: TBD
  catastrophic_fold: TBD

regime_if_applicable:
  detector: TBD
  retrospective_or_online: TBD
  max_regimes_or_breaks: TBD
  minimum_dwell_time: TBD
  minimum_effective_n_per_regime: TBD
  causal_state_availability: TBD

promotion:
  g0_integrity_rule: ALL_REQUIRED
  g1_structure_rule: TBD
  g2_prediction_rule: TBD
  g3_replication_rule: TBD
  sensitivity_rule: ALL_PREREGISTERED_CORE_CHECKS_PASS
  terminal_states:
    - INVALID_STUDY
    - DATA_RIGHTS_BLOCKED
    - INSUFFICIENT_EVIDENCE
    - NO_REPLICABLE_STRUCTURE_WITHIN_SCOPE
    - STATISTICAL_STRUCTURE_ONLY
    - NO_PREDICTIVE_ADVANTAGE
    - REPLICATION_FAILED
    - ECONOMIC_EVALUATION_ELIGIBLE
  profitability_claim: false
  paper_eligibility: false
  demo_eligibility: false
  real_money_eligibility: false

deviations:
  allowed_without_invalidation: [TYPO_ONLY, NON_SEMANTIC_FORMATTING]
  all_other_changes: NEW_PROTOCOL_VERSION_AND_NEW_FUTURE_HOLDOUT
  accidental_holdout_access: INVALIDATE_CONFIRMATION
```

---

## 13. Plantilla del informe final

El informe final debe contener, incluso si el resultado es negativo:

1. protocolo congelado, hashes y desviaciones;
2. manifest/licencia, lineage y auditoría de calidad;
3. diagrama exacto de splits, purge, embargo y warm-up;
4. ledger completo del espacio buscado;
5. nulls y chequeos de fidelidad de surrogates;
6. `n`, `n_eff`, clusters, duración calendario, block length y sensibilidad;
7. tamaños de efecto e intervalos, p-values raw/ajustados, FWER/FDR y potencia;
8. resultados de todos los folds, periodos, instrumentos y regímenes;
9. scores propios, benchmark, calibración y cobertura si aplica;
10. resultados de confirmation y réplica, abiertos sólo conforme al protocolo;
11. una única conclusión terminal y la justificación gate por gate;
12. limitaciones y lista explícita de afirmaciones no permitidas;
13. `profitability_claim=false` salvo que un protocolo económico posterior e independiente lo sustituya con evidencia válida.

Formato mínimo de la decisión:

```yaml
result:
  terminal_state: TBD
  g0_integrity: PASS_OR_FAIL
  g1_structure: PASS_OR_FAIL_OR_NOT_RUN
  g2_prediction: PASS_OR_FAIL_OR_NOT_RUN
  g3_replication: PASS_OR_FAIL_OR_NOT_RUN
  confirmation_opened_once: TBD
  seeds_61_80_remained_sealed: true
  primary_effect: TBD
  confidence_interval: TBD
  multiplicity_adjusted_p: TBD
  raw_n: TBD
  effective_n: TBD
  empirical_fwer: TBD
  power_at_mde: TBD
  profitability_claim: false
  economic_evidence: NOT_EVALUATED
```

---

## 14. Recomendación científicamente prudente

1. **Empezar estrecho:** un instrumento/fuente permisible, una transformación causal, una pregunta primaria, pocos lags/horizontes y un benchmark simple.
2. **Usar discovery para descartar, no para confirmar.** Toda señal descubierta se congela como una única hipótesis antes de confirmation.
3. **Tratar los tests de no linealidad como diagnósticos condicionados al null.** Primero remover y validar estructura lineal/volatilidad; luego usar IAAFT/model-based surrogates.
4. **Priorizar efecto, intervalo, potencia y réplica sobre p-values.** Un resultado pequeño pero significativo con gran `n` puede ser irrelevante; uno no significativo y subpotente es inconcluso.
5. **Exigir FWER para el gate.** FDR sirve para ordenar leads, no para promoción.
6. **No abrir confirmation si G0, potencia o fidelidad de surrogates fallan.** Preservar el holdout tiene más valor que obtener otra cifra.
7. **Separar formalmente estadística y economía.** Aun con réplica predictiva, el siguiente documento debe modelar el contrato ejecutable y costos observados. La salida honesta de S3 puede ser negativa o `ECONOMIC_EVALUATION_ELIGIBLE`; ninguna implica rentabilidad.
8. **Mantener selladas las semillas 61–80 para siempre en este protocolo.** Si ya fueron reservadas para una hipótesis cerrada, reutilizarlas degradaría la trazabilidad y no aportaría independencia real.

---

## 15. Fuentes metodológicas primarias

Consultadas/verificadas mediante sus DOI; las decisiones del protocolo no dependen de una única referencia.

### Dependencia lineal, estacionariedad y regímenes

- Ljung, G. M. y Box, G. E. P. (1978), “On a measure of lack of fit in time series models”. DOI: <https://doi.org/10.1093/biomet/65.2.297>.
- Phillips, P. C. B. y Perron, P. (1988), “Testing for a unit root in time series regression”. DOI: <https://doi.org/10.1093/biomet/75.2.335>.
- Kwiatkowski, D. et al. (1992), “Testing the null hypothesis of stationarity against the alternative of a unit root”. DOI: <https://doi.org/10.1016/0304-4076(92)90104-Y>.
- Hamilton, J. D. (1989), “A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle”. DOI: <https://doi.org/10.2307/1912559>.
- Bai, J. y Perron, P. (1998), “Estimating and Testing Linear Models with Multiple Structural Changes”. DOI: <https://doi.org/10.2307/2998540>.

### No linealidad, información y entropía

- Theiler, J. et al. (1992), “Testing for nonlinearity in time series: the method of surrogate data”. DOI: <https://doi.org/10.1016/0167-2789(92)90102-S>.
- Schreiber, T. y Schmitz, A. (1996), “Improved Surrogate Data for Nonlinearity Tests” (IAAFT). DOI: <https://doi.org/10.1103/PhysRevLett.77.635>.
- Fraser, A. M. y Swinney, H. L. (1986), “Independent coordinates for strange attractors from mutual information”. DOI: <https://doi.org/10.1103/PhysRevA.33.1134>.
- Schreiber, T. (2000), “Measuring Information Transfer”. DOI: <https://doi.org/10.1103/PhysRevLett.85.461>.
- Pincus, S. M. (1991), “Approximate entropy as a measure of system complexity”. DOI: <https://doi.org/10.1073/pnas.88.6.2297>.
- Richman, J. S. y Moorman, J. R. (2000), “Physiological time-series analysis using approximate entropy and sample entropy”. DOI: <https://doi.org/10.1152/ajpheart.2000.278.6.H2039>.

### Remuestreo, calibración y selección múltiple

- Künsch, H. R. (1989), “The Jackknife and the Bootstrap for General Stationary Observations”. DOI: <https://doi.org/10.1214/aos/1176347265>.
- Politis, D. N. y Romano, J. P. (1994), “The Stationary Bootstrap”. DOI: <https://doi.org/10.1080/01621459.1994.10476870>.
- Gneiting, T. y Raftery, A. E. (2007), “Strictly Proper Scoring Rules, Prediction, and Estimation”. DOI: <https://doi.org/10.1198/016214506000001437>.
- Benjamini, Y. y Hochberg, Y. (1995), “Controlling the False Discovery Rate”. DOI: <https://doi.org/10.1111/j.2517-6161.1995.tb02031.x>.
- Holm, S. (1979), “A Simple Sequentially Rejective Multiple Test Procedure”. URL estable JSTOR: <https://www.jstor.org/stable/4615733>.
- White, H. (2000), “A Reality Check for Data Snooping”. DOI: <https://doi.org/10.1111/1468-0262.00152>.
- Hansen, P. R. (2005), “A Test for Superior Predictive Ability”. DOI: <https://doi.org/10.1198/073500105000000063>.

---

## 16. Checklist de freeze

- [ ] Familia nueva e independiente; Even/Odd y Multipliers excluidos.
- [ ] Semillas 61–80 siguen selladas, no generadas y no reutilizadas.
- [ ] Derechos de datos y retención resueltos.
- [ ] Pregunta, unidad, target, horizonte y benchmark congelados.
- [ ] Ledger del espacio de búsqueda completo.
- [ ] Splits por fecha, purge, embargo y warm-up congelados.
- [ ] Nulls/surrogates y propiedades preservadas declarados.
- [ ] Tests de fidelidad de surrogates definidos.
- [ ] `n_eff`, bloques, clusters y duración mínima definidos.
- [ ] FWER/FDR y familia de multiplicidad definidas.
- [ ] MDE, potencia, falso positivo empírico y parada definidos.
- [ ] Gate de calibración y score propio definido si aplica.
- [ ] Regímenes retrospectivos separados de estados causales.
- [ ] Confirmation inaccesible y réplica identificada.
- [ ] Estados terminales y criterios catastróficos congelados.
- [ ] Economía contractual explícitamente diferida a otro protocolo.
- [ ] No quedan `TBD` bloqueantes.
