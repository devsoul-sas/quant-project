"""Read-only ACCU proposal adapter for the Deriv demo WebSocket.

Observes one accumulator proposal (``contract_type="ACCU"``) and returns the
barrier, counter and validation fields needed to reconstruct streaks. It never
constructs a ``buy`` or ``sell`` payload, so the proposal is observation only.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from devsoul_quant.adapters.deriv.demo_url import validate_demo_websocket_url

DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0


class ProposalError(RuntimeError):
    """Raised when an ACCU proposal cannot be obtained safely."""


def _default_connect(url: str) -> Any:
    from websockets.sync.client import connect

    return connect(url)


@dataclass(frozen=True, slots=True)
class AccumulatorProposal:
    """Sanitized, read-only observation of one ACCU proposal."""

    proposal_id: str
    symbol: str
    growth_rate: Decimal
    barrier_fraction: Decimal
    barrier_percentage: Decimal
    high_barrier: Decimal
    low_barrier: Decimal
    barrier_spot_distance: Decimal
    spot: Decimal
    maximum_ticks: int
    maximum_payout: Decimal
    minimum_stake: Decimal
    maximum_stake: Decimal
    ticks_stayed_in: tuple[int, ...]


def _decimal(value: object, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ProposalError(f"Deriv returned an invalid {field}") from None
    if not result.is_finite():
        raise ProposalError(f"Deriv returned an invalid {field}")
    return result


def _percentage(value: object, field: str) -> Decimal:
    text = str(value).strip()
    if text.endswith("%"):
        text = text[:-1].strip()
    result = _decimal(text, field)
    if result < 0:
        raise ProposalError(f"Deriv returned an invalid {field}")
    return result


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProposalError(f"Deriv response is missing {field}")
    return value


def _decode(raw: object) -> Mapping[str, Any]:
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        message = json.loads(raw)  # type: ignore[arg-type]
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        raise ProposalError("Deriv returned an invalid response") from None
    if not isinstance(message, Mapping):
        raise ProposalError("Deriv returned a non-object response")
    return message


def _json_number(value: Decimal, field: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ProposalError(f"{field} must be a positive finite number")
    return result


def propose_accumulator(
    url: str,
    symbol: str,
    *,
    growth_rate: Decimal,
    stake: Decimal,
    connect: Callable[[str], Any] | None = None,
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
) -> AccumulatorProposal:
    """Observe one ACCU proposal for ``symbol`` without purchasing it."""
    validate_demo_websocket_url(url)
    if not isinstance(symbol, str) or not symbol.strip():
        raise ProposalError("symbol must be a non-blank string")
    if (
        not isinstance(growth_rate, Decimal)
        or not growth_rate.is_finite()
        or growth_rate <= 0
        or growth_rate >= Decimal("1")
    ):
        raise ProposalError("growth_rate must be a positive fraction below 1")
    if not isinstance(stake, Decimal) or not stake.is_finite() or stake <= 0:
        raise ProposalError("stake must be a positive finite Decimal")
    connector = connect if connect is not None else _default_connect
    deadline = monotonic() + float(request_timeout_seconds)
    payload = {
        "proposal": 1,
        "amount": _json_number(stake, "stake"),
        "basis": "stake",
        "contract_type": "ACCU",
        "currency": "USD",
        "growth_rate": _json_number(growth_rate, "growth_rate"),
        "underlying_symbol": symbol,
        "req_id": 1,
    }
    try:
        with connector(url) as websocket:
            websocket.send(json.dumps(payload, separators=(",", ":"), sort_keys=True))
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise ProposalError("ACCU proposal request deadline expired")
                message = _decode(websocket.recv(timeout=remaining))
                if "error" in message:
                    raise ProposalError("Deriv rejected the ACCU proposal")
                if "proposal" not in message:
                    continue
                proposal = _mapping(message.get("proposal"), "proposal")
                identifier = proposal.get("id")
                if not isinstance(identifier, str) or not identifier:
                    raise ProposalError("Deriv proposal is missing an id")
                details = _mapping(proposal.get("contract_details"), "contract_details")
                stayed = details.get("ticks_stayed_in")
                if not isinstance(stayed, list) or not stayed:
                    raise ProposalError("Deriv proposal is missing ticks_stayed_in")
                if any(type(value) is not int or value < 0 for value in stayed):
                    raise ProposalError("Deriv ticks_stayed_in contains invalid entries")
                maximum_ticks = details.get("maximum_ticks")
                if type(maximum_ticks) is not int or maximum_ticks < 1:
                    raise ProposalError("Deriv proposal is missing maximum_ticks")
                return AccumulatorProposal(
                    proposal_id=identifier,
                    symbol=symbol,
                    growth_rate=growth_rate,
                    barrier_fraction=_decimal(
                        details.get("tick_size_barrier"), "tick_size_barrier"
                    ),
                    barrier_percentage=_percentage(
                        details.get("tick_size_barrier_percentage"), "tick_size_barrier_percentage"
                    ),
                    high_barrier=_decimal(details.get("high_barrier"), "high_barrier"),
                    low_barrier=_decimal(details.get("low_barrier"), "low_barrier"),
                    barrier_spot_distance=_decimal(
                        details.get("barrier_spot_distance"), "barrier_spot_distance"
                    ),
                    spot=_decimal(proposal.get("spot"), "spot"),
                    maximum_ticks=maximum_ticks,
                    maximum_payout=_decimal(details.get("maximum_payout"), "maximum_payout"),
                    minimum_stake=_decimal(details.get("minimum_stake"), "minimum_stake"),
                    maximum_stake=_decimal(details.get("maximum_stake"), "maximum_stake"),
                    ticks_stayed_in=tuple(stayed),
                )
    except ProposalError:
        raise
    except Exception:
        raise ProposalError("demo websocket failed") from None
