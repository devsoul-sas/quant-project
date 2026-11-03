# Gate 3 Provider-Independent Research Implementation Plan

> **For Hermes:** Implement task-by-task with strict RED → GREEN → REFACTOR and independent review before promotion.

**Goal:** Produce a partner-demonstrable, reproducible quantitative research pipeline that does not depend on Deriv permission, does not claim profitability, and can later ingest a separately approved/licensed data source without changing the domain core.

**Architecture:** Keep Deriv behind a blocked compliance gate. Build deterministic synthetic dataset snapshots, temporal feature computation, walk-forward evaluation, evidence grading, and signed/hash-linked reports through provider-neutral ports. Treat provider selection as a separate due-diligence lane: no external dataset enters persistence until its license manifest passes validation.

**Tech Stack:** Python 3.13.13, uv, pytest, SQLAlchemy/PostgreSQL only for own/licensed artifacts, existing immutable domain and hash-chained ledger, standard-library statistics/Decimal first (no ML dependency yet).

---

## Current state and decision

- `main` is clean and synchronized with `origin/main` at `f9f5e8d`.
- Gate 2 is complete: injected clocks, domain entities, provider-neutral ports, PostgreSQL append-only ledger, migrations, dual memory/PostgreSQL demo, and independent approval.
- Latest Deriv response (Amy, received before this plan): the relevant team is still reviewing the request and will notify DevSoul when there is an update. The chat was closed while review continues.
- This response is **not written authorization** for retention, derived artifacts, partner display, redistribution, or commercial use.
- Deriv remains non-critical and blocked for persistent market-data research.
- Real money, `REAL`, `/ws/real`, OTP/account credentials, and the user's USD 200 remain structurally outside the project.

## Acceptance criteria

1. A deterministic synthetic research run is reproducible byte-for-byte from a frozen spec and seed.
2. Dataset, features, strategy release, risk policy, and report have SHA-256 identities.
3. Temporal splits enforce ordering, purge, embargo, and sealed holdout boundaries.
4. Metrics label synthetic/tick-proxy evidence as non-economic and cannot promote a strategy to Deriv demo.
5. Every persisted dataset is preceded by a machine-readable license/retention manifest.
6. An absent/invalid provider license fails closed before any provider payload is stored.
7. A partner report clearly separates engineering evidence, scientific evidence, blocked evidence, and forbidden claims.
8. Existing demo-only and no-real-money tests remain green.

---

### Task 1: Record the Deriv review state and non-blocking pivot

**Objective:** Preserve a redactable operational record without copying support correspondence verbatim or treating review as permission.

**Files:**
- Modify: `docs/scope/gate-0-status.md`
- Modify: `docs/data/provider-data-policy.md`
- Create: `docs/adr/ADR-006-provider-independent-research-pivot.md`
- Test: `tests/docs/test_policy_documents.py`

**Steps:**
1. Write a failing documentation test asserting that Gate 0 distinguishes `PENDING_PROVIDER_REVIEW` from authorization and names the alternative-license path.
2. Run `uv run pytest tests/docs/test_policy_documents.py -q --no-cov`; expect RED because the documents are not updated.
3. Add a dated, paraphrased status: specialist review still pending, chat closure has no licensing effect, Deriv is no longer on the critical path.
4. ADR-006 must record alternatives considered: wait, violate/assume permission, ephemeral-only Deriv integration, and provider-independent/licensed-source pivot. Select the last option.
5. Run the targeted test; expect PASS.

**Safety:** Do not store email addresses, ticket payloads, account IDs, or verbatim support transcripts.

---

### Task 2: Introduce a fail-closed data-rights manifest

**Objective:** Make persistence conditional on explicit machine-readable rights rather than developer convention.

**Files:**
- Create: `src/devsoul_quant/domain/data_rights.py`
- Create: `tests/domain/test_data_rights.py`
- Create: `docs/data/source-manifest.schema.json`
- Create: `data/manifests/README.md`

**Domain shape:**
- `DataSourceKind`: `DEVSOUL_SYNTHETIC`, `LICENSED_EXTERNAL`.
- `DataRightsManifest`: source ID, license identifier/URL, retrieved-at, allowed retention, derived-artifact permission, partner-display permission, redistribution permission, commercial-use permission, geographic constraints, manifest hash.
- No `DERIV` manifest may claim persistent rights without a separately supplied written-authorization reference.
- `PersistentUseDecision`: `ALLOW` or structured `DENY` reasons.

