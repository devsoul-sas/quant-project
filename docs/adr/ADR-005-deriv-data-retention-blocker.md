# ADR-005 — Pausa del histórico persistente por API Terms

- Estado: aceptada y bloqueante
- Fecha: 2026-09-29

## Contexto

La especificación original exige histórico propio, Parquet, experimentos reproducibles y evidencia para un socio. Los API Users Terms vigentes de Deriv, cláusulas 2.1–2.4, prohíben almacenar contenido del API y solo permiten caché hasta 24 horas.

Reverificado el 2026-11-05: API Users Terms R26|03, actualizado el
2026-10-16. Las cláusulas 2.1–2.4 mantienen la restricción; no existe excepción
para propuestas, resultados demo o artefactos derivados. General Terms R26|03,
2026-10-09, ubica las restricciones de copia/distribución en 16.5–16.6.

## Decisión

Hasta obtener autorización escrita o cambiar de fuente:

- no persistir market data/payloads Deriv más de 24 horas;
- no crear backups de esa caché;
- no construir datasets históricos Deriv;
- no afirmar que transformar datos crea un artefacto libre de la restricción;
- no conservar proposal/contract IDs, economía, settlement, métricas o estado
  longitudinal que enlace un contrato multidiario;
- usar datos sintéticos propios para construir y probar el núcleo;
- mantener el adaptador de market data detrás de un puerto;
- tratar source licensing como requisito funcional y de seguridad.

## Alternativas

1. Permiso escrito de Deriv: conserva el diseño original.
2. Fuente licenciada alternativa: conserva investigación histórica y desacopla ejecución.
3. Caché efímera ≤24 h: solo sirve para integración/operación, no para evidencia histórica suficiente.

## Consecuencias

El Gate 0 no puede aprobar el collector persistente. El Bloque 1 puede crear infraestructura y guardas, pero la migración de ticks debe esperar. La propuesta al socio debe corregirse antes de afirmar que DevSoul construirá un histórico propio de Deriv.

## Revisión

Reemplazar esta decisión únicamente con el texto de autorización/licencia aplicable, alcance, fecha, entidad y obligaciones de retención/eliminación.