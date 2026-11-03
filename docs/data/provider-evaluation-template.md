# Plantilla de evaluación de proveedores de datos

Antes de adoptar cualquier fuente externa, revisar sus términos oficiales (no tutoriales ni
páginas de marketing) y completar este checklist. Cada criterio marcado como desconocido es
un bloqueante.

## Criterios obligatorios

| # | Criterio | Fuente oficial obligatoria |
|---|----------|----------------------------|
| 1 | Derechos explícitos de retención de datos históricos | términos/licencia vigentes |
| 2 | Derechos de retención de features, modelos y métricas derivadas | términos/licencia vigentes |
| 3 | Derechos de presentación comercial / a socios internos | términos/licencia vigentes |
| 4 | Restricciones de redistribución | términos/licencia vigentes |
| 5 | Acceso histórico reproducible y semántica de timestamps | documentación de API |
| 6 | Campos económicos disponibles apropiados al producto (bid/ask/payout/costos) | documentación de API |
| 7 | Límites de API/descarga y precio | pricing/términos |
| 8 | Compatibilidad de jurisdicción y producto | términos |

## Registro de evidencia

Por cada criterio se registra: URL fuente, fecha de consulta, versión del documento y hash
cuando esté permitido. No se infiere permiso por el simple hecho de que la API sea accesible.

## Regla de decisión

Se adopta un proveedor solo si **todos** los criterios obligatorios están explícitamente
cubiertos por escrito. En cualquier otro caso la decisión es `NO_PROVIDER_APPROVED` y la
investigación continúa con datos sintéticos propios.

## Revisión humana

Antes de redistribuir a socios o de ofrecer el producto como SaaS se requiere revisión
humana/jurídica independiente de esta plantilla.
