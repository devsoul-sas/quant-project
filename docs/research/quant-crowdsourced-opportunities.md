# Oportunidades de cuant crowdsourced (pivote post-venue)

- Fecha de consulta: 2026-11-05
- Estado: investigación inicial, fuentes oficiales directas
- Marco: ADR-011 cierra el capítulo venue FX; esta línea reutiliza el núcleo de
  backtesting/validación hacia juegos de predicción **sin capital, sin broker y sin
  bloqueo de derechos de datos**.

## Por qué esta dirección

El FX retail es estructuralmente negativo en valor esperado: exige un edge que supere
costos ejecutables y un venue que conceda retención de datos — ambas cosas quedaron
descartadas (ADR-011). El cuant crowdsourced invierte la ecuación:

- la plataforma **provee los datos** (no hay problema de licencia/retención);
- la compensación es **por mérito** (calidad de predicción), no por resultado de ejecución;
- **no hay capital en riesgo** (se puede empezar con cero; el stake es opcional);
- reutiliza exactamente el perfil del proyecto: ciencia de datos, Python, ML y
  validación causal/out-of-sample.

Contrapartida honesta: es **competitivo**. La mayoría de participantes gana poco o nada;
los tramos altos ganan cantidades significativas. Es un juego de EV positivo condicionado
a habilidad, a diferencia del FX retail que es negativo incluso con habilidad moderada.

## Numerai (verificado en docs.numer.ai, 2026-11-05)

- **Qué es**: un torneo de ciencia de datos + hedge fund real. Los modelos de los
  participantes se combinan en un "Meta Model" que el fondo usa para operar.
- **Datos**: dataset gratuito de alta calidad; cada fila = una acción en un instante;
  `features` (atributos conocidos) y `target` (rendimiento futuro). v6 (`Classic`),
  target `target_jupiter_60` a 60 días hábiles.
- **Flujo**: entrenar modelo → generar predicciones `live` diarias (martes–sábado) →
  subir → se puntúa.
- **Scoring**: `Correlation` y `Meta Model Contribution`; rondas de 20 días (4 semanas)
  o 60 días (12 semanas).
- **Compensación**: si haces stake de `NMR` sobre tus predicciones, ganas (o quemas) NMR
  según el score. El stake es opcional; se puede empezar con cero y re-stakear lo ganado.
- **Stack**: cualquier lenguaje; ejemplos oficiales en Python (LightGBM, pandas, pyarrow,
  `numerapi`). No requiere KYC ni capital para participar.

## WorldQuant BRAIN (verificado en worldquantbrain.com/consultant, 2026-11-05)

- **Qué es**: plataforma de simulación para construir "Alphas" (modelos matemáticos que
  predicen movimientos de precio) y contribuir a la investigación de WorldQuant.
- **Escala**: 550 000+ usuarios, 16 000+ consultores, 17 regiones.
- **Datos/plataforma**: 400 000+ campos de datos de 12 regiones; API BRAIN con Python;
  `SuperAlphas`; periodos de simulación largos.
- **Compensación por mérito** (pago trimestral):
  - Nivel Grandmaster: potencialmente **$8 000 o más** por trimestre.
  - Nivel Master: potencialmente **$2 000 o más** por trimestre.
- **Extras**: Quant Advisory Program (aprendizaje por cohortes), posible pasantía/empleo
  en WorldQuant, eventos exclusivos.
- **Camino**: Sign up → Learn → Submit Alphas → Onboard.
- **Competencia**: IQC 2026 (International Quant Championship) con premios.

## Encaje con el repo DevSoul Quant

- El motor de replay/backtest y la disciplina de validación (features causales, holdout,
  provenance, métricas out-of-sample) son transferibles directamente a construir y evaluar
  modelos/alphas antes de subirlos.
- El stack Python + TDD + pytest es el mismo que exigen ambas plataformas.
- No se reutiliza la infraestructura de ejecución FX (quedó cerrada), sino la
  **metodología** y el **código de validación**.

## Estado

`INVESTIGACIÓN_INICIAL` — hechos verificados contra fuentes oficiales. No se ha
abierto cuenta ni se ha hecho ninguna afirmación de rentabilidad. Siguiente paso
propuesto: un piloto mínimo (descargar datos, entrenar baseline, evaluar out-of-sample)
en una de las dos plataformas, reutilizando el protocolo de validación existente.
