# Evaluación de proveedor: Binance (market data pública e histórica)

- Fecha de corte solicitada: 2026-10-29
- Verificación técnica de las fuentes: 2026-10-30
- Resultado: **RECHAZADO PARA INVESTIGACIÓN COMERCIAL, USO PROPIETARIO EN PRODUCCIÓN Y SaaS BAJO LOS TÉRMINOS PÚBLICOS**
- Alcance: históricos de Binance Vision y market data pública por API, sin autenticación ni descarga de datos de mercado
- Regla: lo no autorizado explícitamente se considera bloqueante

Esta evaluación técnica de derechos no sustituye asesoría jurídica.

> **NOTA DE CORRECCIÓN (2026-11-24, S4):** el veredicto de rechazo de esta evaluación
> aplica al canal **Binance Vision** (descarga masiva `data.binance.vision`), y sigue
> siendo correcto para ese canal. No obstante, la vía que S4 necesita — operar capital
> propio por la **API de exchange** — está gobernada por los **Exchange ToU** (vigentes
> desde 2026-10-27) y los **API Keys Product Terms v2.0** (desde 2026-07-09), que esta
> evaluación no analizó por separado. La reevaluación en
> `docs/research/s4-data-provider-assessment.md` (con cláusulas verbatim y SHA-256) halló
> que esos instrumentos **sí** contemplan "constructing automated trading systems"
> (ToU Cl. 33.7) y licencia para "internal business use" (ToU Cl. 27). Veredicto para la
> vía API: **CONDICIONAL** (no aprobado pleno), pendiente de dos clarificaciones escritas.

## Conclusión ejecutiva

Binance Vision publicó términos específicos, versión 1.0, actualizados el 26 de agosto de
2026. La licencia es **CC BY-NC-SA 4.0**, excluye estrictamente toda utilización comercial y
exige un contrato empresarial escrito para habilitarla (cláusulas 3.1–3.4). Los términos
además incluyen expresamente charts, models y derivative analytical indicators (2.4),
prohíben señales compensadas y order generation comercial (4.2), explotar u hospedar datos
o feeds derivados (4.3), e integrar los datasets en productos financieros, newsletters de
pago o bots comerciales (4.4).

Por tanto, accesibilidad pública, descarga programática y documentación técnica de APIs **no
habilitan** investigación cuantitativa potencialmente comercial ni SaaS. Se requiere una
licencia empresarial escrita de Binance que cubra cada uso y artefacto previsto.

Para la market data pública REST/WebSocket fuera del conjunto definido por Binance Vision no
se encontró una licencia API/data separada que conceda almacenamiento, modelos, display o
redistribución comercial. La documentación técnica describe capacidades, no derechos. Ese
vacío también es **DESCONOCIDO / BLOQUEANTE**.

## Fuentes oficiales verificadas

1. **Binance Vision Dataset Terms**, v1.0, última actualización 2026-08-26:
   - Página: https://data.binance.vision/terms-of-use.html
   - PDF: https://data.binance.vision/Binance_Vision-Terms_of_Use.pdf
   - SHA-256 del PDF: `0ec62cd26207f8be17f424d83240f671280ec4b17f7ef9a0026e7b6e0258121f`
   - Tamaño: 144891 bytes
2. **Repositorio oficial Binance Public Data**, revisión observada
   `d571690eb66760763b0bd6e27e8cd35603c7e244` (2026-10-16):
   - Términos fijados: https://github.com/binance/binance-public-data/blob/d571690eb66760763b0bd6e27e8cd35603c7e244/TERMS_AND_CONDITIONS.md
   - README fijado: https://github.com/binance/binance-public-data/blob/d571690eb66760763b0bd6e27e8cd35603c7e244/README.md
   - SHA-256 de `TERMS_AND_CONDITIONS.md`: `99c4921dbe023cd68c1a447775707d621453cc78aec6ac0bfe2e6c06a5114ee0`
   - SHA-256 de `README.md`: `2e133d9945a9263a02781369078e72805eff074680f305cd5460016471c6caad`
3. **Binance Terms of Use**, fecha efectiva 2026-07-21:
   - Página enlazada por los Dataset Terms: https://www.binance.com/en/about-legal/terms
   - PDF oficial enlazado por la página de términos:
     https://bin.bnbstatic.com/static/cms/cg08ou2ak0tn7mcplvfg/file/bf4879710c904b991848972ec4818ba2cf9e4ce314c09adae84fa2750d3477f7.pdf
   - SHA-256: `bf4879710c904b991848972ec4818ba2cf9e4ce314c09adae84fa2750d3477f7`
   - Tamaño: 1362587 bytes
   - La página oficial estaba protegida por AWS WAF durante la verificación. El enlace al PDF
     se corroboró contra la captura de la página oficial del 2026-10-27, inmediatamente
     anterior al corte, y el PDF se recuperó directamente del CDN oficial de Binance.
