# Resultado del barrido de edge diario (BCE)

- Fecha: 2026-11-04
- Estado: preliminar — NO promocionable, NO operable
- Método: [protocolo económico](economic-protocol.md) + corrección Bonferroni

## Alcance

Barrido sistemático sobre fixings diarios del BCE (EUR base), 4 pares
(EURUSD, EURJPY, EURGBP, EURCHF), 1999–2026 (~7.129 días por par):

- estrategias: momentum y mean-reversion con ventana N;
- lookback N en {1, 2, 5, 10, 20}, duración D en {1, 5, 10, 20};
- spread relativo s en {0, 0.0001, 0.001};
- 120 configuraciones por par (480 en total), walk-forward de 5 folds +
  holdout sellado.

Cada configuración se puntúa con un intervalo bootstrap por bloques ajustado
por Bonferroni (`confidence = 1 − 0.05/n_tests`), de modo que el barrido de 120
configuraciones por par no infle la tasa de falsos descubrimientos.

## Resultado

| Par | Configs con edge (family-wise) | Máx. límite inferior bootstrap |
|---|---|---|
| EURUSD | 0 | 0.4863 |
| EURJPY | 0 | 0.4858 |
| EURGBP | 7 | 0.5314 |
| EURCHF | 1 | 0.5004 |

EURUSD y EURJPY no muestran señal direccional. EURGBP concentra las 7
configuraciones con `bootstrap_lower > 0.50`; todas son mean-reversion, ninguna
momentum.

## Deep-dive EURGBP

La señal más fuerte es mean-reversion con lookback 10 y duración 5 (sin spread):

- hit rate direccional: 0.5678 (56.78 %);
- hit rate por fold: 0.5551, 0.5763, 0.5551, 0.6271, 0.5254 (consistencia 0.1017);
- robusto al seed del bootstrap (límite inferior entre 0.5288 y 0.5373);
- sobrevive 1 pip de fricción (hit 0.5636, límite inferior 0.5271);
- NO sobrevive 10 pips (spread 0.001) — el efecto es de unos pocos pips netos.

El patrón es coherente (mean-reversion de medio plazo, horizonte 5–10 días),
no un outlier aislado del barrido.

## Caveats (por qué esto NO es un edge confirmado)

1. El fixing del BCE es mid-point sin bid/ask ejecutable; un artefacto de
   redondeo o de convención del fixing podría producir reversión espuria.
2. La evidencia proviene de una sola fuente (BCE); no hay validación con una
   fuente independiente de precios FX.
3. El holdout sellado sigue sin abrirse; abrirlo exige congelar un
   `StrategyRelease` y solo puede hacerse una vez.
4. El efecto neto es de pocos pips y no se ha contrastado contra costos reales
   de un broker concreto.

## Conclusión

Existe una señal preliminar de mean-reversion en EURGBP, estable en el tiempo y
robusta al seed, pero no verificable como edge económico sin (a) una fuente
independiente y (b) la apertura del holdout tras congelar la estrategia. No se
promociona ni se opera: `promotion_eligibility = NOT_ELIGIBLE` y
`profitability_claim = False` siguen vigentes.
