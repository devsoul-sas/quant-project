# DevSoul Quant

Núcleo cuantitativo local-first, reproducible y demo-only.

## Estado

El desarrollo está permitido con datos sintéticos propios. El almacenamiento persistente de market data Deriv está bloqueado por API Users Terms 2.1–2.4 hasta obtener autorización escrita o adoptar una fuente con licencia compatible.

No existe modo de dinero real.

Los dos documentos fuente originales de la raíz están superados y retirados de circulación; no se versionan ni deben enviarse a socios. Véase `docs/scope/legacy-source-status.md`.

## Requisitos

- Python 3.13, gestionado por `uv`
- `uv` 0.12.21+ para instalar exactamente Python 3.13.13
- Docker con Compose, solo para infraestructura local

## Preparación

```bash
uv sync --locked
```

## Verificación

```bash
./scripts/verify.sh
```

El gate ejecuta formato, lint, tipos, tests con cobertura y build del paquete.

La cobertura mínima del 95 % se calcula sobre **toda** la suite. Para ejecutar un archivo
de pruebas de forma focalizada sin que el resto del código cuente como no cubierto, use:

```bash
uv run pytest tests/domain/test_execution_mode.py -v --no-cov
uv run pytest tests/adapters/deriv/test_demo_url.py -v --no-cov
uv run pytest tests/domain/test_contracts.py -v --no-cov
uv run pytest tests/domain/test_replay.py -v --no-cov
uv run pytest tests/domain/test_ledger.py -v --no-cov
uv run pytest tests/application/test_demo.py -v --no-cov
```

Que una ejecución focalizada sin `--no-cov` termine con `Coverage failure` no significa
que sus tests hayan fallado; significa que ese subconjunto no cubre por sí solo el 95 %
de todo el paquete. El gate autoritativo continúa siendo `./scripts/verify.sh`.

## PostgreSQL local

El servicio local usa `127.0.0.1:5434` para no interferir con otras bases instaladas.

```bash
cp .env.example .env
docker compose up -d --wait postgres
docker compose ps
docker compose down
```

No almacenar ticks, propuestas ni payloads Deriv en esta base. Por ahora PostgreSQL está reservado para estado propio, fixtures sintéticas y futuros datos con licencia compatible.

## CLI

Ejecute el vertical slice sintético reproducible con:

```bash
uv run devsoul-quant demo --seed 42
```

El comando conecta generador propio de ticks, estrategia baseline, riesgo, paper broker,
replay y ledger hash-chained. Devuelve JSON con acción, decisión de riesgo, resultado
direccional, procedencia económica, hashes de cada evento y hash final. `economy=UNAVAILABLE` y
`profitability_claim=false` son deliberados: esta demo valida comportamiento técnico, no
rentabilidad ni P/L. La CLI no ofrece modo real ni acepta credenciales.

## Documentación

- `docs/README.md`
- `docs/scope/gate-0-status.md`
- `docs/deriv/api-storage-blocker.md`
- `docs/adr/ADR-005-deriv-data-retention-blocker.md`

## Seguridad

- modos reales y URLs `/ws/real` deben fallar cerrados;
- secretos y `.env` no se versionan;
- no hay commits ni despliegues automáticos desde este scaffold;
- cambios a dinero real requieren un proyecto y autorización separados.