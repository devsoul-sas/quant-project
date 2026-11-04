"""ECB euro reference-rates data-rights manifest (open, permissive license)."""

from __future__ import annotations

from devsoul_quant.domain.data_rights import (
    DataRightsManifest,
    DataSourceKind,
    build_manifest,
)

ECB_SOURCE_ID = "ecb-euro-fx-reference"
ECB_LICENSE_IDENTIFIER = "ECB-COPYRIGHT-POLICY"
ECB_LICENSE_URL = "https://www.ecb.europa.eu/services/disclaimer/html/index.en.html"

# The ECB copyright policy grants "free use of the information obtained directly"
# with no deletion obligation, so retention is effectively indefinite. The
# fail-closed gate requires an explicit positive retention window; a long-lived
# value signals persistent retention without inventing a TTL the license does not impose.
ECB_RETENTION_SECONDS = 3_155_695_200  # 100 years


def build_ecb_manifest(*, retrieved_at: int) -> DataRightsManifest:
    """Build the approved open-license manifest for ECB euro FX reference rates.

    The license permits storage, derived works, and commercial redistribution,
    all conditioned on citing the ECB as the source, disclosing the free
    availability of the data, and stating any modification explicitly.
    """
    return build_manifest(
        source_id=ECB_SOURCE_ID,
        source_kind=DataSourceKind.OPEN_LICENSE,
        license_identifier=ECB_LICENSE_IDENTIFIER,
        license_url=ECB_LICENSE_URL,
        retrieved_at=retrieved_at,
        retention_seconds=ECB_RETENTION_SECONDS,
        derived_artifacts_allowed=True,
        partner_display_allowed=True,
        redistribution_allowed=True,
        commercial_use_allowed=True,
        geographic_constraints=(),
        written_authorization_ref=None,
    )
