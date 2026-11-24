# ADR-011 — Cierre del capítulo venue y pivote estratégico

- Estado: aceptada
- Fecha: 2026-11-05

## Contexto

La búsqueda de un venue primario de ejecución spot/CFD FX (EURGBP, demo/paper,
admisión de residente colombiano, economía observada y derechos de persistencia para
investigación potencialmente comercial) fue agotada de forma escrita y fail-closed.
Ninguno de los candidatos evaluados resultó aprobado:

- **IG International** — swaps, slippage y derechos de datos bloqueados.
- **Interactive Brokers** — exige cuenta real financiada; non-display/derived data sin
  aclaración.
- **OANDA** — entidad Colombia/EURGBP/licencia no resueltas.
- **Darwinex Zero** — capa de track-record sobre capital virtual, no es venue.
- **Darwinex Global (Tradeslide Global Ltd, FSA SD171)** — Colombia como opción
  condicional y EURGBP publicado, pero sin licencia escrita de datos/derivados.
- **Darwinex UK (Tradeslide Trading Tech Ltd, FCA FRN 586466)** — el `Client Agreement`
  (May 2023) **prohíbe expresamente** retransmitir/redistribuir el dato (9.1(d)), limita
  su uso al propósito del contrato (9.1(c)) y exige **consentimiento previo escrito** para
  herramientas de trading automático (9.6); el `DARWIN API T&C` restringe el dato a
  "internal purposes" (3.2), ordena su borrado al revocar (3.4) y reserva a Darwinex todo
  "derivative work" (6).

El patrón es estructural: ningún broker retail concede por escrito retención reproducible
de bid/ask + derivados con fines comerciales. En paralelo, la hipótesis EURGBP
mean-reversion L=10/D=5 — real en estadística (54.75% de acierto) — **no sobrevive los
costos ejecutables** (~2 pips; falla a 5) y la aritmética de Deriv Options es perdedora
(break-even 55.13% > 54.75%). BCE y Fed H.10 son fixings diarios, no precios ejecutables.

## Decisión

1. **Cerrar el capítulo venue de FX retail.** No se persigue más venue spot/CFD ni se
   envían consultas formales a brokers por correo (decisión del propietario, 2026-11-05).
2. Los invariantes científicos permanecen y no se relajan:
   - `profitability_claim = False`
   - `promotion_eligibility = NOT_ELIGIBLE`
   - `real_money = EXCLUDED`
   - `holdout_opened = False`
3. **Pivote estratégico** hacia dos frentes que reutilizan el activo real del proyecto
   (rigor metodológico + ingeniería Python/TDD + perfil de ciencia de datos + idioma
   español), sin depender de un venue de ejecución:
   - **Cuant crowdsourced** (Numerai, WorldQuant BRAIN): monetizar la calidad de
     predicción sin capital, sin broker y sin derechos de datos de mercado.
   - **Producto educativo/metodológico en español**: empaquetar la validación
     científica de estrategias ("trading algorítmico con validación reproducible") como
     contenido/herramienta.

## Consecuencias

- La hipótesis EURGBP queda registrada como **conclusión negativa válida**: no hay edge
  económico demostrable tras costos. No se hereda a la nueva dirección.
- El núcleo de ingeniería (replay determinista, ledger hash-chained, provenance
  OBSERVED/ESTIMATED/UNAVAILABLE, guardas fail-closed, reloj inyectable) se conserva
  como activo metodológico y reutilizable en backtesting para el pivote.
- No se construye más infraestructura de ejecución de FX retail ni se reabre la
  evaluación de venues.
- El holdout BCE permanece sellado y no se abre.
- No se habilita dinero real, promoción ni paper/demo orientado a demostrar edge.

## Invariantes

- `profitability_claim = False`
- `promotion_eligibility = NOT_ELIGIBLE`
- `real_money = EXCLUDED`
- `holdout_opened = False`
- Ninguna afirmación de rentabilidad se fabrica; la conclusión negativa es un resultado
  válido.
