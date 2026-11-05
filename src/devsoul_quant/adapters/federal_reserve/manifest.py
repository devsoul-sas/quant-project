"""Federal Reserve H.10 public-domain data-rights manifest."""

from __future__ import annotations

from devsoul_quant.domain.data_rights import (
    DataRightsManifest,
    DataSourceKind,
    build_manifest,
)

FED_H10_SOURCE_ID = "federal-reserve-h10-fx"
FED_H10_LICENSE_IDENTIFIER = "US-PUBLIC-DOMAIN-17-USC-105"
FED_H10_LICENSE_URL = "https://www.federalreserve.gov/disclaimer.htm"
FED_H10_RETENTION_SECONDS = 3_155_695_200  # 100 years; no public-domain TTL


def build_fed_h10_manifest(*, retrieved_at: int) -> DataRightsManifest:
    """Build the approved public-domain manifest for Federal Reserve H.10."""
    return build_manifest(
        source_id=FED_H10_SOURCE_ID,
        source_kind=DataSourceKind.OPEN_LICENSE,
        license_identifier=FED_H10_LICENSE_IDENTIFIER,
        license_url=FED_H10_LICENSE_URL,
        retrieved_at=retrieved_at,
        retention_seconds=FED_H10_RETENTION_SECONDS,
        derived_artifacts_allowed=True,
        partner_display_allowed=True,
        redistribution_allowed=True,
        commercial_use_allowed=True,
        geographic_constraints=(),
        written_authorization_ref=None,
    )
