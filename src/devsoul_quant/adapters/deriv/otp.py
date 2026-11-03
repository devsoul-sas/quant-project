"""One-time-password (OTP) resolution for the Deriv demo WebSocket.

Implements the documented REST flow that produces the ephemeral demo WebSocket
URL without building it by hand:

1. ``GET /trading/v1/options/accounts`` -> list of Options accounts
   (``account_id`` + ``account_type``, where ``"demo"`` is a demo account).
2. Select a demo account (or take an explicit ``account_id``).
3. ``POST /trading/v1/options/accounts/{account_id}/otp`` -> ``data.url``.
4. Validate the returned URL (demo endpoint only, never ``/ws/real``).

The HTTP transport is injectable so the flow is testable without network access.
The default transport is stdlib ``urllib``; no extra dependency is required.
"""

from __future__ import annotations

import json as _json
import urllib.error
import urllib.request
from typing import Any, Protocol

from devsoul_quant.adapters.deriv.demo_url import validate_demo_websocket_url

API_BASE_URL = "https://api.derivws.com"
ACCOUNTS_PATH = "/trading/v1/options/accounts"


class DerivOtpError(RuntimeError):
    """Raised when the demo OTP flow cannot complete safely."""


class JsonResponse(Protocol):
    @property
    def status(self) -> int: ...

    def json(self) -> Any: ...


class OtpSession(Protocol):
    def get(self, url: str, *, headers: dict[str, str]) -> JsonResponse: ...

    def post(self, url: str, *, headers: dict[str, str], json: Any) -> JsonResponse: ...


class UrllibResponse:
    def __init__(self, raw: bytes, status: int) -> None:
        self._raw = raw
        self._status = status

    @property
    def status(self) -> int:
        return self._status

    def json(self) -> Any:
        return _json.loads(self._raw.decode("utf-8"))


class UrllibSession:
    """Minimal stdlib HTTP transport with an injectable ``urlopen`` for tests."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        urlopen: Any = urllib.request.urlopen,
    ) -> None:
        self._timeout = timeout
        self._urlopen = urlopen

    def get(self, url: str, *, headers: dict[str, str]) -> JsonResponse:
        request = urllib.request.Request(url, headers=headers, method="GET")
        return self._open(request)

    def post(self, url: str, *, headers: dict[str, str], json: Any) -> JsonResponse:
        merged = {**headers, "Content-Type": "application/json"}
        body = _json.dumps(json).encode("utf-8")
        request = urllib.request.Request(url, headers=merged, method="POST", data=body)
        return self._open(request)

    def _open(self, request: urllib.request.Request) -> JsonResponse:
        try:
            with self._urlopen(request, timeout=self._timeout) as response:
                return UrllibResponse(response.read(), response.status)
        except urllib.error.HTTPError as error:
            return UrllibResponse(error.read(), error.code)


def _auth_headers(token: str, app_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Deriv-App-ID": app_id}


def _accounts_url() -> str:
    return f"{API_BASE_URL}{ACCOUNTS_PATH}"


def list_accounts(session: OtpSession, *, token: str, app_id: str) -> list[dict[str, Any]]:
    response = session.get(_accounts_url(), headers=_auth_headers(token, app_id))
    if response.status != 200:
        raise DerivOtpError(f"get accounts returned HTTP {response.status}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise DerivOtpError("get accounts returned a non-object body")
    data = payload.get("data")
    if not isinstance(data, list):
        raise DerivOtpError("get accounts returned no account list")
    return [item for item in data if isinstance(item, dict)]


def request_otp(session: OtpSession, *, token: str, app_id: str, account_id: str) -> str:
    if not isinstance(account_id, str) or not account_id.strip():
        raise DerivOtpError("account_id must be a non-blank string")
    url = f"{_accounts_url()}/{account_id}/otp"
    response = session.post(url, headers=_auth_headers(token, app_id), json={})
    if response.status != 200:
        raise DerivOtpError(f"otp request returned HTTP {response.status}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise DerivOtpError("otp request returned a non-object body")
    data = payload.get("data")
    ws_url = data.get("url") if isinstance(data, dict) else None
    if not isinstance(ws_url, str) or not ws_url:
        raise DerivOtpError("otp response did not include a WebSocket url")
    return validate_demo_websocket_url(ws_url)


def resolve_demo_url(
    session: OtpSession,
    *,
    token: str,
    app_id: str,
    account_id: str | None = None,
) -> str:
    """Resolve a validated demo WebSocket URL from a PAT and optional account."""
    if not isinstance(token, str) or not token.strip():
        raise DerivOtpError("token must be a non-blank string")
    if not isinstance(app_id, str) or not app_id.strip():
        raise DerivOtpError("app_id must be a non-blank string")

    selected: Any = account_id
    if selected is None:
        accounts = list_accounts(session, token=token, app_id=app_id)
        demo = [item for item in accounts if item.get("account_type") == "demo"]
        if not demo:
            raise DerivOtpError("no demo Options account found")
        selected = demo[0].get("account_id")

    if not isinstance(selected, str) or not selected.strip():
        raise DerivOtpError("could not resolve a demo account_id")
    return request_otp(session, token=token, app_id=app_id, account_id=selected)
