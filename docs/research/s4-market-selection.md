# S4 — Selección de mercado: cripto Spot como punto de partida

Fecha: 2026-11-24
Estado: `ASSESSMENT_ONLY — NO EXECUTION`

## 1. Por qué cripto Spot primero

S4 exige mercados convencionales con fuentes históricas autorizadas. Dentro de las
opciones evaluadas (FX minorista, acciones, futuros, cripto), cripto Spot es el
punto de partida técnicamente más accesible:

- **Mercado 24/7**, sin gaps de horario de mercado ni problemas de cierre nocturno.
- **APIs públicas de market data** con histórico de velas accesible sin contrato de
  datos previo (aunque la retención exige verificación jurídica — ver
  `s4-data-provider-assessment.md`).
- **Sin apalancamiento obligatorio**: Spot encaja con la restricción "sin
  apalancamiento" (a diferencia de futuros/margen).
- **Barreras de entrada bajas** y pares muy líquidos (BTC, ETH).

Limitaciones que condicionan la viabilidad:

- Volatilidad alta → drawdowns grandes; exige límites de riesgo estrictos.
- Fee/spread drag: las comisiones spot típicas (0.1%–0.6% por lado) son un costo
  material en horizontes de minutos.
- La ambigüedad de derechos de retención de histórico (común a todos los exchanges)
  es el gate principal.

## 2. Mercados descartados en esta etapa (y por qué)

| Mercado | Motivo de descarte inicial |
|---|---|
| FX minorista spot/CFD | Capítulo venue ya cerrado (ADR-011); ningún broker aprobado por datos |
| Acciones (equities) | Market data con licencia contractual costosa; horarios de mercado |
| Futuros/derivados | Implican apalancamiento/rollover; fuera del alcance sin margen |
| Índices sintéticos (Deriv) | EPHEMERAL_ONLY; sin histórico licenciado (S3) |

Cripto Spot es el único mercado convencional que, a priori, combina API pública de
histórico + ejecución sin apalancamiento + mercado continuo. No se descarta que en
una etapa posterior se evalúe otro mercado, pero no sin repetir esta diligencia.

## 3. Universo de activos (selección objetiva)

Criterios congelados (umbrales numéricos se fijan en el preregistro de S4.1):

1. Par Spot contra USDT (y/o USDC) en el proveedor elegido.
2. Capitalización de mercado y volumen diario por encima de umbrales preregistrados.
3. Antigüedad de listado mínima (histórico suficiente).
4. Spread medio bajo y fee tier competitivo.

Universo objetivo: **3–6 activos** líquidos. Punto de partida natural: BTC/USDT y
ETH/USDT (libros más profundos, menor spread), más 1–4 large-caps seleccionados
por los criterios. Evitar: tokens de listado reciente, baja capitalización, pares
ilíquidos (riesgo de wash trading y slippage).

## 4. Horizonte

- Velas de 1m/5m/15m/1h.
- Operación de minutos a horas.
- **Excluido HFT** (sub-minuto, arbitraje de latencia).

Fundamento: el horizonte de minutos a horas permite probar estructura de
tendencia/momentum con un número de operaciones suficiente sin incurrir en la
latencia y el costo de ejecución del HFT, y sin la lentitud (y pocas observaciones)
del swing de varios días.

## 5. Baselines de mercado

El listón es alto: cripto ha tenido deriva direccional de largo plazo (BTC/ETH),
por lo que **Buy & Hold es un baseline exigente**, no trivial. Una estrategia
debe superar a Buy & Hold y a efectivo en términos ajustados al riesgo, no solo a
un baseline aleatorio. Esto se mantiene como gate en `s4-alpha-discovery-protocol.md`.

## 6. Riesgos de mercado específicos

- **Fee drag**: a 0.1%–0.6% por lado, una estrategia de minutos paga el equivalente
  a varios puntos porcentuales al año; el EV debe superarlo con margen.
- **Spread/slippage**: el spread medio es una fracción del tick de precio; el
  slippage en pares ilíquidos puede invalidar una señal.
- **Quote/stablecoin risk**: USDT no es riesgo-cero; se puede diversificar a USDC.
- **On/off-ramp Colombia**: conversión COP↔USD/stablecoin es un costo y un riesgo
  de contraparte (ver `s4-economic-feasibility.md`).
- **Manipulación en pares pequeños**: el universo líquido mitiga este riesgo.

## 7. Conclusión de selección

Cripto Spot con un universo pequeño y líquido (BTC, ETH + large-caps), horizonte
de minutos a horas, es el punto de partida defendible para S4. La decisión de
proveedor concreto y la viabilidad económica están en
`s4-data-provider-assessment.md` y `s4-economic-feasibility.md`. Si ningún
proveedor desbloquea retención de histórico dentro del presupuesto, la etapa se
detiene (condición explícita del mandato S4).
