"""OTP resolution flow tests (offline, with a fake HTTP session)."""

import io
import urllib.error
from email.message import Message
from typing import Any

import pytest

from devsoul_quant.adapters.deriv.demo_url import UnsafeDerivUrl
from devsoul_quant.adapters.deriv.otp import (
    ACCOUNTS_PATH,
    API_BASE_URL,
    DerivOtpError,
    UrllibResponse,
    UrllibSession,
    list_accounts,
    request_otp,
    resolve_demo_url,
)

DEMO_URL = "wss://api.derivws.com/trading/v1/options/ws/demo?otp=abc123"
TOKEN = "pat-token"
APP_ID = "12345"


class FakeResponse:
    def __init__(self, status: int = 200, payload: Any = None) -> None:
        self._status = status
        self._payload = payload

    @property
    def status(self) -> int:
        return self._status

    def json(self) -> Any:
        return self._payload


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str], Any]] = []
        self.get_response = FakeResponse(payload={"data": []})
        self.post_response = FakeResponse(payload={"data": {"url": DEMO_URL}})

    def get(self, url: str, *, headers: dict[str, str]) -> FakeResponse:
        self.calls.append(("GET", url, headers, None))
        return self.get_response

    def post(self, url: str, *, headers: dict[str, str], json: Any) -> FakeResponse:
        self.calls.append(("POST", url, headers, json))
        return self.post_response


def test_list_accounts_sends_bearer_and_app_id_headers() -> None:
    session = FakeSession()
    session.get_response = FakeResponse(
        payload={"data": [{"account_id": "DOT1", "account_type": "demo"}]}
    )

    accounts = list_accounts(session, token=TOKEN, app_id=APP_ID)

    assert accounts == [{"account_id": "DOT1", "account_type": "demo"}]
    method, url, headers, _ = session.calls[0]
    assert method == "GET"
    assert url == f"{API_BASE_URL}{ACCOUNTS_PATH}"
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert headers["Deriv-App-ID"] == APP_ID


def test_list_accounts_raises_on_http_error() -> None:
    session = FakeSession()
    session.get_response = FakeResponse(status=401, payload={"errors": []})

    with pytest.raises(DerivOtpError, match="401"):
        list_accounts(session, token=TOKEN, app_id=APP_ID)


def test_list_accounts_raises_when_data_is_not_a_list() -> None:
    session = FakeSession()
    session.get_response = FakeResponse(payload={"data": {}})

    with pytest.raises(DerivOtpError, match="no account list"):
        list_accounts(session, token=TOKEN, app_id=APP_ID)


def test_request_otp_posts_to_the_account_endpoint_and_validates_url() -> None:
    session = FakeSession()

    url = request_otp(session, token=TOKEN, app_id=APP_ID, account_id="DOT1")

    assert url == DEMO_URL
    method, path, headers, body = session.calls[0]
    assert method == "POST"
    assert path == f"{API_BASE_URL}{ACCOUNTS_PATH}/DOT1/otp"
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert body == {}


def test_request_otp_rejects_the_real_money_url() -> None:
    session = FakeSession()
    session.post_response = FakeResponse(
        payload={"data": {"url": "wss://api.derivws.com/trading/v1/options/ws/real?otp=x"}}
    )

    with pytest.raises(UnsafeDerivUrl):
        request_otp(session, token=TOKEN, app_id=APP_ID, account_id="DOT1")


def test_request_otp_raises_when_url_is_missing() -> None:
    session = FakeSession()
    session.post_response = FakeResponse(payload={"data": {}})

    with pytest.raises(DerivOtpError, match="did not include"):
        request_otp(session, token=TOKEN, app_id=APP_ID, account_id="DOT1")


def test_request_otp_rejects_a_blank_account_id() -> None:
    session = FakeSession()

    with pytest.raises(DerivOtpError, match="account_id"):
        request_otp(session, token=TOKEN, app_id=APP_ID, account_id="  ")


def test_resolve_demo_url_selects_a_demo_account() -> None:
    session = FakeSession()
    session.get_response = FakeResponse(
        payload={
            "data": [
                {"account_id": "DOT_REAL", "account_type": "real"},
                {"account_id": "DOT_DEMO", "account_type": "demo"},
            ]
        }
    )

    url = resolve_demo_url(session, token=TOKEN, app_id=APP_ID)

    assert url == DEMO_URL
    # list accounts, then request otp for the demo account
    assert session.calls[0][0] == "GET"
    assert session.calls[1][1].endswith("/DOT_DEMO/otp")


def test_resolve_demo_url_raises_without_a_demo_account() -> None:
    session = FakeSession()
    session.get_response = FakeResponse(
        payload={"data": [{"account_id": "DOT_REAL", "account_type": "real"}]}
    )

    with pytest.raises(DerivOtpError, match="no demo"):
        resolve_demo_url(session, token=TOKEN, app_id=APP_ID)


def test_resolve_demo_url_skips_listing_with_an_explicit_account() -> None:
    session = FakeSession()

    url = resolve_demo_url(session, token=TOKEN, app_id=APP_ID, account_id="DOT9")

    assert url == DEMO_URL
    assert session.calls[0][0] == "POST"
    assert session.calls[0][1].endswith("/DOT9/otp")


@pytest.mark.parametrize(("token", "app_id"), [("   ", APP_ID), (TOKEN, "")])
def test_resolve_demo_url_rejects_blank_credentials(token: str, app_id: str) -> None:
    session = FakeSession()

    with pytest.raises(DerivOtpError):
        resolve_demo_url(session, token=token, app_id=app_id)


class FakeUrlOpen:
    def __init__(self, raw: bytes, status: int = 200) -> None:
        self._raw = raw
        self._status = status
        self.request: Any = None
        self.timeout: float | None = None

    def __call__(self, request: Any, timeout: float) -> "FakeUrlOpen":
        self.request = request
        self.timeout = timeout
        return self

    def __enter__(self) -> "FakeUrlOpen":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._raw

    @property
    def status(self) -> int:
        return self._status


def test_urllib_session_get_builds_a_get_request() -> None:
    urlopen = FakeUrlOpen(b'{"data": []}')
    session = UrllibSession(urlopen=urlopen)

    response = session.get("https://example.com/accounts", headers={"Authorization": "Bearer x"})

    assert urlopen.request.method == "GET"
    assert urlopen.request.get_header("Authorization") == "Bearer x"
    assert isinstance(response, UrllibResponse)
    assert response.json() == {"data": []}


def test_urllib_session_post_sends_json_body_and_content_type() -> None:
    urlopen = FakeUrlOpen(b"{}")
    session = UrllibSession(urlopen=urlopen)

    session.post(
        "https://example.com/otp",
        headers={"Deriv-App-ID": "1"},
        json={"otp": 1},
    )

    assert urlopen.request.method == "POST"
    assert urlopen.request.get_header("Content-type") == "application/json"
    assert urlopen.request.data == b'{"otp": 1}'


def test_urllib_session_captures_http_errors_as_responses() -> None:
    error = urllib.error.HTTPError(
        "https://example.com", 401, "Unauthorized", Message(), io.BytesIO(b'{"errors":[]}')
    )

    class RaisingOpen(FakeUrlOpen):
        def __call__(self, request: Any, timeout: float) -> Any:
            raise error

    session = UrllibSession(urlopen=RaisingOpen(b"{}"))

    response = session.get("https://example.com/accounts", headers={})

    assert response.status == 401
    assert response.json() == {"errors": []}
