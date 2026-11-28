#!/usr/bin/env bash
set -uo pipefail

if (($# == 0)); then
  printf 'usage: %s COMMAND [ARG ...]\n' "$0" >&2
  exit 64
fi

set +e
"$@"
status=$?
set -e
printf 'AUTONOMOUS_EXIT=%d\n' "$status" >&2
exit "$status"
