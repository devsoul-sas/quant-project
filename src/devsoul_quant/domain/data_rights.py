"""Fail-closed data-rights manifests that gate any persistent use."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256

DERIV_SOURCE_ID = "deriv"


class DataSourceKind(StrEnum):
    """Where a dataset comes from and who owns its rights."""

    DEVSOUL_SYNTHETIC = "DEVSOUL_SYNTHETIC"
    LICENSED_EXTERNAL = "LICENSED_EXTERNAL"


class PersistentUseDecision(StrEnum):
    """Whether a manifest authorizes persistent use of the described data."""

    ALLOW = "ALLOW"
    DENY = "DENY"


class InvalidDataRightsManifest(ValueError):
    """Raised when a manifest fails structural validation."""


@dataclass(frozen=True, slots=True)
class PersistentUseOutcome:
    """Structured decision with the reasons that produced it."""

    decision: PersistentUseDecision
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DataRightsManifest:
    """Immutable declaration of a dataset's provenance and use rights."""

    source_id: str
    source_kind: DataSourceKind
    license_identifier: str | None
    license_url: str | None
    retrieved_at: int | None
    retention_seconds: int | None
    derived_artifacts_allowed: bool
    partner_display_allowed: bool
    redistribution_allowed: bool
    commercial_use_allowed: bool
    geographic_constraints: tuple[str, ...]
    written_authorization_ref: str | None
    manifest_hash: str

    def to_dict(self) -> dict[str, object]:
        """Return the manifest as a JSON-ready mapping matching the schema."""
        return {
            "source_id": self.source_id,
            "source_kind": str(self.source_kind),
            "license_identifier": self.license_identifier,
            "license_url": self.license_url,
            "retrieved_at": self.retrieved_at,
            "retention_seconds": self.retention_seconds,
            "derived_artifacts_allowed": self.derived_artifacts_allowed,
            "partner_display_allowed": self.partner_display_allowed,
            "redistribution_allowed": self.redistribution_allowed,
            "commercial_use_allowed": self.commercial_use_allowed,
            "geographic_constraints": list(self.geographic_constraints),
            "written_authorization_ref": self.written_authorization_ref,
            "manifest_hash": self.manifest_hash,
        }


