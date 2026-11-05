# Gate 0 — Acta corregida

Fecha: 2026-09-29 UTC

## Resultado

Estado: **BLOQUEADO POR LICENCIA DE DATOS**.

La API y el lifecycle técnico fueron verificados, pero los API Users Terms actuales no permiten el histórico persistente que requieren los documentos originales. La API solo permite cachear contenido durante un máximo de 24 horas, salvo autorización adicional.

## Decisión terminal sobre Deriv

Actualizado: 2026-11-05.

Estado: **EPHEMERAL_ONLY**.

Por decisión de producto, no se esperará autorización futura. Deriv se limita a
conectividad y una sesión demo en memoria con TTL estricto menor de 24 horas. No
puede aportar corpus histórico, métricas retenidas ni evidencia económica longitudinal.

Deriv ya no está en el camino crítico: la investigación continúa provider-independiente con
datos sintéticos propios y la ruta alternativa de fuente con licencia compatible permanece
abierta (véase ADR-006). El estado de revisión no bloquea el avance de ingeniería.

## Decisiones técnicas válidas

- arquitectura local-first y monolito modular;
- núcleo replay-first;
- modos permitidos: backtest, paper y Deriv demo;
- dinero real ausente por construcción;
- dominio `ENTER_CONTRACT / NO_TRADE / EXIT_CONTRACT`;
- schemas oficiales fijados por release/hash;
- OTP nuevo por conexión demo y rechazo estructural de `/ws/real`;
- resultados negativos y downtime como evidencia.

## Hallazgo bloqueante

Fuente: https://deriv.com/terms-and-conditions/api-users

- API Terms 2.1 prohíbe almacenar contenido del API, incluido feed data.
- API Terms 2.3 permite caché por máximo 24 horas.
- No está claro si features, métricas, modelos o resultados agregados pueden conservarse más tiempo.

Los datos públicos capturados temporalmente durante la comprobación fueron eliminados el mismo día. No se conservaron payloads, inventarios, ticks ni propuestas.

## Permitido mientras se resuelve

- inicializar repositorio y tooling;
- desarrollar dominio, reloj, ledger y guardas demo-only;
- usar fixtures sintéticas creadas por DevSoul;
- probar schema parsing con ejemplos oficiales sujetos a su licencia;
- usar caché en memoria con TTL <24 h, sin backups ni exportación.

## Bloqueado

- collector histórico persistente;
- PostgreSQL/Parquet con ticks o propuestas Deriv por más de 24 h;
- backup de feed/payloads;
- backtesting histórico con corpus Deriv local;
- entrenamiento persistente sobre datos Deriv sin aclarar derivados;
- dashboard para socio con datos/resultados no autorizados;
- paper/demo orientado a demostrar edge;
- dinero real.

## Condición de desbloqueo científico

Una fuente de datos alternativa con licencia compatible y un venue alternativo con
economía observada y protocolo ajustado. Deriv no es una condición de desbloqueo.

## Próximo paso

Mantener Deriv en `EPHEMERAL_ONLY`, sin nuevas solicitudes de permiso. El pipeline de
investigación avanza con BCE/H.10 y datos propios; la economía ejecutable requiere un
venue alternativo con licencia compatible. Deriv no está en el camino crítico.