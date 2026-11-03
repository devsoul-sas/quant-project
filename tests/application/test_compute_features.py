"""Feature computation over dataset snapshot tests."""

from devsoul_quant.application.build_dataset import build_dataset
from devsoul_quant.application.compute_features import compute_features_for_snapshot
from devsoul_quant.domain.data_rights import DataRightsManifest, DataSourceKind, build_manifest
from devsoul_quant.domain.datasets import GENERATOR_VERSION, SCHEMA_VERSION, DatasetSpec
from devsoul_quant.domain.features import FeatureSetSpec


def _manifest() -> DataRightsManifest:
    return build_manifest(
        source_id="devsoul-synthetic",
        source_kind=DataSourceKind.DEVSOUL_SYNTHETIC,
        license_identifier="DEVSOUL-INTERNAL-1.0",
        license_url=None,
        retrieved_at=1_760_000_000,
        retention_seconds=31_536_000,
        derived_artifacts_allowed=True,
        partner_display_allowed=True,
        redistribution_allowed=False,
        commercial_use_allowed=False,
        geographic_constraints=(),
        written_authorization_ref=None,
    )


def test_compute_features_for_snapshot_binds_snapshot_hash() -> None:
    manifest = _manifest()
    snapshot = build_dataset(
        spec=DatasetSpec(
            generator_version=GENERATOR_VERSION,
            seed=42,
            start_epoch=1_700_000_000,
            interval=1,
            row_count=8,
            schema_version=SCHEMA_VERSION,
            rights_manifest_hash=manifest.manifest_hash,
        ),
        manifest=manifest,
    )
    spec = FeatureSetSpec(
        name="momentum-baseline",
        version="1",
        lag_windows=(1, 3),
        rolling_window=3,
    )

    frame = compute_features_for_snapshot(spec=spec, snapshot=snapshot)

    assert frame.dataset_hash == snapshot.data_hash
    assert len(frame.rows) == len(snapshot.ticks)
    assert frame.rows[0].warmup is True
