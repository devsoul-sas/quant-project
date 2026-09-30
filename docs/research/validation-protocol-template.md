# Plantilla de protocolo de validación cuantitativa

> Debe completarse, versionarse y congelarse antes de abrir el holdout final o iniciar una corrida formal. Los campos `TBD` bloquean la promoción científica.

## 1. Identidad

```yaml
protocol_id: TBD
protocol_version: 1
status: DRAFT  # DRAFT | FROZEN | COMPLETED | INVALIDATED
created_at: TBD
frozen_at: null
owners: [DevSoul]
research_question: TBD
primary_hypothesis: TBD
null_hypothesis: TBD
```

## 2. Unidad experimental y universo

```yaml
provider: TBD
product: options
contract_family: rise_fall
contract_types: [CALL, PUT]
symbols: TBD
duration: 5
duration_unit: t
currency: TBD
basis: stake
unit_of_observation: contract_decision
prediction_time_definition: TBD
outcome_time_definition: settlement
barrier_definition: TBD
exit_policy: expiry
```

La selección de símbolos y contrato debe congelarse antes del holdout. Agregar o quitar símbolos crea un protocolo nuevo.

Gate previo obligatorio:

```yaml
data_source: TBD
data_licence_or_written_permission: TBD
retention_period: TBD
derived_artifacts_retention_allowed: TBD
partner_display_allowed: TBD
```

Ningún protocolo puede pasar a `FROZEN` mientras estos campos sigan en `TBD`. Para Deriv, los API Users Terms actuales solo autorizan caché de hasta 24 horas salvo permiso adicional.

## 3. Calidad económica

```yaml
accepted_economics_modes:
  research: [TICK_PROXY_BACKTEST, QUOTE_REPLAY_BACKTEST]
  promotion_to_demo: [QUOTE_REPLAY_BACKTEST]
proposal_capture_required_fields:
  - canonical_request
  - proposal_id
  - ask_price
  - payout
  - spot
  - spot_time
  - date_start
  - date_expiry
  - captured_at
  - schema_release
```

`TICK_PROXY_BACKTEST` puede ayudar a descartar hipótesis, pero no demostrar rentabilidad ni promover a demo.

## 4. Datos y lineage

```yaml
dataset_snapshot_id: TBD
dataset_sha256: TBD
schema_version: TBD
source_start: TBD
source_end: TBD
row_count: TBD
gap_policy: TBD
invalid_data_policy: TBD
feature_set_version: TBD
feature_set_sha256: TBD
max_lookback: TBD
label_horizon: 5t
```

Toda feature debe usar únicamente información disponible en `prediction_time_definition`.

## 5. Splits temporales

```yaml
train:
  start: TBD
  end: TBD
validation:
  start: TBD
  end: TBD
test:
  start: TBD
  end: TBD
walk_forward:
  type: expanding  # o rolling, justificar
  folds: TBD
  train_window: TBD
  validation_window: TBD
  purge: TBD
  embargo: TBD
```

Reglas:

- nunca shuffle aleatorio entre tiempos;
- test permanece sellado hasta congelar release;
- labels superpuestos requieren purga/embargo o justificación estadística;
- una nueva evaluación tras ver test crea release/hipótesis nueva.

## 6. Estrategia y baselines

```yaml
primary_strategy:
  name: TBD
  version: TBD
  git_sha: TBD
  model_sha256: TBD
  random_seed: TBD
baselines:
  - always_wait
  - random_decision
  - simple_momentum
  - simple_mean_reversion
primary_baseline: TBD
```

Regresión logística es el primer modelo estadístico permitido. Árbol pequeño/random forest requiere hipótesis concreta. Modelos complejos quedan excluidos inicialmente.

## 7. Métricas

