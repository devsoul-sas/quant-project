"""Provider-independent risk gate for synthetic and demo decisions."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from devsoul_quant.domain.contracts import ContractIntent, EnterContractIntent, NoTradeIntent


class InvalidRiskPolicy(ValueError):
    """Raised when a risk policy cannot fail safely."""


class RiskDisposition(StrEnum):
    """Outcome of evaluating a contract intent."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NO_ACTION = "NO_ACTION"


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Immutable explanation produced by the risk gate."""

    disposition: RiskDisposition
    reason: str
    intent: ContractIntent


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """Fail-closed stake and kill-switch policy with an explicit switch."""

    max_amount_per_contract: Decimal
    kill_switch_enabled: bool

    def __post_init__(self) -> None:
        amount = self.max_amount_per_contract
        if not isinstance(amount, Decimal) or not amount.is_finite() or amount <= 0:
            raise InvalidRiskPolicy("max_amount_per_contract must be a positive finite Decimal")
        if type(self.kill_switch_enabled) is not bool:
            raise InvalidRiskPolicy("kill_switch_enabled must be a boolean")

    def evaluate(self, intent: ContractIntent) -> RiskDecision:
        """Approve only supported entries that satisfy every active limit."""
        if isinstance(intent, NoTradeIntent):
            return RiskDecision(RiskDisposition.NO_ACTION, "strategy selected no trade", intent)
        if not isinstance(intent, EnterContractIntent):
            return RiskDecision(
                RiskDisposition.REJECTED,
                "unsupported contract lifecycle action",
                intent,
            )
        if self.kill_switch_enabled:
            return RiskDecision(RiskDisposition.REJECTED, "risk kill switch is enabled", intent)
        if intent.amount_requested > self.max_amount_per_contract:
            return RiskDecision(
                RiskDisposition.REJECTED,
                "requested amount exceeds risk limit",
                intent,
            )
        return RiskDecision(
            RiskDisposition.APPROVED,
            "entry is within synthetic risk limits",
            intent,
        )
