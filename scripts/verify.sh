#!/usr/bin/env bash
set -euo pipefail

uv sync --locked
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy
uv run pytest
uv build
