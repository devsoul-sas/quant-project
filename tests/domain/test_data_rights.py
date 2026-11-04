"""Fail-closed data-rights manifest tests."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from devsoul_quant.domain.data_rights import (
    DERIV_SOURCE_ID,
    DataRightsManifest,
    DataSourceKind,
    InvalidDataRightsManifest,
    PersistentUseDecision,
    build_manifest,
    decide_persistent_use,
    manifest_from_dict,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "data" / "source-manifest.schema.json"
MANIFESTS_DIR = REPO_ROOT / "examples" / "manifests"


def _valid(**overrides: object) -> DataRightsManifest:
    fields: dict[str, object] = {
        "source_id": "devsoul-synthetic",
        "source_kind": DataSourceKind.DEVSOUL_SYNTHETIC,
        "license_identifier": "DEVSOUL-INTERNAL-1.0",
        "license_url": None,
        "retrieved_at": 1_760_000_000,
        "retention_seconds": 31_536_000,
        "derived_artifacts_allowed": True,
        "partner_display_allowed": True,
        "redistribution_allowed": False,
        "commercial_use_allowed": False,
        "geographic_constraints": (),
        "written_authorization_ref": None,
    }
    fields.update(overrides)
    return build_manifest(**fields)  # type: ignore[arg-type]


def test_synthetic_manifest_is_allowed() -> None:
    outcome = decide_persistent_use(_valid())

    assert outcome.decision is PersistentUseDecision.ALLOW
    assert outcome.reasons == ()


def test_manifest_with_stale_hash_is_denied() -> None:
    manifest = _valid()
    tampered = replace(manifest, commercial_use_allowed=True)

    outcome = decide_persistent_use(tampered)

    assert outcome.decision is PersistentUseDecision.DENY
    assert "manifest hash mismatch" in outcome.reasons


def test_missing_license_is_denied() -> None:
    outcome = decide_persistent_use(_valid(license_identifier=None, license_url=None))

    assert outcome.decision is PersistentUseDecision.DENY
    assert "missing license" in outcome.reasons


def test_ambiguous_retention_is_denied() -> None:
    outcome = decide_persistent_use(_valid(retention_seconds=None))

    assert outcome.decision is PersistentUseDecision.DENY
    assert "unspecified retention" in outcome.reasons


def test_zero_retention_is_denied() -> None:
    outcome = decide_persistent_use(_valid(retention_seconds=0))

    assert outcome.decision is PersistentUseDecision.DENY
    assert "no persistent retention allowed" in outcome.reasons


def test_missing_retrieved_at_is_denied() -> None:
    outcome = decide_persistent_use(_valid(retrieved_at=None))

    assert outcome.decision is PersistentUseDecision.DENY
    assert "missing retrieved-at" in outcome.reasons


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(InvalidDataRightsManifest, match="timezone"):
        build_manifest(
            source_id="devsoul-synthetic",
            source_kind=DataSourceKind.DEVSOUL_SYNTHETIC,
            license_identifier="DEVSOUL-INTERNAL-1.0",
            license_url=None,
            retrieved_at=datetime(2026, 10, 29),
            retention_seconds=10,
        )


def test_unknown_source_kind_is_rejected() -> None:
    with pytest.raises(InvalidDataRightsManifest, match="source kind"):
        _valid(source_kind="BOGUS")


def test_deriv_persistent_rights_require_written_authorization() -> None:
    manifest = _valid(
        source_id=DERIV_SOURCE_ID,
        source_kind=DataSourceKind.LICENSED_EXTERNAL,
        license_identifier="DERIV-API-USERS-TERMS-R26",
        license_url="https://deriv.com/terms-and-conditions/api-users",
        written_authorization_ref=None,
    )

    outcome = decide_persistent_use(manifest)

    assert outcome.decision is PersistentUseDecision.DENY
    assert any("deriv" in reason and "authorization" in reason for reason in outcome.reasons)


def test_external_written_authorization_is_denied_when_not_in_approved_registry() -> None:
    manifest = _valid(
        source_id=DERIV_SOURCE_ID,
        source_kind=DataSourceKind.LICENSED_EXTERNAL,
        license_identifier="DERIV-API-USERS-TERMS-R26",
        license_url="https://deriv.com/terms-and-conditions/api-users",
        written_authorization_ref="AUTH-REF-2026-001",
    )

    outcome = decide_persistent_use(manifest)

    assert outcome.decision is PersistentUseDecision.DENY
    assert "external authorization is not in the approved registry" in outcome.reasons


def test_external_written_authorization_is_allowed_from_approved_registry() -> None:
    manifest = _valid(
        source_id="licensed-provider",
        source_kind=DataSourceKind.LICENSED_EXTERNAL,
        license_identifier="COMMERCIAL-1",
        license_url="https://provider.example/terms",
        written_authorization_ref="sha256:approved-license",
    )

    outcome = decide_persistent_use(
        manifest,
        approved_authorization_refs=frozenset({"sha256:approved-license"}),
    )

    assert outcome.decision is PersistentUseDecision.ALLOW


def test_open_license_manifest_is_allowed_without_written_authorization() -> None:
    manifest = _valid(
        source_id="ecb-euro-fx-reference",
        source_kind=DataSourceKind.OPEN_LICENSE,
        license_identifier="ECB-COPYRIGHT-POLICY",
        license_url="https://www.ecb.europa.eu/services/disclaimer/html/index.en.html",
        written_authorization_ref=None,
    )

    outcome = decide_persistent_use(manifest)

    assert outcome.decision is PersistentUseDecision.ALLOW
    assert outcome.reasons == ()


def test_open_license_manifest_still_requires_a_license() -> None:
    manifest = _valid(
        source_id="ecb-euro-fx-reference",
        source_kind=DataSourceKind.OPEN_LICENSE,
        license_identifier=None,
        license_url=None,
    )

    outcome = decide_persistent_use(manifest)

    assert outcome.decision is PersistentUseDecision.DENY
    assert "missing license" in outcome.reasons


def test_operation_specific_right_is_required() -> None:
    manifest = _valid(partner_display_allowed=False)

    outcome = decide_persistent_use(manifest, require_partner_display=True)

    assert outcome.decision is PersistentUseDecision.DENY
    assert "partner display is not allowed" in outcome.reasons


def test_deriv_ephemeral_retention_is_not_an_authorization_gap() -> None:
    manifest = _valid(
        source_id=DERIV_SOURCE_ID,
        source_kind=DataSourceKind.LICENSED_EXTERNAL,
        license_identifier="DERIV-API-USERS-TERMS-R26",
        license_url="https://deriv.com/terms-and-conditions/api-users",
        retention_seconds=0,
        written_authorization_ref=None,
    )

    outcome = decide_persistent_use(manifest)

    assert outcome.decision is PersistentUseDecision.DENY
    assert "no persistent retention allowed" in outcome.reasons
    assert "no persistent retention allowed" in outcome.reasons


def test_manifest_hash_is_deterministic_and_canonical() -> None:
    first = _valid()
    second = _valid()
    changed = _valid(license_identifier="OTHER-1.0")

    assert first.manifest_hash == second.manifest_hash
    assert len(first.manifest_hash) == 64
    assert all(character in "0123456789abcdef" for character in first.manifest_hash)
    assert changed.manifest_hash != first.manifest_hash


def test_manifest_is_immutable() -> None:
    manifest = _valid()

    with pytest.raises(AttributeError):
        manifest.source_id = "other"  # type: ignore[misc]


def test_aware_datetime_is_normalized_to_epoch() -> None:
    aware = datetime(2026, 10, 29, 12, 0, 0, tzinfo=UTC)

    manifest = _valid(retrieved_at=aware)

    assert manifest.retrieved_at == int(aware.timestamp())


def test_schema_and_fixture_files_parse_as_json() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["type"] == "object"

    for name in ("devsoul-synthetic.example.json", "unapproved-external.example.json"):
        payload = json.loads((MANIFESTS_DIR / name).read_text(encoding="utf-8"))
        assert payload["source_id"]
        assert payload["source_kind"]


def test_devsoul_synthetic_fixture_round_trips_to_allowed() -> None:
    payload = json.loads(
        (MANIFESTS_DIR / "devsoul-synthetic.example.json").read_text(encoding="utf-8")
    )

    manifest = manifest_from_dict(payload)

    assert manifest.manifest_hash == payload["manifest_hash"]
    assert decide_persistent_use(manifest).decision is PersistentUseDecision.ALLOW


def test_unapproved_external_fixture_round_trips_to_denied() -> None:
    payload = json.loads(
        (MANIFESTS_DIR / "unapproved-external.example.json").read_text(encoding="utf-8")
    )

    manifest = manifest_from_dict(payload)

    assert manifest.manifest_hash == payload["manifest_hash"]
    assert decide_persistent_use(manifest).decision is PersistentUseDecision.DENY


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_id": "   "},
        {"retrieved_at": -1},
        {"retrieved_at": "2026-10-29"},
        {"source_kind": 123},
        {"retention_seconds": -1},
        {"derived_artifacts_allowed": "yes"},
        {"geographic_constraints": ["europe"]},
        {"geographic_constraints": (" ",)},
        {"written_authorization_ref": "   "},
    ],
)
def test_build_manifest_rejects_invalid_fields(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidDataRightsManifest):
        _valid(**overrides)


def test_manifest_to_dict_is_json_ready_and_matches_schema_shape() -> None:
    manifest = _valid(geographic_constraints=("co", "br"))

    payload = manifest.to_dict()

    assert payload["source_id"] == "devsoul-synthetic"
    assert payload["source_kind"] == "DEVSOUL_SYNTHETIC"
    assert payload["geographic_constraints"] == ["co", "br"]
    assert payload["manifest_hash"] == manifest.manifest_hash
    json.dumps(payload)


def test_manifest_from_dict_accepts_missing_constraints_key() -> None:
    payload: dict[str, object] = {
        "source_id": "devsoul-synthetic",
        "source_kind": "DEVSOUL_SYNTHETIC",
        "license_identifier": "DEVSOUL-INTERNAL-1.0",
        "license_url": None,
        "retrieved_at": 1_760_000_000,
        "retention_seconds": 31_536_000,
    }

    manifest = manifest_from_dict(payload)

    assert manifest.geographic_constraints == ()


def test_manifest_from_dict_accepts_null_constraints() -> None:
    payload: dict[str, object] = {
        "source_id": "devsoul-synthetic",
        "source_kind": "DEVSOUL_SYNTHETIC",
        "license_identifier": "DEVSOUL-INTERNAL-1.0",
        "license_url": None,
        "retrieved_at": 1_760_000_000,
        "retention_seconds": 31_536_000,
        "geographic_constraints": None,
    }

    manifest = manifest_from_dict(payload)

    assert manifest.geographic_constraints == ()
