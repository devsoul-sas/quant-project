"""Federal Reserve H.10 data-rights manifest tests."""

import pytest

from devsoul_quant.adapters.federal_reserve.manifest import (
    FED_H10_LICENSE_IDENTIFIER,
    FED_H10_LICENSE_URL,
    FED_H10_RETENTION_SECONDS,
    FED_H10_SOURCE_ID,
    build_fed_h10_manifest,
)
from devsoul_quant.domain.data_rights import (
    DataSourceKind,
    InvalidDataRightsManifest,
    PersistentUseDecision,
    decide_persistent_use,
)


def test_fed_h10_manifest_is_public_domain_and_approved() -> None:
    manifest = build_fed_h10_manifest(retrieved_at=1_760_000_000)

    assert manifest.source_id == FED_H10_SOURCE_ID
    assert manifest.source_kind is DataSourceKind.OPEN_LICENSE
    assert manifest.license_identifier == FED_H10_LICENSE_IDENTIFIER
    assert manifest.license_url == FED_H10_LICENSE_URL
    assert manifest.retention_seconds == FED_H10_RETENTION_SECONDS
    assert manifest.derived_artifacts_allowed is True
    assert manifest.partner_display_allowed is True
    assert manifest.redistribution_allowed is True
    assert manifest.commercial_use_allowed is True
    assert manifest.written_authorization_ref is None

    outcome = decide_persistent_use(manifest, require_derived_artifacts=True)
    assert outcome.decision is PersistentUseDecision.ALLOW
    assert outcome.reasons == ()


def test_fed_h10_manifest_hash_is_deterministic() -> None:
    first = build_fed_h10_manifest(retrieved_at=1_760_000_000)
    second = build_fed_h10_manifest(retrieved_at=1_760_000_000)

    assert first.manifest_hash == second.manifest_hash
    assert len(first.manifest_hash) == 64


def test_fed_h10_manifest_rejects_negative_retrieved_at() -> None:
    with pytest.raises(InvalidDataRightsManifest):
        build_fed_h10_manifest(retrieved_at=-1)