4. **Documentación oficial de APIs**:
   - Introducción: https://developers.binance.com/en/docs/introduction
   - Términos del producto Spot: https://developers.binance.com/en/docs/products/spot/PROD-TERMS-OF-USE
   - La introducción dice que las APIs permiten acceder a market data real-time/historical,
     construir automatización e integrar datos en dashboards/analytics; no constituye una
     licencia de datos. Los términos Spot remiten a los Binance Terms of Use.
5. **Portal de históricos**: https://data.binance.vision/

Los PDF y documentos usados para hashes permanecieron solo en `/tmp`; no se descargó ningún
precio, libro, trade, kline ni otro payload de market data.

## Citas contractuales determinantes

### Alcance y datos derivados

Dataset Terms 2.1:

> “Binance publishes historical market data, order book metrics, trade flow logs, and related
> indicators (the ‘Datasets’) made available through data.binance.vision and associated
> endpoints.”

Dataset Terms 2.4:

> “Use of any data derived from, calculated with, or extracted from the Datasets (including
> charts, models, and derivative analytical indicators) is strictly governed by these Vision
> Dataset Terms.”

### Licencia y uso comercial

Dataset Terms 3.1:

> “Datasets are provided to you under the Creative Commons
> Attribution-NonCommercial-ShareAlike 4.0 International Public License (‘CC BY-NC-SA 4.0’).”

Dataset Terms 3.4:

> “Commercial licensing is strictly excluded under this agreement; any commercial utilization
> requires a separate, written enterprise data license agreement executed with Binance.”

Dataset Terms 4.1 limita los usos a investigación académica, educación abierta no monetizada,
backtesting algorítmico “for purely personal non-production research” y evaluación open source
no comercial.

Dataset Terms 4.2–4.4:

> “You shall not use the Datasets for live proprietary trading execution, automated commercial
> order generation, or signal distribution to third parties for direct or indirect compensation.”

> “You shall not license, sub-license, sell, rent, lease, host, or commercially exploit the
> Datasets or any derivative real-time or historical data feeds.”

> “You shall not integrate the Datasets into commercial financial products, hedge fund
> management tools, paid subscription newsletters, or commercial trading bot platforms.”

### Redistribución, atribución y marca

Dataset Terms 4.5:

> “any redistributed derivative work ... provides appropriate attribution to Binance Vision and
> remains licensed under the identical CC BY-NC-SA 4.0 terms.”

Dataset Terms 8.2–8.3 prohíbe implicar patrocinio/endorsement sin consentimiento y usar
“Binance” o “Binance Vision” para comercializar aplicaciones, señales o software al consumidor.

### Automatización

Dataset Terms 7.1–7.3 exige respetar rate limits, guías de scripts y protocolos; prohíbe
scripts o consultas continuas que eludan límites o perjudiquen el hosting, y permite banear IP,
revocar claves o limitar ancho de banda.

El README oficial muestra descarga programática por `curl`/`wget` y scripts auxiliares, pero
eso solo evidencia un método técnico permitido dentro de la licencia no comercial; no concede
uso comercial. No se encontró una cuota contractual numérica general aplicable a todo el
portal: **DESCONOCIDO / BLOQUEANTE para un colector de producción**.

### Cambios, suspensión y terminación

Dataset Terms 1.4 permite modificar los términos con o sin aviso, pero dice que cada cambio
aplica prospectivamente y no afecta los derechos sobre datasets ya descargados bajo los
términos vigentes al descargarlos. La cláusula 5.3 permite modificar, redactar o descontinuar
cualquier par, dataset o endpoint sin aviso.

General Terms 25.1 permite modificar/descontinuar servicios y suspender o terminar acceso con
efecto inmediato. General Terms 27 limita la licencia de Binance IP a la duración del acuerdo o
hasta suspensión/terminación, para “non-commercial personal or internal business use”. No se
encontró en los Dataset Terms una obligación expresa de borrar datasets ya obtenidos al terminar;
la retención de backups, logs, pesos de modelo y auditoría post-terminación tampoco se define.
Para un uso comercial, esto es **DESCONOCIDO / BLOQUEANTE** y debe resolverse en la licencia
empresarial.

### Entidad, jurisdicción y restricciones de producto/geografía

Dataset Terms 1.3 identifica a **NEST EXCHANGE LIMITED**, Recognised Investment Exchange
regulada por la FSRA de ADGM, Abu Dhabi, como entidad proveedora.

Dataset Terms 12 incorpora las reglas de disputas de los General Terms. General Terms 37 exige
arbitraje ICC individual, sede ADGM, en inglés; 38 dispone derecho exclusivo de ADGM; 39
renuncia a class actions.

