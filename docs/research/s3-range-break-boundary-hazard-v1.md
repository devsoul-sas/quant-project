# S3 — Preregistro RANGE_BREAK_BOUNDARY_HAZARD_V1

Fecha de creación: 2026-11-24
Estado: `DRAFT — POWER_GATE_UNDERPOWERED` (no pasa a FROZEN; ver análisis de potencia)

## 0. Veredicto anticipado (lectura rápida)

El preregistro se diseñó íntegro, pero el **análisis de potencia** (documento
`docs/research/s3-range-break-power-analysis.md`) concluye que la hipótesis
primaria **no alcanza ≥80% de potencia dentro de una sesión efímera**. Aplicando
la condición de cancelación comprometida en `s3-decision-matrix.md`, el estudio
queda en:

```text
UNDERPOWERED — DO_NOT_RUN
```

No se abre confirmation. No se corre la sesión de observación. El documento que
sigue deja el diseño congelable por si el usuario, en el futuro, autoriza
replantear la unidad de análisis o aportar una fuente persistente.

## 1. Identidad

```yaml
identity:
  protocol_id: S3-RBBH-001
  version: 1
  status: DRAFT            # no FROZEN: power gate falla
  created_at_utc: 2026-11-24
  frozen_at_utc: null      # permanece null salvo replanteo con potencia
  owners: [DevSoul]
  git_commit: uncommitted
  protocol_sha256: d2a7451ac0db06b562a66a5dd8ae33e5e3f9ab98a9ca9f8c0ba7e5c86fb9ec8f
  prior_families_excluded: [EVEN_ODD, MULTIPLIERS]
  reserved_seed_cohort_61_80: SEALED_NOT_GENERATED_NOT_REUSED
```

## 2. Hipótesis

```yaml
claim:
  research_question: >
    ¿La probabilidad de ruptura de rango (hazard) aumenta con el conteo causal
    de impactos en el límite, por encima de un proceso de renovación sin memoria
    calibrado en train?
  claim_level_requested: S1          # estructura (no predicción, no economía)
  primary_hypothesis: >
    El hazard de ruptura NO es constante: la tasa de ruptura por impacto es
    mayor en la fase tardía (edad >= media/2) que en la temprana.
  primary_null: >
    Renovación sin memoria: cada impacto provoca ruptura con probabilidad
    constante p; los conteos de impactos hasta ruptura son geométricos.
  minimum_relevant_effect: "HR = 2.0 (tasa tardía / tasa temprana), one-sided"
  prohibited_claims: [PROFITABLE, PAPER_ELIGIBLE, DEMO_ELIGIBLE, REAL_MONEY_ELIGIBLE]
```

## 3. Datos y retención

```yaml
data:
  provider: Deriv
  instrument_family: Range Break
  instrument_variant: "Range Break 100 (media de 100 impactos por ruptura)"
  instrument_symbol: "descubierto vía active_symbols en sesión; NO hard-codeado"
  licence_or_permission_ref: "Deriv API Users Terms + ADR-012 EPHEMERAL_ONLY"
  retention_and_derivative_rights: >
    Ninguno persistente. Memoria únicamente, TTL estricto <24 h, zeroización al
    cerrar. Sin CSV/Parquet/PostgreSQL. Sin dataset persistido -> sin dataset_sha256.
  dataset_id: EPHEMERAL_SESSION
  dataset_sha256: N/A (no hay persistencia)
  universe_rule: >
    Un único instrumento: Range Break 100. NO probar 200 en esta hipótesis
    (evita multiplicidad y selección retrospectiva 100 vs 200).
  clock: epoch/ticks del proveedor
  frequency_or_event_rule: "unidad de exposición = impacto de límite"
  timezone: UTC
  gap_policy: "desconexión > umbral preregistrado invalida el segmento; reconexión reinicia warm-up"
  duplicate_policy: "deduplicar por epoch"
  outlier_policy: "sin recorte; los spikes son la señal de ruptura"
```

## 4. Unidad de análisis

```yaml
unit_of_analysis:
  observation: "impacto de límite: tick que toca/cruza el límite actual del rango"
  prediction_origin: "estado causal al inicio del impacto (edad del rango, posición normalizada)"
  target: "¿este impacto resulta en ruptura? {break, bounce}"
  horizon: 1
  score_unit: impacto
  inferential_block: "ciclo de rango (impactos del mismo ciclo correlacionados)"
  replication_unit: "sesión efímera independiente"
  clustering: "por ciclo de rango"
```

## 5. Definición causal del estado (riesgo de leakage — congelado)

El índice no expone límites, impactos ni rupturas; deben **inferirse solo con
pasado**. Reglas congeladas a priori desde el mecanismo publicado, sin usar
futuro:

1. **Límites:** tras detectar una ruptura, los límites se re-inicializan con los
   extremos (máx/mín) de las últimas `W` ticks previas a la ruptura. `W` se
   congela en la fase de caracterización con criterio de mecanismo (ancho típico
   del rango en ticks), nunca ajustado al outcome.
2. **Impacto:** tick cuyo precio alcanza el límite vigente (dentro de `epsilon`
   ticks, con `epsilon` congelado) y NO lo excede.
3. **Ruptura (break):** tick cuyo precio cruza el límite vigente por más de
   `delta` ticks. Tras la ruptura, se abre un ciclo nuevo y la edad se reinicia a 0.
4. **Edad del rango:** conteo de impactos desde la última ruptura.
5. **Fase:** `temprana` si `edad < 50`, `tardía` si `edad >= 50` (media publicada = 100).

