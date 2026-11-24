# Evaluación de Darwinex Zero como venue de ejecución EURGBP

- Fecha de consulta: 2026-11-05
- Estado: **NO ES UN VENUE** — es una capa de track-record y capital inversor
- Veredicto: **NO DESBLOQUEA EL VENUE** (`NINGUNO APROBADO` permanece)

`UNKNOWN/BLOCKING` significa falta de evidencia oficial suficiente; no afirma que la
actividad esté prohibida.

## Conclusión principal

Darwinex Zero **no es un venue de ejecución**. Es una plataforma de capital virtual que
monitorea y evalúa la actividad de trading del usuario en una cuenta de un **broker
subyacente** y, si el track record es consistente, canaliza capital de inversores a cambio
de una comisión de éxito (~15%).

Por tanto, Darwinex Zero **no resuelve el gate g5** (venue primario). La ejecución y los
datos de mercado residen en el broker subyacente, cuya admisión de Colombia, cotizaciones
EURGBP, economía y derechos de retención siguen sin evaluar.

## Cadena de entidades

- La marca **Darwinex Zero** y el dominio `darwinexzero.com` son operados por
  **Tradeslide Technologies Ltd** (Reino Unido, n.º de empresa 14398381; los términos citan
  oficina en 20 Fitzroy Square, el pie de página 24 Fitzroy Square, Londres).
- El pie de página oficial declara: *"Tradeslide Technologies Ltd es un representante
  designado introductor de Tradeslide Trading Tech Ltd, autorizada y regulada por la
  Financial Conduct Authority (FRN 586466)."*
- Por tanto, el broker regulado real es **Tradeslide Trading Tech Ltd (FCA FRN 586466)**;
  Tradeslide Technologies Ltd actúa como representante introductor de aquella.

## Modelo operativo

La página de activos oficial declara:

- *"Darwinex Zero es una plataforma virtual, no una demo."*
- *"El capital es virtual, las condiciones de mercado no."*
- *"Hablamos de slippage, latencia y volatilidad."*
- *"Más de 1.500 activos"* (Forex & CFDs, Futuros, Acciones, ETFs, CFDs de cripto).

No se comprobó un catálogo oficial que liste específicamente `EURGBP` (el título genérico
"más de 1.500 activos" no es prueba del par exacto). La confirmación del par queda
`UNKNOWN/BLOCKING`.

## Cláusulas relevantes (términos oficiales, recuperados 2026-11-05)

Fuente: `https://www.darwinexzero.com/es/legal/terminos-uso` (Website Terms of Use,
texto en inglés).

- Cláusula 1.5.4 — la actividad se monitoriza contra una cuenta de un tercero:
  *"...your brokerage account details. We will have access to your financial information
  either through your trading account opened with any third party financial institution
  (\"Third Party Broker\") or when trades are transmitted directly from your trading
  terminal to your Broker."*
- Cláusula 1.5.5 — derecho irrevocable a monitorear y evaluar la actividad de trading y a
  mostrar cálculos "in a way that does not enable third users to replicate your trading
  strategy without your prior consent."
- Cláusula 1.2.2 — restricción de reproducción/almacenamiento del sitio:
  *"no part of this Website may be reproduced or stored in any other website or included in
  any public or private electronic retrieval system or service without TradeSlide's prior
  written permission."*
- Cláusula 3.5 — restricción de uso comercial/extracción:
  *"You may not use this Website for any commercial, profit-making or re-sale purposes,
  including the systematic extraction and/or re-utilisation of any part of a service or its
  content."*
- Cláusula 4.3 — *"All performance claims found on www.darwinexzero.com about trading
  systems or strategies must be regarded as hypothetical."*
- Pie de página — *"El contenido de este sitio web tiene únicamente fines educativos y no
  debe interpretarse como asesoramiento financiero y/o de inversión."*

## Derechos de datos (matriz resumida)

| Dimensión | Hallazgo |
|---|---|
| Acceso | Público (web) / registro para cuenta virtual |
| Storage del sitio | Restringido — cláusula 1.2.2 exige "prior written permission" |
| Uso comercial/extracción | Restringido — cláusula 3.5 prohíbe "systematic extraction" |
| Datos de mercado | No residen en Darwinex Zero; provienen del broker subyacente |
| Retención/derivados del broker | Sin evaluar (depende del broker subyacente) |
| Colombia / entidad aplicable | Sin evaluar |

Las cláusulas 1.2.2 y 3.5 gobiernan el contenido del **sitio web**, no los datos de
mercado del broker. Los derechos sobre cotizaciones, persistencia y derivados deben
resolverse contra los términos del broker subyacente (Tradeslide Trading Tech Ltd, FCA
FRN 586466, o un Third Party Broker), no contra Darwinex Zero.

## Impacto en la decisión

Darwinex Zero aporta un **modelo de monetización legítimo** (track record verificado →
capital inversor → comisión de éxito ~15%) pero **no desbloquea el venue**. El gate g5
permanece abierto: sigue faltando un broker spot/CFD único con admisión colombiana
verificada, `EURGBP` confirmado, economía ejecutable completa (spread/comisión/slippage/
financiación) y derechos de persistencia/derivados por escrito.

Ver [execution-venue-evaluation.md](execution-venue-evaluation.md) para la matriz de
venues spot/CFD (IG / IBKR / OANDA), que continúa en `NINGUNO APROBADO`.

El holdout BCE permanece sellado. No se abren cuentas, no se conservan payloads y no se
opera.