**Steps:**
1. RED tests for missing license, ambiguous retention, naive timestamps, unknown source kind, and persistent Deriv content without authorization.
2. Implement immutable validation and canonical SHA-256.
3. Add schema fixtures for one DevSoul synthetic manifest and one denied/unapproved external manifest.
4. Verify JSON Schema documents parse with the standard library; do not add a dependency unless required.
5. Run `uv run pytest tests/domain/test_data_rights.py -q --no-cov`; expect PASS.

---

### Task 3: Build immutable synthetic dataset snapshots

**Objective:** Turn the existing generator into a reproducible research artifact with complete lineage.

**Files:**
- Create: `src/devsoul_quant/domain/datasets.py`
- Create: `src/devsoul_quant/application/build_dataset.py`
- Modify: `src/devsoul_quant/domain/synthetic.py`
- Create: `tests/domain/test_datasets.py`
- Create: `tests/application/test_build_dataset.py`

**Steps:**
1. RED tests for deterministic rows/hash under mutable global Decimal context, invalid ordering, duplicate timestamps, non-synthetic provenance, and mismatched manifest hash.
2. Define frozen `DatasetSpec` and `DatasetSnapshot` containing generator version, seed, start time, interval, row count, schema version, rights-manifest hash, and data SHA-256.
3. Serialize canonical JSON Lines with sorted keys and fixed Decimal strings; never serialize floats.
4. Require an `ALLOW` persistent-use decision before a snapshot can be written.
5. Use `Clock` only through injection; no `datetime.now()` in domain/application code.
6. Verify same spec produces identical bytes/hash in two temporary directories.

---

### Task 4: Add a causal temporal feature pipeline

**Objective:** Compute versioned features without future leakage and with explicit warm-up gaps.

**Files:**
- Create: `src/devsoul_quant/domain/features.py`
- Create: `src/devsoul_quant/application/compute_features.py`
- Create: `tests/domain/test_features.py`
- Create: `tests/application/test_compute_features.py`

**Initial features (YAGNI):**
- lagged return over 1 and 3 observations;
- rolling mean over 3 observations;
- rolling absolute move over 3 observations;
- warm-up status.

**Steps:**
1. RED tests prove each feature at index `t` uses only rows `<= t` and that modifying `t+1` cannot change features at `t`.
2. Define immutable `FeatureSetSpec` with name/version/window definitions and canonical hash.
3. Use local Decimal contexts and explicit rounding.
4. Preserve `UNAVAILABLE` rather than impute missing warm-up observations silently.
5. Hash canonical feature output and bind it to dataset snapshot hash.
6. Run targeted tests and the global Decimal invariance probe.

---

### Task 5: Implement temporal split, purge, embargo, and sealed holdout

**Objective:** Prevent accidental leakage and premature holdout inspection.

**Files:**
- Create: `src/devsoul_quant/domain/validation.py`
- Create: `src/devsoul_quant/application/prepare_validation.py`
- Create: `tests/domain/test_validation.py`
- Create: `tests/application/test_prepare_validation.py`

**Steps:**
1. RED tests for overlap, unordered boundaries, inadequate purge, inadequate embargo, and direct holdout iteration before release freeze.
2. Define `TemporalSplitSpec`, `WalkForwardFold`, and `SealedHoldout`.
3. Require purge at least equal to maximum lookback/label overlap; require explicit embargo.
4. Expose only holdout hash/count before `StrategyRelease` is frozen.
5. Opening a holdout emits a ledger event tied to release hash and validation-run ID.
6. Re-opening or changing specs after freeze invalidates the run rather than mutating it.

---

### Task 6: Add evidence-graded evaluation metrics

**Objective:** Evaluate engineering behavior while making economic overclaim impossible.

**Files:**
- Create: `src/devsoul_quant/domain/metrics.py`
- Create: `src/devsoul_quant/application/evaluate.py`
- Create: `tests/domain/test_metrics.py`
- Create: `tests/application/test_evaluate.py`

**Initial outputs:**
- decisions, enter/wait counts, wait rate;
- directional hit rate (explicitly non-economic);
- longest directional loss streak;
- fold consistency;
- deterministic block-bootstrap interval for directional accuracy;
- evidence mode and promotion eligibility.

**Steps:**
1. RED tests ensure `TICK_PROXY_BACKTEST` cannot produce `expected_value`, ROI, profit, payout, or `promotion_eligible=true`.
2. Define evidence modes as an enum and a promotion matrix.
3. Use an injected deterministic seed for block bootstrap.
4. Require observed/licensed proposal economics before enabling economic metrics in any future adapter.
5. Reject empty samples, malformed outcomes, and mixed provenance.
6. Verify repeated evaluation is byte-identical.

