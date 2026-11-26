# Política provisional de datos del proveedor

Estado: bloqueante
Fecha: 2026-09-29 (revalidación oficial 2026-11-25)

## Estado terminal del proveedor

Deriv queda en `EPHEMERAL_ONLY`: no se esperará autorización futura. La política
permanece bloqueante para toda persistencia de contenido o derivados Deriv; la
investigación continúa provider-independiente según ADR-006. Ningún payload Deriv
entra en persistencia.

## Regla vigente

Fuente principal:

https://deriv.com/terms-and-conditions/api-users

API Users Terms R26|03, actualizado 2026-11-16:

- 2.1: no almacenar contenido que derive/proceda del sitio o se obtenga mediante la API, incluido feed data;
- 2.2: se pueden almacenar API tokens y OAuth tokens;
- 2.3: contenido del sitio/API puede mantenerse como caché por máximo 24 horas desde la solicitud;
- 2.4: al terminar la relación debe eliminarse permanentemente, salvo obligación legal contraria.

Fuentes adicionales:

- https://deriv.com/terms-and-conditions/general-terms-of-use
- https://deriv.com/terms-and-conditions/trading-terms
- https://deriv.com/terms-and-conditions/business-partners-general-terms

General Terms 16.5–16.6 requieren permiso escrito para copiar o distribuir materiales. Trading Terms 6.2 identifica la redistribución del feed y el exceso de recursos como posible abuso.

## Consecuencia

De forma permanente para el alcance actual:

1. No persistir ticks, historial, catálogos, propuestas, payouts ni lifecycle Deriv más de 24 horas.
2. La caché temporal debe tener TTL verificable <24 h.
3. No crear backups, snapshots, DLQ, logs de payloads ni exportaciones que sobrevivan al TTL.
4. No construir corpus histórico Deriv para backtest o entrenamiento.
5. No asumir que CSV/Parquet o una transformación evita la restricción.
6. Features, etiquetas, modelos y métricas derivados solo pueden existir en memoria dentro de
   la caché de sesión; no conservarlos más allá del TTL ni reutilizarlos entre sesiones.
7. No mostrar al socio datos crudos, feeds reproducibles ni propuestas.
8. No usar marcas, logo o afirmaciones de asociación/aprobación sin permiso.
9. Mantener tokens y datos de cuenta fuera de Git/logs y con mínimo privilegio.
10. Mantener dinero real fuera del sistema.

## Caché efímera permitida provisionalmente

Si se implementa antes de recibir respuesta:

- TTL máximo: 23 horas para margen operativo;
- sin backups ni réplica duradera;
- expiración por registro y barrido periódico;
- borrado verificable;
- logs sin payloads/precios;
- métricas operativas sin reconstruir el feed;
- fail-closed si el mecanismo de expiración falla.

Esta caché sirve para integración, no para evidencia histórica suficiente.

## Matriz de aprendizaje adaptativo S3.8

La revalidación del 2026-11-25 también consideró API Terms 1.1 (desarrollar y probar una
aplicación), 4.1 (exclusión del contenido obtenido o derivado de la API) y General Terms
16.5–16.6 (permiso escrito para copia/distribución):

| Capacidad | Estado |
|---|---|
| entrenamiento incremental en memoria | `EPHEMERAL_ONLY` durante una sesión <24 h |
| evaluación prequential en memoria | `EPHEMERAL_ONLY` |
| features y etiquetas temporales | `EPHEMERAL_ONLY` |
| parámetros entrenados/checkpoints persistentes | `BLOCKED` |
| métricas derivadas persistentes o longitudinales | `BLOCKED` |
| visualización local no reconstructiva durante la sesión | `EPHEMERAL_ONLY` |
| publicación o presentación externa de resultados derivados | `BLOCKED` sin permiso escrito |

Entrenar en memoria no convierte los parámetros o métricas en artefactos propios persistibles.
La sesión debe zeroizar modelos, buffers, etiquetas pendientes y métricas al cerrar o fallar.

## Artefactos propios

Código, datos sintéticos generados por DevSoul y pruebas que no copien contenido Deriv pueden persistirse. La retención de features, métricas, modelos y backtests derivados de datos Deriv sigue pendiente de confirmación.

## Preguntas pendientes

Solicitar confirmación escrita sobre:

- raw data por más de 24 horas;
- features, labels, métricas, modelos y backtests;
- campos mínimos de auditoría;
- dashboard privado para socio;
- licencia para SaaS;
- Derived/Synthetic Indices;
- atribución, borrado y restricciones geográficas.

Borrador: `docs/legal/deriv-data-permission-request.md`.

## Acción aplicada

Los datos públicos capturados para comprobar compatibilidad fueron eliminados el 2026-09-29, antes de 24 horas. No se conservaron copias raw ni snapshots del sitio. El registro de fuentes mantiene únicamente URLs, versiones y cláusulas consultadas.