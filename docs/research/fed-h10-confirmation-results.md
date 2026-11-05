# Confirmación independiente EURGBP — Reserva Federal H.10

- Fecha: 2026-11-04
- Estado: señal direccional replicada — **NO promocionable, NO operable**
- Fuente: Federal Reserve H.10 (dominio público, fixing de Nueva York)
- Hipótesis preregistrada: mean-reversion EURGBP, lookback 10, duración 5 observaciones,
  spread relativo 0.0001 (1 pip)

## Diseño confirmatorio

Esta ejecución no repite el grid search del BCE. Prueba una sola configuración
seleccionada antes de observar H.10:

- estrategia: mean-reversion;
- lookback: 10 observaciones;
- horizonte: 5 observaciones;
- fricción primaria: 0.0001;
- split: purge 20, embargo 5, 5 folds de 252 observaciones;
- holdout: 252 observaciones, sellado y sin abrir;
- bootstrap por bloques: seed 42, intervalo 95 % (una sola hipótesis confirmatoria).

EURGBP se reconstruye como `(USD por EUR) / (USD por GBP)` sobre la intersección
de fechas de las dos series oficiales.

## Evidencia reproducible

Páginas oficiales consultadas:

- EUR: `https://www.federalreserve.gov/releases/h10/hist/dat00_eu.htm`
  - SHA-256: `90be50289028f00214a4e8e8bda8a53c40332ef0c57821450e9bd19adb58579b`
  - tamaño: 1.133.042 bytes
- GBP: `https://www.federalreserve.gov/releases/h10/hist/dat00_uk.htm`
  - SHA-256: `8085bdfc7e88619609beee0f50d57c77cfcfeecb608f4793558d6861c028b325`
  - tamaño: 1.133.042 bytes

> Nota de proveniencia: la página H.10 incrusta la fecha de publicación
> ("…H.10 - November 02, 2026") y muta en cada release, por lo que los hashes
> fijan un snapshot recuperado el 2026-11-04 y no se reproducen byte a byte en
> descargas posteriores (mismo tamaño, hash distinto). Son evidencia del snapshot
> analizado, no una firma de contenido estable.

Los HTML se usaron desde `/tmp` y se eliminaron al terminar. El repositorio no
retiene payloads de proveedor.

## Resultado primario

- observaciones EURGBP comunes: 6.727;
- decisiones en los folds: 1.180;
- hit rate neto de 1 pip: **0.5475 (54.75 %)**;
- bootstrap 95 %: **[0.5161, 0.5822]**;
- folds: 0.5212, 0.5593, 0.5424, 0.5636, 0.5508;
- consistencia (rango de hit rates): 0.0424;
- criterio confirmatorio (`bootstrap_lower > 0.50`): **SUPERADO**.

Los cinco folds quedan sobre 0.50. La replicación usa un fixing independiente
del BCE (Nueva York vs concertación del BCE), por lo que reduce materialmente la
hipótesis de un artefacto exclusivo del fixing del BCE.

## Sensibilidad a fricción

La tabla la regenera `run_fed_h10_eurgbp_sensitivity` (congelada y cubierta por
test); los números que siguen son el resultado del snapshot 2026-11-04.

| Fricción relativa | Aproximación | Hit rate | Bootstrap 95 % | Confirma |
|---:|---:|---:|---:|:---:|
| 0 | 0 pips | 0.5534 | [0.5229, 0.5898] | Sí |
| 0.0001 | 1 pip | 0.5475 | [0.5161, 0.5822] | Sí |
| 0.0002 | 2 pips | 0.5407 | [0.5085, 0.5754] | Sí |
| 0.0005 | 5 pips | 0.5186 | [0.4915, 0.5517] | No |
| 0.0010 | 10 pips | 0.4949 | [0.4636, 0.5263] | No |

Además, para una posición durante cinco observaciones, el costo real debe incluir
spread, slippage y rollover/swap; aún no
existe evidencia de que el costo total sea menor a 5 pips.

## Holdout y promoción

- holdout H.10: 252 observaciones;
- hash sellado:
  `e0e7af27cd8ecff6ed3a5fc6a94d75a56aace92237726b71b40a7a1a8cc14232`;
- abierto: **No**;
- `promotion_eligibility = NOT_ELIGIBLE`;
- métricas económicas/P&L: no disponibles;
- dinero real: excluido.

No se congela todavía un `StrategyRelease` ni se abre el holdout. Antes debe
existir economía ejecutable observada y autorizada para el producto elegido,
durante una ventana equivalente a las cinco observaciones de ADR-010. Abrir el
holdout sin resolver ese gate desperdiciaría la única prueba final.

## Conclusión

La mean-reversion EURGBP L=10/D=5 queda **replicada como señal direccional** en
una segunda fuente independiente y permisiva. No queda demostrada como edge
económico. El siguiente gate es obtener costos ejecutables reales; solo si el
costo total conservador queda dentro del rango que la señal soporta se congela
el release y se abre el holdout una única vez.
