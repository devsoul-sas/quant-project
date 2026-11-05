# ADR-006 — Pivot a investigación provider-independiente

- Estado: aceptada
- Fecha: 2026-10-29

## Contexto

La solicitud histórica no produjo autorización. Por decisión del proyecto del
2026-11-05, Deriv queda `EPHEMERAL_ONLY`; no se esperará autorización futura y no
está en el camino crítico.

## Decisión

Pivotar la investigación a provider-independiente:

- mantener Deriv detrás de un gate de cumplimiento bloqueado;
- construir snapshots de dataset sintéticos deterministas, features temporales causales,
  evaluación walk-forward y reportes con evidencia graduada sobre puertos neutrales;
- tratar la selección de proveedor como un carril de due diligence separado: ningún dataset
  externo entra en persistencia hasta que su manifest de licencia pase validación.

## Alternativas consideradas

1. Esperar a Deriv sin avanzar: retrasa ingeniería por una variable fuera de control.
2. Asumir o inferir permiso por accesibilidad del API: viola los términos y expone al
   proyecto a riesgo contractual.
3. Integración Deriv solo efímera (caché <24 h): sirve para integración, no para evidencia
   histórica suficiente.
4. Pivot provider-independiente con fuente licenciada posterior: conserva el núcleo,
   produce evidencia reproducible y desacopla el avance de la licencia. **Seleccionada.**

## Consecuencias

El Gate 3 entrega un pipeline de investigación reproducible, demostrable a socios, que no
depende de Deriv ni afirma rentabilidad. La validación económica real comienza solo tras
aprobar una fuente con derechos explícitos compatibles. El dinero real permanece excluido
por construcción.
