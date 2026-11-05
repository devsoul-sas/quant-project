# Bloqueo de almacenamiento de datos Deriv

Estado: P0 — bloquea el diseño original del MVP
Detectado: 2026-09-29 UTC

## Fuente oficial

API Users Terms, versión R26|03, actualizada 2026-10-16:

https://deriv.com/terms-and-conditions/api-users

Cláusulas relevantes:

- 2.1: prohíbe almacenar contenido que derive o proceda del sitio o que se obtenga mediante la API; menciona expresamente feed data.
- 2.2: permite almacenar identificadores/tokens API y tokens OAuth.
- 2.3: permite cachear contenido del sitio/API durante un máximo de 24 horas desde la solicitud.
- 2.4: exige eliminación permanente al terminar la relación, salvo obligación legal contraria.

Fuentes adicionales:

- General Terms 16.5–16.6: permiso previo escrito para copiar/distribuir materiales.
- Trading Terms 6.2: redistribuir el feed o sobreutilizar recursos puede considerarse abuso.

## Impacto

Sin autorización escrita, DevSoul no debe:

- construir un histórico persistente de ticks o propuestas;
- conservar raw JSON, CSV, Parquet, backups o logs de payloads más de 24 horas;
- asumir que features, etiquetas, métricas o modelos derivados pueden retenerse indefinidamente;
- mostrar a un socio feeds, ticks o propuestas reproducibles;
- diseñar el MVP alrededor de una base histórica propia de Deriv.

La transformación de JSON a Parquet no evita la restricción.

## Acción aplicada

Los artefactos públicos temporales capturados durante el Gate 0 fueron eliminados el mismo día, mucho antes del límite de 24 horas. No se ejecutaron operaciones ni se usaron credenciales.

Se conserva únicamente:

- documentación técnica de endpoints y schemas;
- el ZIP oficial de schemas descargado desde GitHub, sujeto a su licencia;
- una descripción de la prueba de compatibilidad, sin conservar feed/payloads;
- registro de las URLs y versiones contractuales consultadas, sin copia local de sus páginas.

## Decisiones posibles

### Opción A — Autorización escrita de Deriv

Solicitar permiso para:

- persistir ticks y propuestas más de 24 horas;
- derivar y retener features, labels, métricas, modelos y backtests;
- mostrar resultados agregados a un socio;
- operar un dashboard privado;
- conocer requisitos de atribución, retención y eliminación.

Es la opción que conserva el MVP original.

### Opción B — Fuente de datos con licencia compatible

Usar una fuente/broker que permita almacenamiento histórico y uso cuantitativo. Deriv podría permanecer solo como adaptador demo posterior, si los términos permiten usar señales derivadas de la fuente autorizada.

### Opción C — Laboratorio efímero de 24 horas

Trabajar únicamente con caché TTL ≤24 h, sin backups ni corpus histórico. Esta opción permite pruebas de integración, pero no es suficiente para evidencia estadística persistente ni backtesting reproducible a largo plazo.

## Gate

El Gate 0 queda bloqueado para collector persistente, datasets, backtesting histórico y dashboard de evidencia hasta resolver A o B. Solo se autoriza bootstrap técnico sin market data persistente y experimentos sintéticos generados por DevSoul.