`W`, `epsilon` y `delta` son los parámetros de inferencia más sensibles a
leakage. Se congelan en la **fase de caracterización** (hipótesis-free), usando
solo agregados de mecanismo (tasa de ruptura, ancho de rango), **nunca**
optimizándolos contra el resultado del test. Cualquier ajuste posterior invalida
la confirmation.

## 6. Espacio de búsqueda (1 hipótesis, 0 exploratorias)

```yaml
search_space:
  transforms: [edad_del_rango, posicion_normalizada, signo_ultimo_movimiento]
  features: ["bin de edad: temprana (edad<50) vs tardía (edad>=50)"]
  lags: 0                       # causal
  horizons: [1]
  estimators: "comparación de tasas (log-rank / score test one-sided)"
  hyperparameters: {corte_fase: 50}
  regime_rules: "ningún detector retrospectivo; el estado es la edad causal"
  benchmarks: ["renovación sin memoria (geométrica)", "no-operar"]
  total_confirmatory_hypotheses: 1
  total_exploratory_hypotheses: 0
  ledger_path_and_hash: "ledger del preregistro; hash en identidad"
```

## 7. Fases (intrasesión efímera)

```yaml
splits:
  characterization:
    purpose: "medir tasa de ruptura y congelar W/epsilon/delta (hipótesis-free)"
    access: OPEN
  confirmation:
    purpose: "test primario sobre sesión efímera FRESCA e independiente"
    access: SEALED             # solo tras aprobar GO y potencia
  replication:
    purpose: "sesión adicional independiente"
    access: UNTOUCHED
  max_feature_lookback: "hasta el último break (reset de edad)"
  label_horizon: 1
  warmup_per_session: "primer ciclo completo descartado (inferencia sin historia)"
```

## 8. Test primario

```yaml
primary_test:
  domain: REGIME              # heterogeneidad de hazard por estado causal
  statistic: "z one-sided de diferencia de tasas de ruptura tardía vs temprana"
  parameters: {corte: 50, p_estimado: "train (caracterización)"}
  null_generator: "simulación geométrica (renovación sin memoria) calibrada en train"
  preserved_properties: ["tasa media de ruptura", "conteo total de impactos"]
  surrogate_validation_tolerances: {tasa: "<= 5% de desviación"}
  monte_carlo_replicates: 9999
  monte_carlo_seed: 12345      # fuera de 61..80
  alternative: greater         # one-sided
```

## 9. Inferencia y potencia

```yaml
inference:
  alpha: 0.05
  primary_multiplicity: NONE   # 1 hipótesis primaria
  discovery_fdr_q: 0.05
  fdr_findings_are_leads_only: true
  bootstrap: MOVING_BLOCK
  bootstrap_replicates_final: 9999
  block_length_rule_fit_on_train: "correlación de impactos estimada en train"
  block_length_sensitivity: [0.5x, 1x, 2x]
  effective_sample_size_rule: "n_eff = n_impactos / (1 + 2*sum(rho))"
  minimum_effective_n: 52      # rupturas para HR=2.0 @ power 0.80 (one-sided)
  raw_n: 52

power:
  effect_injection_model: >
    hazard por impacto p(a) = p0*lambda_e (edad<50), p0*lambda_l (edad>=50),
    lambda_l/lambda_e = HR, media preservada
  null_scenarios: "renovación geométrica p = 1/100"
  drift_and_regime_scenarios: "deriva de la tasa media dentro de la sesión"
  simulation_replicates: 20000
  target_empirical_fwer_max: 0.05
  target_power_min: 0.80
  achieved_power_at_mde: 0.91    # empírica en N=52 (fórmula conservadora)
  stopping_rule: "FIXED_EVENTS_52_OR_SESSION_CAP"
  verdict: UNDERPOWERED_DO_NOT_RUN   # ver documento de potencia
```

## 10. Dirección de ruptura (secundario, no confirmatorio)

```yaml
prediction_if_applicable:
  event_definition: "dirección de la ruptura {up, down}"
  benchmark: "frecuencia de dirección en train"
  primary_score: N/A          # el primario es un test de tasa, no un score
  status: SECONDARY_ONLY
```

## 11. Promoción y estados terminales

```yaml
promotion:
  g0_integrity_rule: ALL_REQUIRED
  g1_structure_rule: "z one-sided > 1.645 con n_eff >= 52 y fidelidad de surrogates OK"
  g2_prediction_rule: N/A     # claim S1
  g3_replication_rule: "réplica en sesión independiente"
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

## 12. Resultado actual

```yaml
result:
  terminal_state: INSUFFICIENT_EVIDENCE
  g0_integrity: NOT_RUN
  g1_structure: NOT_RUN
  g2_prediction: NOT_RUN
  g3_replication: NOT_RUN
  confirmation_opened_once: false
  seeds_61_80_remained_sealed: true
  power_at_mde: UNDER_0.80_WITHIN_EPHEMERAL_SESSION
  profitability_claim: false
  economic_evidence: NOT_EVALUATED
  reason: >
    El test primario exige ~52 rupturas (HR=2.0 @ 0.80). A 1 impacto/s y Range
    Break 100 son ~1.4 h de ticks continuos; con tasas de impacto realistas,
    3-15+ h. Inalcanzable en una sesión efímera fail-closed. DO_NOT_RUN.
```

## 13. Referencias metodológicas

- Schoenfeld, D. (1983), "Sample-size formula for the proportional-hazards
  regression model", Biometrics 39(2):499–503. La fórmula de eventos usada en el
  análisis de potencia.
- Protocolo S3 (sección 12): plantilla de preregistro que este documento instancia.
- Decisión S3: `docs/research/s3-decision-matrix.md` (condición de cancelación).
