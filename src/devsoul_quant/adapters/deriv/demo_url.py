"""Validation for OTP WebSocket URLs returned by Deriv."""

from urllib.parse import parse_qs, urlsplit


class UnsafeDerivUrl(ValueError):
    """Raised when an OTP URL could enable unsafe execution."""


def validate_demo_websocket_url(url: str) -> str:
    """Accept only the official TLS demo endpoint with one non-empty OTP."""
    if url != url.strip() or any(ord(character) < 32 or ord(character) == 127 for character in url):
        raise UnsafeDerivUrl("invalid Deriv demo WebSocket URL")

    try:
        parsed = urlsplit(url)
        port = parsed.port
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as error:
        raise UnsafeDerivUrl("invalid Deriv demo WebSocket URL") from error

    if parsed.path == "/trading/v1/options/ws/real":
        raise UnsafeDerivUrl("real-money WebSocket URL is forbidden")

    otp_values = query.get("otp", [])
    otp = otp_values[0] if len(otp_values) == 1 else ""
    valid_otp = (
        set(query) == {"otp"}
        and bool(otp)
        and otp == otp.strip()
        and not any(
            character.isspace() or ord(character) < 32 or ord(character) == 127 for character in otp
        )
    )
    valid_endpoint = (
        parsed.scheme == "wss"
        and parsed.netloc == "api.derivws.com"
        and port is None
        and parsed.username is None
        and parsed.password is None
        and parsed.path == "/trading/v1/options/ws/demo"
        and not parsed.fragment
    )
    if not valid_endpoint or not valid_otp:
        raise UnsafeDerivUrl("invalid Deriv demo WebSocket URL")

    return url
