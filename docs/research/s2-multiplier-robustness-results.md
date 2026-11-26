# S2 — Resultado del gate de robustez Multipliers

Fecha de ejecución: 2026-11-24
Protocolo: `docs/research/s2-multiplier-robustness-protocol.md`

## Decisión

`NO_EDGE`

- Gate aprobado: no.
- Holdout reservado 61–80 abierto: no.
- `PAPER_ELIGIBLE`: no.
- Afirmación de rentabilidad: no.
- Métricas económicas disponibles: no.

La decisión fue emitida automáticamente por los criterios congelados antes de ejecutar las semillas de desarrollo 21–60.

## Integridad

- 40/40 semillas ejecutadas para cada proceso primario.
- 40/40 semillas puntuables en OU y random walk.
- Semillas exploratorias 1–20 excluidas.
- Semillas reservadas 61–80 no generadas por el runner.
- Holdouts estructurales abiertos: 0.
- Baseline aleatorio calibrado exclusivamente en train.
- Bootstrap pareado: 5.000 remuestras, intervalo bilateral 95%, seed estadística 20261123.

## Configuración primaria

`delta_brier = brier_estrategia - brier_aleatorio`; valores negativos favorecen la estrategia.

| Proceso | Delta medio | IC bootstrap 95% | Wins / 40 | Target rate estrategia | Target rate aleatorio | Gate descriptivo |
|---|---:|---:|---:|---:|---:|---|
| Ornstein–Uhlenbeck | -0.0099225150 | [-0.0161337633, -0.0035434795] | 26 | 0.616761 | 0.508507 | Mejora media, pero estabilidad insuficiente |
| Random walk | 0.0042527216 | [-0.0066319641, 0.0148025987] | 14, 4 empates | 0.036939 | 0.032542 | Control negativo sin falso positivo |
| GBM | 0.0069735316 | [0.0011257658, 0.0129595864] | 14 | 0.495050 | 0.489209 | Degradación consistente frente al baseline |
| Regímenes de volatilidad | -0.0245741010 | [-0.0561741374, 0.0057352186] | 21 | 0.408451 | 0.432710 | Media favorable, intervalo cruza cero |

## Sensibilidad OU

| Celda congelada | Delta medio | IC bootstrap 95% | Wins / 40 |
|---|---:|---:|---:|
| Target/stop 0.000025, horizonte 5 | -0.0089855356 | [-0.0155808045, -0.0027079488] | 26 |
| Target/stop 0.00005, horizonte 3 | -0.0111863854 | [-0.0186275436, -0.0040803951] | 28 |
| Target/stop 0.00005, horizonte 5, primaria | -0.0099225150 | [-0.0161337633, -0.0035434795] | 26 |
| Target/stop 0.00005, horizonte 10 | -0.0077375530 | [-0.0203034437, 0.0051295338] | 27 |
| Target/stop 0.0001, horizonte 5 | -0.0002592203 | [-0.0097116426, 0.0090591305] | 21 |

La sensibilidad cumplió 5/5 medias negativas y 4/5 celdas con al menos 24 wins. Esto no rescata el gate primario ni permite seleccionar retrospectivamente horizonte 3.

## Checks fallidos

1. `ou.wins_at_least_28`: observado 26/40.
2. `stress.nonpositive_processes_at_least_3`: observado 2/4.
3. `stress.no_consistent_degradation`: falló porque el límite inferior de GBM fue mayor que cero.

Los demás checks de integridad, control negativo, media/intervalo OU, target rate y sensibilidad pasaron.

## Interpretación

- El detector sí reconoce reversión incorporada deliberadamente en OU, pero la mejora no es suficientemente uniforme entre semillas.
- El control random walk se comportó correctamente: no produjo evidencia falsa de ventaja.
- La degradación estadísticamente consistente en GBM demuestra dependencia de régimen y bloquea promoción.
- El desempeño de regímenes de volatilidad no fue concluyente y su target rate quedó por debajo del baseline.
- Los procesos son proxies propios. Nada de esto demuestra una ventaja sobre índices sintéticos de Deriv.

## Consecuencia científica

El protocolo ordena cerrar esta hipótesis como `NO_EDGE` dentro del alcance evaluado. No se abre la cohorte 61–80 y no se reajustan target, stop u horizonte usando estos resultados. Un trabajo futuro tendría que formular una hipótesis nueva, preregistrada y causalmente distinta; no puede presentar una configuración de esta matriz como confirmación independiente.

## Impacto operativo y costos

- Ejecución local y offline.
- Llamadas a Deriv o terceros: 0.
- Persistencia de datos Deriv: 0.
- Recursos GCP creados o modificados: 0.
- Logs, métricas o almacenamiento GCP adicionales: 0.
- Costo GCP incremental estimado: USD 0.
