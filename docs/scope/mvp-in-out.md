# Alcance DevSoul Quant MVP v0.2

Estado: capítulo venue FX cerrado; laboratorio Deriv efímero activo (ADR-012)
Fecha de corte: 2026-11-23

> El alcance FX/CFD original queda cerrado. Ningún venue spot/CFD fue aprobado y la
> hipótesis EURGBP no sobrevive costos. La dirección activa reutiliza el núcleo de
> backtesting hacia cuant crowdsourced (Numerai / WorldQuant BRAIN) y producto
> educativo/metodológico en español. Ver ADR-011.

## Propósito

Construir un laboratorio local que pueda producir evidencia reproducible sobre estrategias contractuales, sin violar licencias de datos y sin ruta hacia dinero real.

Una conclusión negativa es un resultado válido.

## Cambio crítico respecto a v0.1

Los API Users Terms de Deriv, cláusulas 2.1–2.4, prohíben almacenar contenido del API y solo permiten caché hasta 24 horas. Por decisión del proyecto, Deriv queda `EPHEMERAL_ONLY` con TTL estricto <24 h; el histórico, Parquet y backtest persistente requieren una fuente licenciada alternativa.

## Vertical slice técnico provisional

Mientras se resuelve la licencia:

- arquitectura local-first;
- motor contractual genérico;
- fixtures y series sintéticas creadas por DevSoul;
- semántica Rise/Fall (`CALL`/`PUT`) como primer caso de contrato;
- horizonte de fixture: 5 ticks;
- paper broker sintético;
- guardas demo-only;
- adaptador Deriv público limitado a caché efímera ≤23 h, si se implementa;
- ningún símbolo, moneda o stake queda congelado hasta consultar dinámicamente `contracts_for` y una cuenta demo autorizada.

No hay afirmación de rentabilidad ni selección definitiva de mercado.

## Laboratorio operativo efímero

Deriv se usa únicamente durante una sesión con TTL estricto menor de 24 horas. Cada
sesión comienza sin estado y ninguna sesión aprende de una sesión anterior. Ticks,
propuestas, features, decisiones y resultados permanecen en memoria y se eliminan al
cerrar. No se enviarán nuevas solicitudes de permiso ni se encadenarán sesiones para
reconstruir historia.

Las hipótesis activas son Even/Odd y Multipliers, separadas por protocolo. Solo pueden
producir `NO_EDGE`, `INSUFFICIENT_EVIDENCE` o `PAPER_ELIGIBLE` dentro de la sesión.
El dinero real permanece excluido.

## Incluido ahora

1. Repositorio, tooling y arquitectura modular.
2. Dominio `ENTER_CONTRACT / NO_TRADE / EXIT_CONTRACT`.
3. Reloj inyectado y replay determinista con datos propios/sintéticos.
4. Ledger append-only y tamper-evident.
5. Pruebas de rechazo de `REAL` y `/ws/real`.
6. Interfaces para fuentes de datos con metadatos de licencia/retención.
7. Caché efímera con TTL ≤23 h, sin backup, si es necesaria para integración.
8. Features causales y baselines sobre fixtures sintéticas.
9. Protocolo científico y reportes sin contenido Deriv retenido.
10. Evaluación de un proveedor/venue alternativo con licencia compatible.

## Incluido solo después de desbloqueo de licencia

- histórico persistente de mercado;
- PostgreSQL/Parquet con datos reales;
- backtest histórico reproducible;
- propuestas observadas persistentes;
- entrenamiento y retención de modelos derivados;
- paper/demo orientado a demostrar edge;
- dashboard privado para socio.

## Excluido

- dinero real y endpoints/cuentas reales;
- `DerivRealBroker` funcional o skeleton ejecutable;
- fondos del socio o terceros;
- Martingale como estrategia/sizing por defecto;
- copy trading, markup, billing o onboarding SaaS;
- promesas de rentabilidad;
- asesoría financiera individual;
- redistribución de feed o datos de Deriv;
- backups de la caché Deriv;
- cualquier conservación mayor al plazo autorizado.

## Modos permitidos

Antes del desbloqueo:

```text
SYNTHETIC_BACKTEST
SYNTHETIC_PAPER
EPHEMERAL_PUBLIC_INTEGRATION
```

Después de autorización expresa:

```text
QUOTE_REPLAY_BACKTEST
PAPER
DERIV_DEMO
```

`REAL` no es un modo válido. Una configuración, cuenta o URL no demostrada como demo debe provocar fallo de arranque.

## Definición de terminado

El MVP científico original solo termina si existe:

- licencia/autorización compatible o fuente alternativa;
- dataset persistente legalmente utilizable;
- economía contractual observada y trazable;
- backtest sin leakage;
- paper/demo reconciliado;
- ledger íntegro;
- evidencia etiquetada por origen y limitaciones;
- conclusión honesta sobre edge.

Sin licencia, el entregable se limita a un núcleo técnico validado con datos sintéticos y una decisión documentada de no avanzar con datos Deriv.