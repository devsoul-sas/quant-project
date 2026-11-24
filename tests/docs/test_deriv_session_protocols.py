"""Integrity tests for preregistered ephemeral Deriv session protocols."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVEN_ODD = REPO_ROOT / "docs" / "research" / "deriv-even-odd-session-protocol.md"
MULTIPLIERS = REPO_ROOT / "docs" / "research" / "deriv-multiplier-session-protocol.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_even_odd_protocol_freezes_causal_ephemeral_economics() -> None:
    assert EVEN_ODD.is_file()
    text = _read(EVEN_ODD)

    assert "Volatility 10 estándar" in text
    assert "active_symbols" in text and "contracts_for" in text
    assert "pip_size" in text
    assert "50/50" in text
    assert "DIGITEVEN" in text and "DIGITODD" in text
    assert "ask_price / payout" in text
    assert "warm-up" in text and "forward" in text
    assert "Wilson" in text
    assert "Bonferroni" in text
    assert "NO_TRADE" in text
    assert "martingala" in text.lower()


def test_multiplier_protocol_freezes_runtime_market_and_complete_costs() -> None:
    assert MULTIPLIERS.is_file()
    text = _read(MULTIPLIERS)

    assert "Drift Switching" in text
    assert "Volatility 10 estándar" in text
    assert "active_symbols" in text and "contracts_for" in text
    assert "MULTUP" in text and "MULTDOWN" in text
    assert "no_expiry" in text
    assert "multiplier_range" in text
    assert "comisión" in text and "slippage" in text and "latencia" in text
    assert "stop-out" in text
    assert "ESTIMATED" in text
    assert "NO_TRADE" in text
    assert "martingala" in text.lower()


def test_both_protocols_are_session_local_and_never_authorize_real_money() -> None:
    for path in (EVEN_ODD, MULTIPLIERS):
        text = _read(path)
        normalized = text.lower()

        assert "ttl estricto menor de 24 horas" in normalized
        assert "cada sesión comienza sin estado" in normalized
        assert "ninguna sesión aprende de una sesión anterior" in normalized
        assert "no se persiste" in normalized
        assert "NO_EDGE" in text
        assert "INSUFFICIENT_EVIDENCE" in text
        assert "PAPER_ELIGIBLE" in text
        assert "real_money = EXCLUDED" in text