```yaml
primary_metric: expected_value_per_contract
confidence_method: TBD  # considerar block bootstrap por dependencia temporal
confidence_level: TBD
minimum_relevant_effect: TBD
multiple_testing_correction: TBD
secondary_metrics:
  - net_profit
  - roi
  - profit_factor
  - max_drawdown_absolute
  - max_drawdown_percent
  - longest_losing_streak
  - sortino_ratio
  - exposure
  - wait_rate
  - effective_sample_size
```

Sharpe/Sortino requieren definición explícita de retorno, frecuencia y anualización. Riesgo de ruina requiere fórmula, supuestos y sensibilidad.

## 8. Riesgo pre-registrado

```yaml
initial_balance: TBD
max_stake_pct_balance: TBD
max_daily_loss_pct: TBD
risk_day_timezone: UTC
max_drawdown_pct: TBD
max_concurrent_positions: 1
max_consecutive_losses: TBD
cooldown_after_loss_seconds: TBD
kill_switch_default: true
catastrophic_fold_definition: TBD
```

Los defaults de ingeniería no son valores científicamente óptimos.

## 9. Tamaño de muestra y duración

```yaml
power_or_precision_method: TBD
minimum_effective_sample_size: TBD
minimum_calendar_duration: TBD
maximum_calendar_duration: TBD
stopping_rule: TBD
```

No usar un número universal de trades. Debe derivarse de payout, varianza, dependencia serial y efecto mínimo relevante. No detener temprano por buen resultado salvo regla pre-registrada.

## 10. Gate científico

Regla base, ajustable solo antes de congelar:

```text
lower_bound(CI(EV_OOS)) > preregistered_EV_threshold
AND EV_OOS > primary_economic_baseline
AND max_drawdown <= preregistered_limit
AND effective_sample_size >= preregistered_minimum
AND no fold violates catastrophic_fold_definition
AND sensitivity analysis survives preregistered adverse payout/cost scenario
```

```yaml
EV_threshold: TBD
baseline_margin: TBD
max_drawdown_limit: TBD
adverse_payout_scenario: TBD
promotion_rule: TBD
kill_rule: TBD
```

## 11. Paper run

```yaml
strategy_release: TBD
risk_config_sha256: TBD
start_at: TBD
end_condition: TBD
availability_SLO: TBD
recovery_time_objective: TBD
gap_policy: TBD
manual_intervention_policy: invalidate_or_record
```

Aprobación exige:

- 100% de señales con feature hash, release y risk decision;
- replay reproduce decisiones;
- reinicio no duplica ni pierde posición;
- downtime visible;
- ledger rechaza UPDATE/DELETE sobre eventos cerrados.

## 12. Demo run

```yaml
account_type: demo
account_currency: TBD
credential_scope: least_privilege_trade
stake_policy: TBD
start_at: TBD
end_condition: TBD
```

Aprobación exige:

- arranque rechaza cuenta no-demo;
- cada compra enlaza intent, proposal y contract ID;
- timeout reconcilia antes de reintentar;
- cero compras duplicadas;
- payout, profit y balance reconciliados;
- secretos ausentes de logs;
- kill switch probado.

## 13. Invalidación

Invalidar el run si ocurre cualquiera de:

- cambio de estrategia/features/riesgo/universo tras freeze;
- apertura accidental del holdout;
- leakage confirmado;
- pérdida de lineage o hashes;
- economía mal etiquetada;
- datos/gaps fuera de la política;
- intervención no registrada;
- divergencia contable no explicada;
- uso de cuenta no-demo.

La invalidación no elimina evidencia. Se publica la causa y se crea otro run si procede.

## 14. Informe final obligatorio

- protocolo congelado y hashes;
- periodo y downtime;
- dataset/features/release;
- métricas por train/validation/test/fold;
- intervalos de confianza;
- baselines;
- sensibilidad;
- operaciones/rechazos;
- desviaciones e intervenciones;
- conclusión: promover, rediseñar o descartar;
- limitaciones y afirmaciones que los datos no permiten hacer.
