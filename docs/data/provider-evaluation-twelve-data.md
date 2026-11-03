# Evaluación de proveedor: Twelve Data

- Fecha de consulta y verificación: 2026-10-30
- Terms of Use: “Last updated: January 1, 2026”
- Resultado: **CANDIDATO CONDICIONAL, BLOQUEADO PENDIENTE DE LICENCIA ESCRITA**
- Gate: `BLOCKED_PENDING_PERMISSION`
- Alcance: históricos para investigación con posible explotación comercial/SaaS
- Regla: lo no autorizado explícitamente se considera bloqueante

Esta evaluación técnica de derechos no sustituye asesoría jurídica. No se usaron
credenciales ni endpoints de market data.

## Fuentes oficiales verificadas

1. Terms of Use: https://twelvedata.com/terms
   - SHA-256 del HTML: `4683a79c66011b855c772561721ccf37926bc11e461133c1f8d54cb5d2237a57`
   - Tamaño: 176400 bytes.
2. Pricing (Markdown oficial): https://twelvedata.com/pricing.md
   - SHA-256: `7bb05e09eb5575f76cf5ed4a81a5a32780614c00d0fcd6ba53a39612ca8eca6f`
   - Tamaño: 9428 bytes.
3. Business pricing: https://twelvedata.com/pricing-business
4. Documentation: https://twelvedata.com/docs

Los archivos de revisión se mantuvieron solo en `/tmp`; no forman parte del repositorio.

## Evidencia determinante

Los términos permiten al cliente:

> “Access, receive, process, and store Data solely for Internal Use (or as otherwise
> permitted by your Subscription Tier or add-ons)”

También permiten crear `Derived Data` no reversible y establecen que el cliente conserva
sus derechos sobre derivados creados conforme al acuerdo. Sin embargo, prohíben:

> “Store or cache Data beyond permitted timeframes specified in the Documentation”

No encontramos un TTL público inequívoco que autorice conservación permanente de un corpus
histórico. Los planes Business son obligatorios incluso para uso interno por una empresa,
equipo, fondo u organización.

Al terminar, los términos indican tanto cese inmediato y borrado como:

> “All Data must be deleted within 30 days”

No aclaran suficientemente qué ocurre con modelos, pesos, Derived Data, backups y logs.

## Matriz de derechos

| Criterio | Evidencia | Estado |
|---|---|---|
| Uso interno empresarial | Permitido solo conforme a plan Business | **CONDICIONAL** |
| Histórico persistente | Storage interno permitido, pero limitado por timeframes no identificados | **BLOQUEADO** |
| Features/Derived Data | Permitidos si no permiten reconstruir el raw; sin prueba contractual de no reversibilidad | **CONDICIONAL / BLOQUEANTE** |
| Modelos/pesos/parámetros | No regulados expresamente como Derived Data | **DESCONOCIDO / BLOQUEANTE** |
| Display a usuarios | Venture puede cubrir display externo, sujeto a mercado/bolsa | **CONDICIONAL** |
| API/feed/exportación SaaS | Requiere Enterprise, add-on o acuerdo escrito | **BLOQUEADO SIN LICENCIA** |
| White-label | Enterprise+ / términos personalizados | **CONDICIONAL** |
| Automatización | Permitida dentro del plan y rate limits | **PERMITIDO CONDICIONALMENTE** |
| Datos de terceros/bolsas | Puede requerir acuerdos y fees adicionales | **BLOQUEANTE POR DATASET** |
| Terminación/borrado | Borrado máximo en 30 días; derivados/modelos/backups no claros | **BLOQUEANTE** |
| Jurisdicción | Singapur; arbitraje SIAC | **CONFIRMADO** |

## Pricing observado

Los precios no tienen historial/versionado que pruebe el valor exacto del 2026-10-29; estos
son los valores publicados durante la verificación del 2026-10-30:

| Plan | Precio mensual publicado | Derecho destacado |
|---|---:|---|
| Basic | USD 0 | evaluación, sin producción/display externo |
| Venture | USD 149 / 299 / 499 | display externo |
| Enterprise | USD 1.099 | distribución externa |
| Enterprise+ | personalizado | white-label/licencia personalizada |

Los fees de bolsas/add-ons son adicionales y no sustituyen la licencia del mercado concreto.

## Decisión

Twelve Data es el **mejor candidato contractual de la shortlist**, porque reconoce uso
Business y Derived Data, pero todavía no puede integrarse. Antes se requiere una orden o
acuerdo escrito que confirme:

1. retención permanente del histórico y backups;
2. datasets/mercados y licencias de bolsa incluidos;
3. transformación a formatos de investigación;
4. criterio de no reversibilidad para features/labels/métricas;
5. entrenamiento y conservación de modelos/pesos;
6. backtests, señales, reportes y presentación a socios;
7. display frente a API/feed/exportaciones/SaaS;
8. borrado de raw, derivados, modelos, logs y backups al terminar;
9. campos mínimos de auditoría que pueden conservarse.

No se enviará una consulta comercial sin autorización del usuario y su identidad contractual.
