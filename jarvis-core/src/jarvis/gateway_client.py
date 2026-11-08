"""Core's only network code: requests to the local gateway, which owns the internet."""
import os
from urllib.parse import urlsplit

import httpx

from jarvis import config


class GatewayError(Exception):
    def __init__(self, kind: str, status: int = 0) -> None:
        super().__init__(kind)
        self.kind, self.status = kind, status


def token() -> str:
    return os.environ.get(config.TOKEN_ENV, "").strip()


def base_url() -> str:
    return f"http://{config.LOCALHOST}:{config.GATEWAY_PORT}"


def _check_local(url: str) -> None:
    host = urlsplit(url).hostname
    if host not in ("127.0.0.1", "localhost"):
        raise GatewayError("not local")


def post(path: str, timeout: float, json: dict | None = None) -> httpx.Response:
    """POST to the gateway. Raises GatewayError with kind: offline, busy, setup, notfound, upstream,
    bad."""
    secret = token()
    if not secret:
        raise GatewayError("setup")
    url = base_url() + path
    _check_local(url)
    try:
        response = httpx.post(url, json=json, timeout=timeout, follow_redirects=False,
                              headers={config.TOKEN_HEADER: secret})
    except httpx.HTTPError:
        raise GatewayError("offline") from None
    if response.status_code == 200:
        return response
    kind = {401: "setup", 403: "setup", 404: "notfound", 413: "toolong", 429: "busy",
            503: "setup", 502: "upstream", 504: "upstream"}.get(response.status_code, "bad")
    raise GatewayError(kind, response.status_code)


def post_event(state: str, text: str) -> None:
    """Best effort: the browser UI is optional, so a missing gateway changes nothing here."""
    try:
        post("/events", timeout=0.5, json={"state": state, "text": text})
    except GatewayError:
        pass
