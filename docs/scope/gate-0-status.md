# Gate 0 — Acta corregida

Fecha: 2026-09-29 UTC

## Resultado

Estado: **BLOQUEADO POR LICENCIA DE DATOS**.

La API y el lifecycle técnico fueron verificados, pero los API Users Terms actuales no permiten el histórico persistente que requieren los documentos originales. La API solo permite cachear contenido durante un máximo de 24 horas, salvo autorización adicional.

## Estado de la revisión del proveedor

Actualizado: 2026-10-29.

Estado: **PENDING_PROVIDER_REVIEW**.

Deriv notificó en reiteradas ocasiones (la más reciente el 2026-10-29) que la solicitud
sigue en revisión por el equipo competente y que el chat de soporte queda cerrado mientras
tanto. El cierre del chat no tiene efecto de licencia y la notificación de "revisión en
curso" no constituye autorización de retención, derivados, presentación ni redistribución.

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
- diseñar caché TTL ≤24 h sin backups;
- preparar solicitud formal a Deriv.

## Bloqueado

- collector histórico persistente;
- PostgreSQL/Parquet con ticks o propuestas Deriv por más de 24 h;
- backup de feed/payloads;
- backtesting histórico con corpus Deriv local;
- entrenamiento persistente sobre datos Deriv sin aclarar derivados;
- dashboard para socio con datos/resultados no autorizados;
- paper/demo orientado a demostrar edge;
- dinero real.

## Condición de desbloqueo

Una de estas:

1. autorización escrita de Deriv que cubra retención, derivados y presentación privada; o
2. fuente de datos alternativa con licencia compatible y protocolo ajustado.

## Próximo paso

Deriv notificó en reiteradas ocasiones (más reciente: 2026-10-29) que la revisión sigue en
curso y que el chat queda cerrado mientras tanto. No abrir solicitudes duplicadas. El estado
es `PENDING_PROVIDER_REVIEW`: no constituye autorización y no bloquea el avance de
ingeniería. El pipeline de investigación avanza provider-independiente con datos sintéticos
propios (ADR-006); el pipeline persistente de mercado continúa bloqueado hasta autorización
escrita o adopción de una fuente con licencia compatible.