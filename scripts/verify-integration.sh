#!/usr/bin/env bash
set -euo pipefail

# Integration gate: requires a running PostgreSQL with an isolated schema and a
# restricted application role. These URLs are local-only and never committed.
# Create the roles/schema with:
#   docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
#   CREATE ROLE devsoul_quant_test_owner LOGIN PASSWORD 'local-test-owner-only';
#   CREATE ROLE devsoul_quant_test_app LOGIN PASSWORD 'local-test-app-only';
#   GRANT CONNECT ON DATABASE <db> TO devsoul_quant_test_owner, devsoul_quant_test_app;
#   CREATE SCHEMA quant_test AUTHORIZATION devsoul_quant_test_owner;
#   GRANT USAGE ON SCHEMA quant_test TO devsoul_quant_test_app;
#   SQL

: "${TEST_DATABASE_OWNER_URL:?set TEST_DATABASE_OWNER_URL}"
: "${TEST_DATABASE_URL:?set TEST_DATABASE_URL}"

SCHEMA="${DEVSOUL_QUANT_DATABASE_SCHEMA:-quant_test}"
APP_ROLE="${DEVSOUL_QUANT_TEST_APP_ROLE:-devsoul_quant_test_app}"

uv run alembic \
  -x url="$TEST_DATABASE_OWNER_URL" \
  -x schema="$SCHEMA" \
  -x app_role="$APP_ROLE" \
  downgrade base >/dev/null

uv run alembic \
  -x url="$TEST_DATABASE_OWNER_URL" \
  -x schema="$SCHEMA" \
  -x app_role="$APP_ROLE" \
  upgrade head

# The unit gate omits the persistence adapter (it needs a live PostgreSQL), so
# integration measures it separately with a dedicated coverage config.
uv run coverage run \
  --rcfile=scripts/coverage-integration.rc \
  --source=devsoul_quant.adapters.persistence \
  -m pytest -m integration -q -o addopts=
uv run coverage report -m
