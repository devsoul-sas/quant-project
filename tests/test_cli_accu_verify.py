"""CLI coverage for the read-only ACCU verification command (S4.1)."""

from decimal import Decimal
from io import StringIO

import pytest

from devsoul_quant.cli import main


def test_accu_verify_dry_run_emits_a_classification() -> None:
    output = StringIO()
    code = main(["accu-verify", "--dry-run", "--history-count", "500"], stdout=output)

    rendered = output.getvalue()
    assert code == 0
    assert '"type": "final"' in rendered
    assert '"classification"' in rendered
    assert '"barrier_fraction"' in rendered
    assert '"observed_summary"' in rendered
    assert '"reconstructed_summary"' in rendered


def test_accu_verify_live_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_TOKEN", raising=False)
    monkeypatch.delenv("DEVSOUL_QUANT_DERIV_APP_ID", raising=False)
    output = StringIO()

    code = main(["accu-verify"], stdout=output)

    assert code == 2
    assert "demo credentials are not configured" in output.getvalue()


def test_accu_verify_live_runs_with_mocked_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from devsoul_quant.adapters.deriv.accu_proposal import AccumulatorProposal
    from devsoul_quant.adapters.deriv.history import HistoryResult

    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_TOKEN", "tok")
    monkeypatch.setenv("DEVSOUL_QUANT_DERIV_APP_ID", "app")

    def fake_propose(
        url: str, symbol: str, growth_rate: Decimal, stake: Decimal
    ) -> AccumulatorProposal:
        del url, stake
        return AccumulatorProposal(
            proposal_id="p",
            symbol=symbol,
            growth_rate=growth_rate,
            barrier_fraction=Decimal("0.0005"),
            barrier_percentage=Decimal("0.05"),
            high_barrier=Decimal("101"),
            low_barrier=Decimal("99"),
            barrier_spot_distance=Decimal("1"),
            spot=Decimal("100"),
            maximum_ticks=50,
            maximum_payout=Decimal("6000"),
            minimum_stake=Decimal("1"),
            maximum_stake=Decimal("1000"),
            ticks_stayed_in=(1, 2, 3),
        )

    def fake_fetch(
        resolve_url: object,
        symbol: str,
        *,
        total_count: int,
        cadence_seconds: int,
        deadline_remaining: float | None,
    ) -> HistoryResult:
        del resolve_url, symbol, total_count, cadence_seconds, deadline_remaining
        return HistoryResult(ticks=(), pages=0, discontinuities=0, ended_early=False)

    monkeypatch.setattr(
        "devsoul_quant.adapters.deriv.otp.resolve_demo_url",
        lambda *a, **k: "wss://api.derivws.com/trading/v1/options/ws/demo?otp=secret-otp",
    )
    monkeypatch.setattr(
        "devsoul_quant.adapters.deriv.accu_proposal.propose_accumulator", fake_propose
    )
    monkeypatch.setattr("devsoul_quant.adapters.deriv.history.fetch_ticks_history", fake_fetch)

    output = StringIO()
    code = main(
        ["accu-verify", "--max-proposals", "1", "--history-count", "10", "--session-seconds", "60"],
        stdout=output,
    )

    assert code == 0
    assert '"classification"' in output.getvalue()
    assert '"proposals": 1' in output.getvalue()