---

### Task 7: Produce an auditable partner evidence package

**Objective:** Give partners visible progress without implying provider approval or profitability.

**Files:**
- Create: `src/devsoul_quant/application/reporting.py`
- Modify: `src/devsoul_quant/cli.py`
- Create: `tests/application/test_reporting.py`
- Modify: `tests/test_cli.py`
- Create: `docs/partner/demo-evidence-guide.md`

**CLI:**
```text
devsoul-quant research synthetic --spec <path> --output <directory>
```

**Package contents:**
- `run-report.json` canonical machine report;
- `run-summary.md` human-readable summary;
- `manifest.json` with all filenames, sizes, and SHA-256;
- no raw provider content;
- no credentials, account IDs, DSNs, or absolute local paths.

**Steps:**
1. RED tests for deterministic package hashes, path traversal, pre-existing output directory, secret-pattern redaction, and forbidden profitability language.
2. Report four separate states: engineering readiness, scientific evidence, provider/license blockers, real-money exclusion.
3. Include exact reproduction command and Git SHA.
4. Fail closed if the working tree is dirty unless `--allow-dirty` is explicitly used and prominently recorded.
5. Verify two runs from identical clean inputs produce identical package contents.

---

### Task 8: Evaluate alternative providers/licenses without integrating them

**Objective:** Replace urgency-driven guessing with a reproducible provider decision gate.

**Files:**
- Create: `docs/data/provider-evaluation-template.md`
- Create: `docs/data/provider-candidates.md`
- Create: `docs/data/provider-selection-decision.md`
- Create: `tests/docs/test_provider_selection.py`

**Mandatory criteria:**
- explicit historical-data retention rights;
- derived features/models/metrics retention rights;
- commercial/internal partner display rights;
- redistribution restrictions;
- reproducible historical access and timestamp semantics;
- available economic fields (bid/ask/payout/costs) appropriate to the product;
- API/download limits and price;
- jurisdiction/product compatibility;
- written source URL, retrieval timestamp, document version, and hash where permitted.

**Steps:**
1. Build a candidate matrix from current official terms only; tutorials and marketing pages are insufficient.
2. Mark unknowns as blockers, never infer permission from API accessibility.
3. Do not download or persist candidate data during this task.
4. Select a provider only if all mandatory rights are explicit; otherwise select `NO_PROVIDER_APPROVED` and continue synthetic research.
5. Require human/legal review before partner redistribution or SaaS use.

---

### Task 9: Full Gate 3 verification and independent review

**Objective:** Prove determinism, compliance, and no regression before presenting the package.

**Files:**
- Modify: `scripts/verify.sh`
- Create or modify: `scripts/verify-research.sh`
- Modify: `README.md`

**Verification commands:**
```bash
uv lock --check
docker compose config --quiet
uv run ruff format --check src tests migrations
uv run ruff check src tests migrations
uv run mypy
uv run pytest
./scripts/verify.sh
./scripts/verify-integration.sh  # with local isolated PostgreSQL URLs
uv build
```

**Additional probes:**
1. Run the synthetic research package twice and compare directory SHA-256 manifests.
2. Vary global Decimal precision/rounding and confirm identical artifacts.
3. Attempt to persist an unapproved provider manifest; expect denial before write.
4. Search tracked files for `REAL`, `/ws/real`, OTP, account IDs, DSNs, secrets, and profitability claims.
5. Confirm no Deriv payload/data artifact appears in Git.
6. Independent read-only review: security, leakage, scientific claims, rights gating, reproducibility.
7. Commit/push only with explicit user authorization.

---

## Partner-facing milestone

At the end of Gate 3, the honest partner message is:

- the execution/replay/audit architecture works end-to-end;
- the research pipeline is deterministic and scientifically guarded;
- synthetic results validate engineering, not profitability;
- Deriv permission remains pending and is no longer blocking engineering;
- economic validation starts only after a source with explicit compatible rights is approved;
- real money remains excluded until a separate future protocol, evidence gate, and explicit authorization.

## Explicit non-goals

- No live Deriv collector.
- No persistence of Deriv-derived data beyond the current terms.
- No model optimization against a final holdout.
- No statement of expected profits.
- No dashboard/SaaS deployment.
- No real-money broker or use of the USD 200.
