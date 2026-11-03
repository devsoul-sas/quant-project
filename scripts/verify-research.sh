#!/usr/bin/env bash
set -euo pipefail

# Gate 3 research verification: runs the full synthetic pipeline twice and
# confirms byte-for-byte reproducibility, then checks report invariants.

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cat > "$WORK/spec.json" <<'EOF'
{
  "seed": 42,
  "duration": 3,
  "dataset": {
    "generator_version": "synthetic-random-walk-v1",
    "start_epoch": 1700000000,
    "interval": 1,
    "row_count": 60,
    "schema_version": "1"
  },
  "features": {
    "name": "momentum-baseline",
    "version": "1",
    "lag_windows": [1, 3],
    "rolling_window": 3
  },
  "split": {
    "lookback_ticks": 3,
    "purge_ticks": 3,
    "embargo_ticks": 2,
    "test_ticks": 10,
    "fold_count": 3,
    "holdout_ticks": 5
  }
}
EOF

echo "==> research pipeline run 1"
uv run devsoul-quant research synthetic \
  --spec "$WORK/spec.json" --output "$WORK/run1"

echo "==> research pipeline run 2"
uv run devsoul-quant research synthetic \
  --spec "$WORK/spec.json" --output "$WORK/run2"

echo "==> byte-for-byte comparison"
diff -r "$WORK/run1" "$WORK/run2"

echo "==> report invariants"
uv run python - "$WORK/run1/run-report.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["states"]["engineering_readiness"]["status"] == "READY"
assert report["states"]["scientific_evidence"]["status"] == "NON_ECONOMIC"
assert report["states"]["provider_license_blockers"]["status"] == "DERIV_PENDING"
assert report["states"]["real_money_exclusion"]["status"] == "EXCLUDED"
assert report["evaluation"]["promotion_eligibility"] == "NOT_ELIGIBLE"
assert report["evaluation"]["economic_metrics_available"] is False
assert report["profitability_claim"] is False
assert report["git_sha"]
print("report invariants OK")
PY

echo "==> Gate 3 research verification passed"
