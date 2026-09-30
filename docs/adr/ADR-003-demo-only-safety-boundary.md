# ADR-003 — Frontera estructural demo-only

- Estado: aceptada para MVP
- Fecha: 2026-09-29

## Contexto

Dinero real está fuera del MVP. Un flag desactivado o un skeleton de broker real amplía innecesariamente la superficie de error.

## Decisión

Los únicos modos ejecutables son:

```text
BACKTEST
PAPER
DERIV_DEMO
```

No se implementará `DerivRealBroker`, no se aceptarán variables `REAL_*` y no se configurará el endpoint WebSocket real.

## Controles obligatorios

1. Allowlist de modos; cualquier valor desconocido falla al arrancar.
2. El adaptador demo usa únicamente la URL devuelta por el endpoint OTP para una cuenta identificada como demo.
3. Nunca se construye manualmente una URL autenticada a partir de una plantilla.
4. PAT/OAuth, App ID, account ID y OTP no se registran ni persisten en artefactos.
5. Credenciales con privilegio mínimo; para operar se requiere scope de trading y cuenta demo.
6. `kill_switch` comienza bloqueando nuevas entradas.
7. Una prueba automática demuestra que una cuenta o endpoint no-demo hace fallar el arranque.
8. Timeout de `buy` activa reconciliación; nunca reenvío ciego.
9. Toda operación e2e demo requiere habilitación opt-in explícita.

## Consecuencias

Una futura prueba con capital real será otro proyecto: nueva revisión jurídica, threat model, protocolo, credenciales, ADR y autorización humana explícita. No será un cambio de configuración de este MVP.