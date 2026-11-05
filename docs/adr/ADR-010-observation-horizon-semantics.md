# ADR-010 — Semántica causal del horizonte de observaciones

- Estado: aceptada y congelada para la hipótesis existente
- Fecha: 2026-11-05

## Contexto

La documentación describía `duration=5` informalmente como «cinco días». El replay
real no usa días calendario: opera sobre una secuencia de observaciones válidas y
ordenadas. Confundir ambas cosas invalidaría el mapeo a un producto ejecutable.

## Decisión

Para la hipótesis EURGBP mean-reversion L=10/D=5 ya evaluada:

1. la historia de señal termina en `F_t`;
2. la entrada causal es la siguiente observación disponible, `F_{t+1}`;
3. `duration=5` cuenta cinco intervalos observados desde la entrada;
4. la salida es `F_{t+6}`;
5. el outcome es `sign(F_{t+6} - F_{t+1})` en la dirección CALL/PUT;
6. no se interpolan festivos o faltantes;
7. `duration=5` **no significa** cinco días calendario ni una expiración `5d`.

Esta semántica corresponde al código y a los resultados BCE/H.10 existentes. No se
modifica para mejorar equivalencia con un broker.

## Consecuencias para ejecución

- Una opción con `duration_unit="d"` y `duration=5` no es equivalente por defecto.
- Deriv solo podría mapearse si una expiración absoluta representa la quinta
  observación futura bajo una regla preregistrada, y si strike, regla de empate y
  economía son equivalentes y persistibles.
- Spot/CFD requiere entrada ejecutable después de la publicación y salida bajo una
  regla fija asociada a la quinta observación; el fixing no es bid/ask.
- Cambiar a cinco días calendario constituye una hipótesis nueva y no hereda el hit
  rate ni el holdout actual.
- El holdout permanece sellado hasta demostrar equivalencia temporal y económica.

## Gate de equivalencia

PASS solo si se congelan el timestamp de publicación `a_t`, la entrada ejecutable
`tau_t >= a_t`, la salida `T_t`, la política de festivos/faltantes y un producto que
reproduzca la misma ventana sin seleccionar fechas ex post.

FAIL si persiste ambigüedad entre `F_t -> F_{t+5}` y
`F_{t+1} -> F_{t+6}`, si se sustituye por `5d` calendario o si el producto no admite
la expiración necesaria.

## Invariantes

- `promotion_eligibility = NOT_ELIGIBLE`
- `profitability_claim = False`
- `real_money = EXCLUDED`
