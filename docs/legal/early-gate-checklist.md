# Gate jurídico y contractual temprano

Estado: bloqueante
Fecha: 2026-09-29

Este checklist no sustituye asesoría jurídica.

## P0 — Licencia de datos

Fuente: https://deriv.com/terms-and-conditions/api-users

- [x] Revisar API Users Terms 2.1–2.4.
- [x] Confirmar que el límite publicado de caché es 24 horas.
- [x] Eliminar payloads/market data capturados durante la comprobación.
- [x] Suspender histórico persistente y backups de datos Deriv.
- [ ] Obtener respuesta escrita sobre retención >24 h.
- [ ] Obtener respuesta escrita sobre features, labels, métricas, modelos y backtests derivados.
- [ ] Obtener respuesta escrita sobre dashboard privado y presentación al socio.
- [ ] Confirmar campos mínimos de auditoría retenibles.
- [ ] Confirmar reglas específicas de Derived/Synthetic Indices.
- [ ] Definir evidencia de borrado y plazo aplicable.

Si Deriv no autoriza, seleccionar una fuente de datos alternativa con licencia compatible y revisar si sus señales pueden usarse para demo en Deriv.

## Aporte del socio

- [ ] Definir si el aporte es inversión, préstamo, servicios o participación societaria.
- [ ] Definir monto, desembolsos, hitos y condiciones de terminación.
- [ ] Confirmar que no financia trading ni se mezcla con saldo demo/real.
- [ ] Definir pérdidas máximas del proyecto de software.
- [ ] Definir acceso del socio a repositorio, informes y dashboard.

## Propiedad intelectual

- [ ] Titularidad del código preexistente.
- [ ] Titularidad del código nuevo.
- [ ] Titularidad de datos sintéticos propios.
- [ ] Tratamiento de resultados negativos.
- [ ] Licencia de uso del socio.
- [ ] Restricciones de marca Deriv.
- [ ] Revisar API Terms 3 sobre derivados/modificaciones de la API.

No asumir titularidad libre de features/modelos derivados de datos Deriv hasta tener respuesta escrita.

## Producto y regulación

- [ ] Definir que el MVP es I+D interno y demo-only.
- [ ] Confirmar residencia de desarrolladores/usuarios y entidad Deriv aplicable.
- [ ] Revisar si señales, ranking o dashboard pueden constituir asesoría/promoción/copy trading.
- [ ] Prohibir promesas de rentabilidad.
- [ ] Etiquetar backtest, paper y demo inequívocamente.
- [ ] Mantener dinero real fuera del alcance.

## Datos personales y seguridad

- [ ] Inventario de PAT/OAuth, App ID, account ID, OTP y balance.
- [ ] Secretos fuera de Git y logs.
- [ ] Mínimo privilegio.
- [ ] Retención y borrado de datos personales.
- [ ] Proceso de revocación/rotación.
- [ ] Respuesta a incidentes.

## Términos y jurisdicción

- [x] Registrar URLs, versiones y fechas en `source-register.json`.
- [ ] Guardar la respuesta escrita de Deriv y su alcance exacto.
- [ ] Identificar entidad contractual aplicable a Colombia.
- [ ] Revisar jurisdicción/ley aplicable con asesor.
- [ ] Revisión antes de SaaS, terceros, dinero real o distribución pública.

## Gate de aprobación

Para desbloquear market data persistente debe existir evidencia escrita que cubra como mínimo:

1. fuente y campos autorizados;
2. retención de raw data;
3. retención de derivados;
4. uso en backtesting/entrenamiento;
5. presentación al socio;
6. atribución y marca;
7. borrado y terminación;
8. países/entidad/productos.

Hasta entonces solo se permite bootstrap técnico, fixtures sintéticas propias y, si hace falta, caché efímera con TTL operativo ≤23 horas y sin backup.