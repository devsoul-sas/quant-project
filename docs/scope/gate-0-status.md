# Gate 0 — Acta corregida

Fecha: 2026-09-29 UTC

## Resultado

Estado: **BLOQUEADO POR LICENCIA DE DATOS**.

La API y el lifecycle técnico fueron verificados, pero los API Users Terms actuales no permiten el histórico persistente que requieren los documentos originales. La API solo permite cachear contenido durante un máximo de 24 horas, salvo autorización adicional.

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

Deriv confirmó que la solicitud fue escalada al equipo competente y estimó una respuesta
en uno a tres días hábiles. No abrir solicitudes duplicadas durante ese plazo. Esperar la
respuesta sustantiva, conservarla fuera del repositorio público y documentar aquí solo su
interpretación operativa redactada. El bootstrap técnico puede avanzar, pero no el pipeline
persistente de mercado. La escalación y el plazo informado no constituyen autorización.