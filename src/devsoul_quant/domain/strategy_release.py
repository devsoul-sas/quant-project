"""Immutable releases and bounded conclusions for ephemeral strategy sessions."""

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum

_MAX_CACHE_SECONDS = 86_400
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class InvalidStrategyRelease(ValueError):
    """Raised when a strategy release cannot be reproduced or bounded safely."""


class StrategyFamily(StrEnum):
    """Independent hypotheses supported by the ephemeral Deriv laboratory."""

    EVEN_ODD = "EVEN_ODD"
    MULTIPLIER = "MULTIPLIER"


class ResearchConclusion(StrEnum):
    """The complete set of conclusions an ephemeral session may emit."""

    NO_EDGE = "NO_EDGE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    PAPER_ELIGIBLE = "PAPER_ELIGIBLE"


@dataclass(frozen=True, slots=True)
class StrategyRelease:
    """Deterministic strategy identity without data or real-money authorization."""

    family: StrategyFamily
    specification_hash: str
    code_version: str
    risk_policy_hash: str
    ttl_seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.family, StrategyFamily):
            raise InvalidStrategyRelease("family must be a StrategyFamily")
        for field in ("specification_hash", "risk_policy_hash"):
            value = getattr(self, field)
            if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
                raise InvalidStrategyRelease(f"{field} must be a lowercase SHA-256 hash")
        if not isinstance(self.code_version, str) or not self.code_version.strip():
            raise InvalidStrategyRelease("code_version must be non-blank")
        if (
            type(self.ttl_seconds) is not int
            or self.ttl_seconds < 1
            or self.ttl_seconds >= _MAX_CACHE_SECONDS
        ):
            raise InvalidStrategyRelease("ttl_seconds must be an integer strictly below 24 hours")

    @property
    def release_id(self) -> str:
        """Return a stable hash of the complete release specification."""
        payload = json.dumps(
            {
                "code_version": self.code_version,
                "family": self.family.value,
                "risk_policy_hash": self.risk_policy_hash,
                "specification_hash": self.specification_hash,
                "ttl_seconds": self.ttl_seconds,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