General Terms 2.1(e)–(f) exige no ser Restricted Person ni estar ubicado/incorporado/residir,
ser ciudadano u operar donde el acceso sea ilegal o en la List of Prohibited Countries. 25.5
permite restricciones por país, cambios de disponibilidad y bloqueo al viajar; prohíbe evadir la
restricción mediante VPN. Los Product/Local Terms pueden suplementar el acuerdo y la oferta
varía por residencia, producto y entidad.

No se verificó que Colombia, la entidad jurídica concreta del proyecto ni cada familia
Spot/Futures/Options estén habilitadas para el uso comercial previsto. **DESCONOCIDO /
BLOQUEANTE** hasta validación por Binance y revisión jurídica.

## Matriz de derechos

| Criterio obligatorio | Vision histórico no comercial | Uso potencialmente comercial/SaaS | Estado operativo |
|---|---|---|---|
| Descarga/acceso | Expresamente contemplado; sujeto a términos | No concede derechos comerciales | **BLOQUEADO** |
| Almacenamiento histórico | Download/cache contemplados; sin TTL publicado | Toda utilización comercial requiere licencia empresarial | **BLOQUEADO** |
| Backups, logs y DLQ | No regulados con precisión | No autorizados explícitamente | **DESCONOCIDO / BLOQUEANTE** |
| Features, charts, métricas y modelos | Permitidos solo bajo alcance NC; 2.4 los somete a los términos | Comercial excluido; incluye explícitamente models/indicators | **BLOQUEADO** |
| Pesos/parámetros de modelo post-borrado | No especificado | No autorizado | **DESCONOCIDO / BLOQUEANTE** |
| Backtesting | Solo personal, no productivo (4.1) | Backtesting comercial/proprietary production no concedido | **BLOQUEADO** |
| Live trading / señales | 4.2 prohíbe ejecución propietaria live, generación comercial y señales compensadas | Prohibido bajo términos públicos | **BLOQUEADO** |
| Display interno comercial | No cubierto por el permiso NC | 3.4 exige licencia empresarial | **BLOQUEADO** |
| Display a clientes / dashboard SaaS | No cubierto | 4.3–4.4 lo bloquean | **BLOQUEADO** |
| Redistribución derivada NC | Atribución + idéntica CC BY-NC-SA (4.5) | Redistribución comercial bloqueada | **BLOQUEADO** |
| Redistribución/hosting raw NC | Tensión entre CC BY-NC-SA y la prohibición de “host” en 4.3; no se aclara | Comercial bloqueado | **DESCONOCIDO / BLOQUEANTE** |
| Automatización | Admitida solo conforme a límites/protocolos; sin elusión | No convierte el uso en comercialmente autorizado | **BLOQUEADO** |
| Terminación/borrado | Derechos de descargas previas preservados por 1.4; sin borrado expreso | Reglas de borrado/retención comercial no definidas | **DESCONOCIDO / BLOQUEANTE** |
| Entidad/jurisdicción/producto | NEL/FSRA/ADGM; sujeto a Local/Product Terms | País, entidad y productos concretos no confirmados | **DESCONOCIDO / BLOQUEANTE** |
| Marcas/atribución | Atribución requerida para derivados NC; sin sugerir asociación | No usar Binance/Vision para marketing comercial | **BLOQUEADO** |

## Decisión fail-closed

Binance **no puede adoptarse** como proveedor de market data histórico/público para la ruta
comercial, propietaria en producción o SaaS de DevSoul Quant bajo los términos públicos
vigentes al corte.

Continúan permitidos únicamente el desarrollo provider-independent y fixtures sintéticos
propios. Ni un adaptador persistente, ni backtests con data real de Binance, ni entrenamiento de
modelos, dashboards, exports o SaaS deben activarse hasta recibir un contrato empresarial
escrito y revisado jurídicamente.

## Requisitos mínimos para reconsiderar

La licencia/confirmación escrita de Binance debe identificar entidad, país y productos y cubrir:

1. API pública y Binance Vision, Spot/Futures/Options y endpoints asociados;
2. descarga automatizada, límites, WebSocket, throttling y continuidad;
3. almacenamiento persistente, TTL, réplicas, logs, colas, snapshots y backups;
4. features, etiquetas, agregados, métricas, backtests, modelos y pesos entrenados;
5. uso comercial interno, proprietary research/trading y presentación a socios;
6. dashboard/customer display, SaaS, exports y redistribución raw/derivada;
7. atribución, uso de marca y prohibiciones de asociación;
8. terminación, borrado, plazo, copias de backup y campos de auditoría retenibles;
9. terceros incorporados al dataset y sus licencias;
10. ley aplicable, entidad contratante, Colombia y restricciones de producto/usuario.
