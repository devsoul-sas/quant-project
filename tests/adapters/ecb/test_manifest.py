"""ECB data-rights manifest tests."""

import pytest

from devsoul_quant.adapters.ecb.manifest import (
    ECB_LICENSE_IDENTIFIER,
    ECB_LICENSE_URL,
    ECB_RETENTION_SECONDS,
    ECB_SOURCE_ID,
    build_ecb_manifest,
)
from devsoul_quant.domain.data_rights import (
    DataSourceKind,
    InvalidDataRightsManifest,
    PersistentUseDecision,
    decide_persistent_use,
)


def test_ecb_manifest_is_open_license_and_approved() -> None:
    manifest = build_ecb_manifest(retrieved_at=1_760_000_000)

    assert manifest.source_id == ECB_SOURCE_ID
    assert manifest.source_kind is DataSourceKind.OPEN_LICENSE
    assert manifest.license_identifier == ECB_LICENSE_IDENTIFIER
    assert manifest.license_url == ECB_LICENSE_URL
    assert manifest.retention_seconds == ECB_RETENTION_SECONDS
    assert manifest.derived_artifacts_allowed is True
    assert manifest.partner_display_allowed is True
    assert manifest.redistribution_allowed is True
    assert manifest.commercial_use_allowed is True
    assert manifest.written_authorization_ref is None

    outcome = decide_persistent_use(manifest, require_derived_artifacts=True)
    assert outcome.decision is PersistentUseDecision.ALLOW
    assert outcome.reasons == ()


def test_ecb_manifest_requires_no_written_authorization() -> None:
    manifest = build_ecb_manifest(retrieved_at=1_760_000_000)

    outcome = decide_persistent_use(manifest)

    assert outcome.decision is PersistentUseDecision.ALLOW


def test_ecb_manifest_hash_is_deterministic() -> None:
    first = build_ecb_manifest(retrieved_at=1_760_000_000)
    second = build_ecb_manifest(retrieved_at=1_760_000_000)

    assert first.manifest_hash == second.manifest_hash
    assert len(first.manifest_hash) == 64


def test_ecb_manifest_hash_depends_on_retrieved_at() -> None:
    first = build_ecb_manifest(retrieved_at=1_760_000_000)
    second = build_ecb_manifest(retrieved_at=1_760_000_001)

    assert first.manifest_hash != second.manifest_hash


def test_ecb_manifest_rejects_negative_retrieved_at() -> None:
    with pytest.raises(InvalidDataRightsManifest):
        build_ecb_manifest(retrieved_at=-1)