def _require_non_blank(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidDataRightsManifest(f"{field} must be a non-blank string")


def _normalize_retrieved_at(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is int:
        if value < 0:
            raise InvalidDataRightsManifest("retrieved_at must be a non-negative epoch integer")
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise InvalidDataRightsManifest("retrieved_at must be timezone-aware")
        return int(value.timestamp())
    raise InvalidDataRightsManifest(
        "retrieved_at must be an epoch integer, a timezone-aware datetime, or None"
    )


def _normalize_source_kind(value: object) -> DataSourceKind:
    if isinstance(value, DataSourceKind):
        return value
    if isinstance(value, str):
        try:
            return DataSourceKind(value)
        except ValueError:
            raise InvalidDataRightsManifest(f"unknown source kind: {value}") from None
    raise InvalidDataRightsManifest("source_kind must be a DataSourceKind or a known string")


def _normalize_constraints(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise InvalidDataRightsManifest("geographic_constraints must be a tuple of strings")
    for item in value:
        _require_non_blank(item, "geographic_constraints entry")
    return value


def _canonical_hash(
    *,
    source_id: str,
    source_kind: DataSourceKind,
    license_identifier: str | None,
    license_url: str | None,
    retrieved_at: int | None,
    retention_seconds: int | None,
    derived_artifacts_allowed: bool,
    partner_display_allowed: bool,
    redistribution_allowed: bool,
    commercial_use_allowed: bool,
    geographic_constraints: tuple[str, ...],
    written_authorization_ref: str | None,
) -> str:
    canonical = json.dumps(
        {
            "commercial_use_allowed": commercial_use_allowed,
            "derived_artifacts_allowed": derived_artifacts_allowed,
            "geographic_constraints": sorted(geographic_constraints),
            "license_identifier": license_identifier,
            "license_url": license_url,
            "partner_display_allowed": partner_display_allowed,
            "redistribution_allowed": redistribution_allowed,
            "retention_seconds": retention_seconds,
            "retrieved_at": retrieved_at,
            "source_id": source_id,
            "source_kind": str(source_kind),
            "written_authorization_ref": written_authorization_ref,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode()).hexdigest()


def build_manifest(
    *,
    source_id: str,
    source_kind: str | DataSourceKind,
    license_identifier: str | None,
    license_url: str | None,
    retrieved_at: int | datetime | None,
    retention_seconds: int | None,
    derived_artifacts_allowed: bool = False,
    partner_display_allowed: bool = False,
    redistribution_allowed: bool = False,
    commercial_use_allowed: bool = False,
    geographic_constraints: tuple[str, ...] = (),
    written_authorization_ref: str | None = None,
) -> DataRightsManifest:
    """Validate fields and build an immutable manifest with a canonical SHA-256."""
    _require_non_blank(source_id, "source_id")
    kind = _normalize_source_kind(source_kind)
    if license_identifier is not None:
        _require_non_blank(license_identifier, "license_identifier")
    if license_url is not None:
        _require_non_blank(license_url, "license_url")
    epoch = _normalize_retrieved_at(retrieved_at)
    if retention_seconds is not None and (
        type(retention_seconds) is not int or retention_seconds < 0
    ):
        raise InvalidDataRightsManifest("retention_seconds must be a non-negative integer or None")
    for name, value in (
        ("derived_artifacts_allowed", derived_artifacts_allowed),
        ("partner_display_allowed", partner_display_allowed),
        ("redistribution_allowed", redistribution_allowed),
        ("commercial_use_allowed", commercial_use_allowed),
    ):
        if type(value) is not bool:
            raise InvalidDataRightsManifest(f"{name} must be a boolean")
    constraints = _normalize_constraints(geographic_constraints)
    if written_authorization_ref is not None:
        _require_non_blank(written_authorization_ref, "written_authorization_ref")

    manifest_hash = _canonical_hash(
        source_id=source_id,
        source_kind=kind,
        license_identifier=license_identifier,
        license_url=license_url,
        retrieved_at=epoch,
        retention_seconds=retention_seconds,
        derived_artifacts_allowed=derived_artifacts_allowed,
        partner_display_allowed=partner_display_allowed,
        redistribution_allowed=redistribution_allowed,
        commercial_use_allowed=commercial_use_allowed,
        geographic_constraints=constraints,
        written_authorization_ref=written_authorization_ref,
    )
    return DataRightsManifest(
        source_id=source_id,
        source_kind=kind,
        license_identifier=license_identifier,
        license_url=license_url,
        retrieved_at=epoch,
        retention_seconds=retention_seconds,
        derived_artifacts_allowed=derived_artifacts_allowed,
        partner_display_allowed=partner_display_allowed,
        redistribution_allowed=redistribution_allowed,
        commercial_use_allowed=commercial_use_allowed,
        geographic_constraints=constraints,
        written_authorization_ref=written_authorization_ref,
        manifest_hash=manifest_hash,
    )


def manifest_from_dict(data: Mapping[str, object]) -> DataRightsManifest:
    """Rebuild a manifest from a JSON-decoded mapping, recomputing the hash."""
    constraints = data.get("geographic_constraints", ())
    if constraints is None:
        constraints = ()
    if isinstance(constraints, list):
        constraints = tuple(constraints)

    return build_manifest(
        source_id=data["source_id"],  # type: ignore[arg-type]
        source_kind=data["source_kind"],  # type: ignore[arg-type]
        license_identifier=data.get("license_identifier"),  # type: ignore[arg-type]
        license_url=data.get("license_url"),  # type: ignore[arg-type]
        retrieved_at=data.get("retrieved_at"),  # type: ignore[arg-type]
        retention_seconds=data.get("retention_seconds"),  # type: ignore[arg-type]
        derived_artifacts_allowed=data.get("derived_artifacts_allowed", False),  # type: ignore[arg-type]
        partner_display_allowed=data.get("partner_display_allowed", False),  # type: ignore[arg-type]
        redistribution_allowed=data.get("redistribution_allowed", False),  # type: ignore[arg-type]
        commercial_use_allowed=data.get("commercial_use_allowed", False),  # type: ignore[arg-type]
        geographic_constraints=constraints,  # type: ignore[arg-type]
        written_authorization_ref=data.get("written_authorization_ref"),  # type: ignore[arg-type]
    )


def decide_persistent_use(
    manifest: DataRightsManifest,
    *,
    approved_authorization_refs: frozenset[str] = frozenset(),
    require_derived_artifacts: bool = False,
    require_partner_display: bool = False,
    require_redistribution: bool = False,
    require_commercial_use: bool = False,
) -> PersistentUseOutcome:
    """Decide whether persistent use is authorized, failing closed."""
    reasons: list[str] = []
    expected_hash = _canonical_hash(
        source_id=manifest.source_id,
        source_kind=manifest.source_kind,
        license_identifier=manifest.license_identifier,
        license_url=manifest.license_url,
        retrieved_at=manifest.retrieved_at,
        retention_seconds=manifest.retention_seconds,
        derived_artifacts_allowed=manifest.derived_artifacts_allowed,
        partner_display_allowed=manifest.partner_display_allowed,
        redistribution_allowed=manifest.redistribution_allowed,
        commercial_use_allowed=manifest.commercial_use_allowed,
        geographic_constraints=manifest.geographic_constraints,
        written_authorization_ref=manifest.written_authorization_ref,
    )
    if manifest.manifest_hash != expected_hash:
        reasons.append("manifest hash mismatch")
    if manifest.license_identifier is None and manifest.license_url is None:
        reasons.append("missing license")
    if manifest.retention_seconds is None:
        reasons.append("unspecified retention")
    elif manifest.retention_seconds == 0:
        reasons.append("no persistent retention allowed")
    if manifest.retrieved_at is None:
        reasons.append("missing retrieved-at")
    if manifest.source_kind is DataSourceKind.LICENSED_EXTERNAL and (
        manifest.written_authorization_ref is None
        or manifest.written_authorization_ref not in approved_authorization_refs
    ):
        reasons.append("external authorization is not in the approved registry")
    if (
        manifest.source_kind is DataSourceKind.LICENSED_EXTERNAL
        and manifest.source_id.strip().lower() == DERIV_SOURCE_ID
        and manifest.retention_seconds is not None
        and manifest.retention_seconds > 0
        and manifest.written_authorization_ref is None
    ):
        reasons.append("deriv persistent rights require written authorization")
    if require_derived_artifacts and not manifest.derived_artifacts_allowed:
        reasons.append("derived artifacts are not allowed")
    if require_partner_display and not manifest.partner_display_allowed:
        reasons.append("partner display is not allowed")
    if require_redistribution and not manifest.redistribution_allowed:
        reasons.append("redistribution is not allowed")
    if require_commercial_use and not manifest.commercial_use_allowed:
        reasons.append("commercial use is not allowed")
    if reasons:
        return PersistentUseOutcome(PersistentUseDecision.DENY, tuple(reasons))
    return PersistentUseOutcome(PersistentUseDecision.ALLOW, ())
