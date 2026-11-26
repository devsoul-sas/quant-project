"""Tests for declarative provider constraints and storage routing."""

import pytest

from devsoul_quant.domain.data_provider import (
    DERIV_PROVIDER,
    DEVSOUL_SYNTHETIC_PROVIDER,
    InvalidProviderConstraints,
    ProviderConstraints,
    StorageDisposition,
    UnknownProvider,
    provider_constraints,
    registered_source_ids,
)
from devsoul_quant.domain.data_rights import DataSourceKind


def test_deriv_is_ephemeral_only() -> None:
    assert DERIV_PROVIDER.storage_disposition() is StorageDisposition.EPHEMERAL
    assert DERIV_PROVIDER.retention_seconds == 0
    assert DERIV_PROVIDER.historical_available is False
    assert DERIV_PROVIDER.live_available is True


def test_synthetic_is_persistable_and_historical() -> None:
    assert DEVSOUL_SYNTHETIC_PROVIDER.storage_disposition() is StorageDisposition.PERSIST
    assert DEVSOUL_SYNTHETIC_PROVIDER.retention_seconds is None
    assert DEVSOUL_SYNTHETIC_PROVIDER.historical_available is True


def test_registry_lookup_by_source_id() -> None:
    assert provider_constraints("deriv") is DERIV_PROVIDER
    assert provider_constraints("devsoul-synthetic") is DEVSOUL_SYNTHETIC_PROVIDER


def test_registry_lists_both_providers() -> None:
    assert registered_source_ids() == ("devsoul-synthetic", "deriv")


def test_unknown_provider_raises() -> None:
    with pytest.raises(UnknownProvider, match="no provider"):
        provider_constraints("not-a-provider")


def test_retention_must_be_below_twenty_four_hours() -> None:
    with pytest.raises(InvalidProviderConstraints, match="retention_seconds"):
        ProviderConstraints(
            source_id="x",
            source_kind=DataSourceKind.OPEN_LICENSE,
            retention_seconds=86_400,
            historical_available=True,
            live_available=False,
        )


def test_retention_rejects_negative_value() -> None:
    with pytest.raises(InvalidProviderConstraints, match="retention_seconds"):
        ProviderConstraints(
            source_id="x",
            source_kind=DataSourceKind.OPEN_LICENSE,
            retention_seconds=-1,
            historical_available=True,
            live_available=False,
        )


def test_constraints_require_blank_source_id() -> None:
    with pytest.raises(InvalidProviderConstraints, match="source_id"):
        ProviderConstraints(
            source_id="",
            source_kind=DataSourceKind.OPEN_LICENSE,
            retention_seconds=None,
            historical_available=True,
            live_available=False,
        )


def test_constraints_require_valid_kind() -> None:
    with pytest.raises(InvalidProviderConstraints, match="source_kind"):
        ProviderConstraints(
            source_id="x",
            source_kind="NOT_A_KIND",  # type: ignore[arg-type]
            retention_seconds=None,
            historical_available=True,
            live_available=False,
        )


def test_bounded_retention_is_persistable() -> None:
    constraints = ProviderConstraints(
        source_id="x",
        source_kind=DataSourceKind.OPEN_LICENSE,
        retention_seconds=3600,
        historical_available=True,
        live_available=False,
    )
    assert constraints.storage_disposition() is StorageDisposition.PERSIST
