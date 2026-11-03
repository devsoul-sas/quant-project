"""Compute versioned causal features over a dataset snapshot."""

from devsoul_quant.domain.datasets import DatasetSnapshot
from devsoul_quant.domain.features import FeatureFrame, FeatureSetSpec, compute_features


def compute_features_for_snapshot(
    *,
    spec: FeatureSetSpec,
    snapshot: DatasetSnapshot,
) -> FeatureFrame:
    """Compute causal features bound to a dataset snapshot's data hash."""
    return compute_features(spec=spec, ticks=snapshot.ticks, dataset_hash=snapshot.data_hash)
