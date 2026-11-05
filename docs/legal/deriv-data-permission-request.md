# Solicitud de confirmación a Deriv — borrador

Destinatario: `api-support@deriv.com`
Estado: **CERRADA / HISTÓRICA — NO ENVIAR SEGUIMIENTOS**
Referencia activa informada: issue `#141839`
Referencia anterior, posible duplicado: issue `#141833`
Registrada: `2026-09-29T22:18:01Z`
Última actualización: `2026-09-30T14:06:05Z`

Por decisión del proyecto del 2026-11-05, no se esperará autorización futura. Este
archivo conserva contexto histórico; Deriv queda `EPHEMERAL_ONLY` con TTL <24 h.

Tras recibir los detalles adicionales, Deriv confirmó que escaló la solicitud al equipo
competente e informó un plazo estimado de uno a tres días hábiles. No se enviarán solicitudes
duplicadas durante ese plazo. La escalación no es una aprobación ni modifica las
restricciones vigentes; se requiere todavía una respuesta escrita sobre el fondo.

Canal verificado: los enlaces **Contact us** y **Get in touch** del portal oficial
`https://developers.deriv.com/` apuntan a `mailto:api-support@deriv.com`.

Canal secundario para seguimiento: chat oficial en `https://deriv.com/contact-us`.
Usarlo para solicitar un número de ticket y escalamiento al equipo de API/licenciamiento;
el chat no sustituye la autorización escrita.

Asunto: Written clarification on API data retention and derived research artifacts

---

Hello Deriv API Support,

DevSoul is evaluating an internal, local research MVP using the current Deriv Options API. The system would initially use public market data and, later, one DevSoul-owned demo account only. It would not manage client funds, execute real-money trades, redistribute a live feed, or provide copy trading.

We reviewed the API Users Terms version R26|03, particularly clauses 2.1–2.4. Before continuing, we need written clarification on the following:

1. May we retain tick data and price proposal responses for more than 24 hours for internal quantitative research and reproducible backtesting?
2. May we retain artifacts derived from that data for more than 24 hours, including features, labels, aggregated metrics, strategy parameters, trained model parameters and backtest reports?
3. What minimum audit fields may be retained after 24 hours: timestamp, symbol, contract parameters, request/correlation ID, hashes, proposal economics, contract ID and aggregate P/L?
4. May a private dashboard show aggregated paper/demo results to a development partner who funds software R&D but does not provide trading capital?
5. Would that partner be considered a customer or third party under the API Terms?
6. What additional agreement or licence would be required for persistent research data, a private evidence dashboard or a future SaaS?
7. Are there additional restrictions for Derived/Synthetic Indices or storing price proposals?
8. What attribution, copyright notice, deletion and retention controls would be required?
9. Is using a separately licensed historical data source to generate signals, while using Deriv only for demo execution, permitted?
10. Which entity/product restrictions apply to a developer residing in Colombia?

Our intended controls include least-privilege credentials, demo-only execution, no real-money endpoint, no raw-feed redistribution, rate limiting, encrypted local access, append-only audit events and deletion according to the agreed retention period.

Please let us know whether written approval or a separate data/API agreement is available.

Regards,
DevSoul

---

## Antes de enviar

- completar nombre legal y contacto de DevSoul;
- confirmar residencia/entidad;
- no adjuntar datos ni tokens;
- guardar la respuesta y términos aplicables;
- solicitar que el permiso enumere explícitamente raw data, derivados, métricas, modelos y presentación al socio.

## Seguimiento recomendado

1. Enviar desde un correo corporativo o identificable de DevSoul.
2. Conservar fecha, asunto y copia exacta del mensaje fuera del repositorio público.
3. Si no hay respuesta tras cinco días hábiles, responder sobre el mismo hilo.
4. Si continúa sin respuesta, abrir chat oficial, indicar fecha/asunto y pedir número de ticket y escalamiento a API/licenciamiento.
5. Registrar en el repositorio solo una síntesis redactada; no versionar nombres personales, IDs de cuenta, tokens ni el correo completo de soporte.
6. Ausencia de respuesta, respuesta automática o respuesta ambigua no constituye autorización.