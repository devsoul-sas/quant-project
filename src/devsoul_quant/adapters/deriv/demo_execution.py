"""Ephemeral synchronous adapter for one Deriv demo contract lifecycle.

Every operation validates a ``/ws/demo`` OTP URL, opens a bounded connection,
keeps provider payloads only in local variables, and returns minimal domain data.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from devsoul_quant.adapters.deriv.demo_url import validate_demo_websocket_url
from devsoul_quant.application.demo_execution import DemoProposal, DemoSettlement
from devsoul_quant.application.multiplier_lab import (
    ContractAvailability,
    MarketSymbol,
    MultiplierProposal,
)
from devsoul_quant.domain.contracts import EnterContractIntent
from devsoul_quant.domain.multiplier import MultiplierIntent


class DerivDemoExecutionError(RuntimeError):
    """Sanitized demo transport or provider failure."""


def _default_connect(url: str) -> Any:
    from websockets.sync.client import connect

    return connect(url)


def _decimal(value: object, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DerivDemoExecutionError(f"Deriv returned an invalid {field}") from None
    if not result.is_finite():
        raise DerivDemoExecutionError(f"Deriv returned an invalid {field}")
    return result


def _json_number(value: Decimal, field: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise DerivDemoExecutionError(f"{field} is outside the provider numeric range")
    return result


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DerivDemoExecutionError(f"Deriv response is missing {field}")
    return value


def _contract_id(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value
    if type(value) is int and value > 0:
        return str(value)
    raise DerivDemoExecutionError("Deriv response is missing contract_id")


class DerivDemoExecutionGateway:
    """Demo-only execution port; never accepts or constructs a real endpoint."""

    account_type = "demo"

    def __init__(
        self,
        url: str,
        *,
        connect: Callable[[str], Any] | None = None,
        settlement_timeout_seconds: float = 3600.0,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        validate_demo_websocket_url(url)
        try:
            timeout = float(settlement_timeout_seconds)
        except (OverflowError, TypeError, ValueError):
            timeout = math.nan
        if isinstance(settlement_timeout_seconds, bool) or not (
            math.isfinite(timeout) and 0 < timeout <= 23 * 3600
        ):
            raise DerivDemoExecutionError(
                "settlement timeout must be positive and no greater than 23 hours"
            )
        self._url = url
        self._connect = connect if connect is not None else _default_connect
        self._settlement_timeout_seconds = timeout
        self._monotonic = monotonic
        self._connection: Any | None = None
        self._socket: Any | None = None

    def __enter__(self) -> DerivDemoExecutionGateway:
        if self._socket is not None:
            raise DerivDemoExecutionError("Deriv demo connection is already open")
        try:
            connection = self._connect(self._url)
            self._connection = connection
            self._socket = connection.__enter__()
        except Exception as error:
            self._connection = None
            self._socket = None
            raise DerivDemoExecutionError("Deriv demo connection failed") from error
        return self

    def __exit__(self, *exc_info: object) -> bool:
        connection = self._connection
        self._socket = None
        self._connection = None
        if connection is not None:
            return bool(connection.__exit__(*exc_info))
        return False

    @staticmethod
    def _decode(raw: object) -> Mapping[str, Any]:
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            message = json.loads(raw)  # type: ignore[arg-type]
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            raise DerivDemoExecutionError("Deriv returned an invalid response") from None
        result = _mapping(message, "response object")
        if "error" in result:
            raise DerivDemoExecutionError("Deriv rejected the demo request")
        return result

    def _request(self, payload: Mapping[str, object]) -> Mapping[str, Any]:
        try:
            if self._socket is not None:
                self._socket.send(json.dumps(payload, separators=(",", ":"), sort_keys=True))
                return self._decode(self._socket.recv(timeout=30))
            with self._connect(self._url) as websocket:
                websocket.send(json.dumps(payload, separators=(",", ":"), sort_keys=True))
                return self._decode(websocket.recv(timeout=30))
        except DerivDemoExecutionError:
            raise
        except Exception as error:
            raise DerivDemoExecutionError("Deriv demo connection failed") from error

    def _available_contract_payload(self, symbol: str) -> list[object]:
        if not isinstance(symbol, str) or not symbol.strip():
            raise DerivDemoExecutionError("symbol must be a non-blank string")
        message = self._request({"contracts_for": symbol, "req_id": 6})
        contracts_for = _mapping(message.get("contracts_for"), "contracts_for")
        available = contracts_for.get("available")
        if not isinstance(available, list):
            raise DerivDemoExecutionError("Deriv response has invalid available contracts")
        return available

    def available_contract_types(self, symbol: str) -> frozenset[str]:
        """Discover contract families instead of assuming symbol compatibility."""
        contract_types: set[str] = set()
        for contract in self._available_contract_payload(symbol):
            item = _mapping(contract, "available contract")
            contract_type = item.get("contract_type")
            if not isinstance(contract_type, str) or not contract_type:
                raise DerivDemoExecutionError("Deriv response has invalid contract_type")
            contract_types.add(contract_type)
        return frozenset(contract_types)

    def available_contracts(self, symbol: str) -> tuple[ContractAvailability, ...]:
        """Preserve constraints needed to validate Multiplier proposals."""
        constraints: list[ContractAvailability] = []
        for contract in self._available_contract_payload(symbol):
            item = _mapping(contract, "available contract")
            contract_type = item.get("contract_type")
            if contract_type not in ("MULTUP", "MULTDOWN"):
                continue
            expiry_type = item.get("expiry_type")
            barriers = item.get("barriers")
            multiplier_range = item.get("multiplier_range")
            if not isinstance(expiry_type, str) or not expiry_type:
                raise DerivDemoExecutionError("Deriv response has invalid expiry_type")
            if type(barriers) is not int or barriers < 0:
                raise DerivDemoExecutionError("Deriv response has invalid barriers")
            if not isinstance(multiplier_range, list) or not multiplier_range:
                raise DerivDemoExecutionError("Deriv response has invalid multiplier_range")
            parsed_range = tuple(_decimal(value, "multiplier_range") for value in multiplier_range)
            if any(value <= 0 for value in parsed_range):
                raise DerivDemoExecutionError("Deriv response has invalid multiplier_range")
            constraints.append(
                ContractAvailability(
                    contract_type=contract_type,
                    expiry_type=expiry_type,
                    barriers=barriers,
                    multiplier_range=parsed_range,
                )
            )
        return tuple(constraints)

    def active_symbols(self) -> tuple[MarketSymbol, ...]:
        """Return minimal active symbol identities without retaining provider payloads."""
        message = self._request({"active_symbols": "brief", "req_id": 7})
        payload = message.get("active_symbols")
        if not isinstance(payload, list):
            raise DerivDemoExecutionError("Deriv response has invalid active_symbols")
        symbols: list[MarketSymbol] = []
        for raw_symbol in payload:
            item = _mapping(raw_symbol, "active symbol")
            symbol = item.get("underlying_symbol")
            name = item.get("underlying_symbol_name")
            if not isinstance(symbol, str) or not symbol:
                raise DerivDemoExecutionError("Deriv response has invalid symbol code")
            if not isinstance(name, str) or not name:
                raise DerivDemoExecutionError("Deriv response has invalid symbol name")
            symbols.append(MarketSymbol(symbol=symbol, name=name))
        return tuple(symbols)

    def propose_multiplier(self, intent: MultiplierIntent) -> MultiplierProposal:
        """Observe Multiplier economics without purchasing the proposal."""
        message = self._request(
            {
                "proposal": 1,
                "amount": _json_number(intent.stake, "stake"),
                "basis": "stake",
                "contract_type": intent.contract_type.value,
                "currency": "USD",
                "multiplier": _json_number(intent.multiplier, "multiplier"),
                "limit_order": {
                    "stop_loss": _json_number(intent.stop_loss, "stop_loss"),
                    "take_profit": _json_number(intent.take_profit, "take_profit"),
                },
                "underlying_symbol": intent.symbol,
                "req_id": 8,
            }
        )
        payload = _mapping(message.get("proposal"), "proposal")
        proposal_id = payload.get("id")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise DerivDemoExecutionError("Deriv proposal has invalid id")
        return MultiplierProposal(
            proposal_id=proposal_id,
            ask_price=_decimal(payload.get("ask_price"), "ask_price"),
            spot=_decimal(payload.get("spot"), "spot"),
            commission_percent=_decimal(payload.get("commission"), "commission"),
        )

    def propose(self, intent: EnterContractIntent) -> DemoProposal:
        payload: dict[str, object] = {
            "proposal": 1,
            "amount": _json_number(intent.amount_requested, "amount"),
            "basis": intent.basis.value,
            "contract_type": intent.contract_type.value,
            "currency": intent.currency,
            "duration": intent.duration,
            "duration_unit": intent.duration_unit.value,
            "underlying_symbol": intent.symbol,
            "req_id": 1,
        }
        if intent.barrier is not None:
            payload["barrier"] = str(intent.barrier)
        message = self._request(payload)
        proposal = _mapping(message.get("proposal"), "proposal")
        identifier = proposal.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise DerivDemoExecutionError("Deriv response is missing proposal id")
        return DemoProposal(
            proposal_id=identifier,
            ask_price=_decimal(proposal.get("ask_price"), "ask_price"),
            payout=_decimal(proposal.get("payout"), "payout"),
        )

    def buy(self, proposal: DemoProposal) -> str:
        message = self._request(
            {
                "buy": proposal.proposal_id,
                "price": _json_number(proposal.ask_price, "price"),
                "req_id": 2,
            }
        )
        buy = _mapping(message.get("buy"), "buy")
        return _contract_id(buy.get("contract_id"))

    def await_settlement(self, contract_id: str) -> DemoSettlement:
        try:
            request_contract_id: str | int = int(contract_id)
        except ValueError:
            request_contract_id = contract_id

        def wait(websocket: Any) -> DemoSettlement:
            subscription_id: str | None = None
            deadline = self._monotonic() + self._settlement_timeout_seconds
            websocket.send(
                json.dumps(
                    {
                        "proposal_open_contract": 1,
                        "contract_id": request_contract_id,
                        "subscribe": 1,
                        "req_id": 3,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            try:
                while True:
                    remaining = deadline - self._monotonic()
                    if remaining <= 0:
                        raise DerivDemoExecutionError("demo settlement deadline expired")
                    message = self._decode(websocket.recv(timeout=remaining))
                    subscription = message.get("subscription")
                    if isinstance(subscription, Mapping):
                        candidate = subscription.get("id")
                        if isinstance(candidate, str) and candidate:
                            subscription_id = candidate
                    lifecycle = _mapping(
                        message.get("proposal_open_contract"), "proposal_open_contract"
                    )
                    if lifecycle.get("is_sold") in (1, True):
                        return DemoSettlement(
                            contract_id=_contract_id(lifecycle.get("contract_id")),
                            profit=_decimal(lifecycle.get("profit"), "profit"),
                        )
            finally:
                if subscription_id is not None:
                    websocket.send(json.dumps({"forget": subscription_id, "req_id": 4}))

        try:
            if self._socket is not None:
                return wait(self._socket)
            with self._connect(self._url) as websocket:
                return wait(websocket)
        except DerivDemoExecutionError:
            raise
        except Exception as error:
            raise DerivDemoExecutionError("Deriv demo settlement failed") from error

    def reconcile(self) -> tuple[str, ...]:
        message = self._request({"portfolio": 1, "req_id": 5})
        portfolio = _mapping(message.get("portfolio"), "portfolio")
        contracts = portfolio.get("contracts", [])
        if not isinstance(contracts, list):
            raise DerivDemoExecutionError("Deriv response has invalid portfolio contracts")
        identifiers: list[str] = []
        for contract in contracts:
            item = _mapping(contract, "portfolio contract")
            identifiers.append(_contract_id(item.get("contract_id")))
        return tuple(identifiers)
