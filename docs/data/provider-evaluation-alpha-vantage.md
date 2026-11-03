# Evaluación de proveedor: Alpha Vantage

- Fecha de consulta y verificación: 2026-10-30
- Resultado: **RECHAZADO BAJO LOS TÉRMINOS ESTÁNDAR**
- Gate: `BLOCKED_PENDING_PERMISSION`
- Alcance: históricos y API para investigación con posible explotación comercial/SaaS
- Regla: lo no autorizado explícitamente se considera bloqueante

Esta evaluación técnica de derechos no sustituye asesoría jurídica. No se hicieron llamadas
autenticadas ni se descargaron datos de mercado.

## Fuentes oficiales verificadas

1. Terms of Service: https://www.alphavantage.co/terms_of_service/
   - PDF oficial, sin versión ni fecha efectiva visible.
   - SHA-256: `88ed3d22fe0f3624e76e53a210db3498b4a90712ab0d934356cc84b19ed1468a`
   - Tamaño: 156583 bytes.
2. API documentation: https://www.alphavantage.co/documentation/
3. Support/rate limits: https://www.alphavantage.co/support/
4. Premium pricing: https://www.alphavantage.co/premium/
5. Market data policy: https://www.alphavantage.co/realtime_data_policy/

El PDF se mantuvo solo en `/tmp` para verificar texto/hash; no forma parte del repositorio.

## Citas determinantes

Los términos conceden uso:

> “for personal, non-commercial use, unless you and Alpha Vantage have agreed otherwise in
> writing”

El análisis/investigación permitido bajo esa licencia debe ser:

> “private and individual in nature”

Se considera comercial si se usa en nombre de una corporación/asociación o si terceros
acceden directa o indirectamente a la información. La licencia es:

> “non-exclusive, non-sublicensable, non-transferable, non-assignable, revocable”

Para uso comercial, la fuente oficial exige contactar a Alpha Vantage. Una suscripción
Premium pública no equivale por sí sola a una licencia comercial.

## Matriz de derechos

| Criterio | Evidencia | Estado |
|---|---|---|
| Investigación individual privada | Permitida bajo licencia estándar no comercial | **LIMITADO** |
| Uso corporativo/interno | Clasificado como comercial | **BLOQUEADO sin acuerdo escrito** |
| Histórico persistente | La API entrega históricos, pero no concede expresamente retención, backups o data lake | **DESCONOCIDO / BLOQUEANTE** |
| Features, backtests y agregados | El usuario conserva su contenido, pero no se aclaran artefactos derivados de market data | **DESCONOCIDO / BLOQUEANTE** |
| Modelos/pesos/parámetros | No están regulados expresamente | **DESCONOCIDO / BLOQUEANTE** |
| Dashboard, informes o SaaS | Acceso directo o indirecto por terceros se considera comercial | **BLOQUEADO** |
| Redistribución raw | Licencia no sublicenciable/no transferible; sin concesión downstream | **BLOQUEADO** |
| Redistribución derivada | No distingue bruto, transformado, señales o exportaciones | **DESCONOCIDO / BLOQUEANTE** |
| Automatización/API | API contemplada dentro del plan; no autoriza descarga masiva comercial persistente | **BLOQUEADO PARA ESTE USO** |
| Terminación | Desactiva acceso; no define borrado/retención de datos, backups o modelos | **DESCONOCIDO / BLOQUEANTE** |
| Precio comercial | No publicado; requiere contacto comercial | **DESCONOCIDO / BLOQUEANTE** |
| Ley aplicable | Massachusetts | **CONFIRMADO** |

La documentación confirma capacidad técnica de 25+ años de históricos, pero capacidad no
equivale a licencia de retención. El nivel gratuito publica 25 solicitudes/día; los planes
Premium públicos se presentan como uso personal. Datasets de terceros (por ejemplo FRED)
pueden añadir términos propios.

## Decisión

Alpha Vantage **no se integra** bajo sus términos estándar. Se requeriría un acuerdo comercial
escrito que cubra persistencia, backups, históricos por tipo, features/backtests, modelos,
uso interno, display a terceros, SaaS, redistribución, terminación/borrado y datasets de
terceros.
