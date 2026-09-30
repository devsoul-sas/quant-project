import pytest

from devsoul_quant.adapters.deriv.demo_url import UnsafeDerivUrl, validate_demo_websocket_url


def test_real_websocket_url_is_rejected() -> None:
    url = "wss://api.derivws.com/trading/v1/options/ws/real?otp=one-time-token"

    with pytest.raises(UnsafeDerivUrl, match="real-money WebSocket URL is forbidden"):
        validate_demo_websocket_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "ws://api.derivws.com/trading/v1/options/ws/demo?otp=token",
        "wss://api.derivws.com.evil.test/trading/v1/options/ws/demo?otp=token",
        "wss://user@api.derivws.com/trading/v1/options/ws/demo?otp=token",
        "wss://api.derivws.com/trading/v1/options/ws/public?otp=token",
        "wss://api.derivws.com/trading/v1/options/ws/demo",
        "wss://api.derivws.com/trading/v1/options/ws/demo?otp=",
        "wss://api.derivws.com/trading/v1/options/ws/demo?otp=one&otp=two",
        "wss://api.derivws.com/trading/v1/options/ws/demo?otp=token#fragment",
        " wss://api.derivws.com/trading/v1/options/ws/demo?otp=token",
        "wss://api.derivws.com/trading/v1/options/ws/demo?otp=token\n",
        "wss://api.derivws.com/trading/v1/options/ws/demo?otp=%20",
        "wss://api.derivws.com/trading/v1/options/ws/demo?otp=%0d%0aX-Test:yes",
        "wss://API.DERIVWS.COM/trading/v1/options/ws/demo?otp=token",
    ],
)
def test_non_official_demo_websocket_url_is_rejected(url: str) -> None:
    with pytest.raises(UnsafeDerivUrl, match="invalid Deriv demo WebSocket URL"):
        validate_demo_websocket_url(url)


def test_official_demo_websocket_url_is_accepted() -> None:
    url = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=one-time-token"

    assert validate_demo_websocket_url(url) == url
