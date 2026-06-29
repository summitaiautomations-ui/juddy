"""eBay OAuth: one-time browser flow + refresh-token-backed access tokens.

State file: discs/.ebay_state.json (gitignored). Stores refresh_token (long
lived, ~18 months), most recent access_token + expiry, business policy IDs,
merchant location key, and ZIP code.
"""

import base64
import json
import os
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass, field, asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

STATE_PATH = Path(__file__).resolve().parent.parent / ".ebay_state.json"
OAUTH_BASE = "https://api.ebay.com/identity/v1/oauth2/token"
CONSENT_BASE = "https://auth.ebay.com/oauth2/authorize"

# Scopes required for the full flow (inventory + offers + account).
SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.marketing",
]

CALLBACK_HOST = "localhost"
CALLBACK_PORT = 8765
CALLBACK_PATH = "/callback"


@dataclass
class EbayState:
    refresh_token: str = ""
    access_token: str = ""
    access_token_expires_at: float = 0.0
    fulfillment_policy_id: str = ""
    payment_policy_id: str = ""
    return_policy_id: str = ""
    merchant_location_key: str = ""
    zip_code: str = ""

    @classmethod
    def load(cls):
        if not STATE_PATH.exists():
            return cls()
        return cls(**json.loads(STATE_PATH.read_text()))

    def save(self):
        STATE_PATH.write_text(json.dumps(asdict(self), indent=2))


def _credentials_from_env():
    app_id = os.environ.get("EBAY_APP_ID", "").strip()
    cert_id = os.environ.get("EBAY_CERT_ID", "").strip()
    ru_name = os.environ.get("EBAY_RU_NAME", "").strip()
    missing = [n for n, v in [("EBAY_APP_ID", app_id), ("EBAY_CERT_ID", cert_id), ("EBAY_RU_NAME", ru_name)] if not v]
    if missing:
        raise RuntimeError(
            f"Missing eBay credentials in ~/juddy/.env: {', '.join(missing)}. "
            "See discs/EBAY_SETUP.md."
        )
    return app_id, cert_id, ru_name


def _basic_auth_header(app_id, cert_id):
    pair = f"{app_id}:{cert_id}".encode("utf-8")
    return "Basic " + base64.b64encode(pair).decode("ascii")


class _CallbackHandler(BaseHTTPRequestHandler):
    captured_code = None
    captured_error = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs:
            _CallbackHandler.captured_code = qs["code"][0]
            body = b"<html><body><h2>Authorized.</h2><p>You can close this window.</p></body></html>"
        else:
            _CallbackHandler.captured_error = qs.get("error_description", ["unknown"])[0]
            body = b"<html><body><h2>Auth failed.</h2><p>Check the terminal.</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):
        pass


def run_consent_flow():
    """Open a browser to eBay's consent page, capture the code via localhost callback,
    exchange for a refresh token, save state. Returns the EbayState.
    """
    app_id, cert_id, ru_name = _credentials_from_env()

    consent_url = (
        CONSENT_BASE
        + "?"
        + urllib.parse.urlencode({
            "client_id": app_id,
            "redirect_uri": ru_name,
            "response_type": "code",
            "scope": " ".join(SCOPES),
        })
    )

    server = HTTPServer((CALLBACK_HOST, CALLBACK_PORT), _CallbackHandler)
    print(f"Opening browser for eBay consent…")
    print(f"If it doesn't open, paste this URL manually:\n  {consent_url}\n")
    webbrowser.open(consent_url)

    server.handle_request()  # blocks until eBay redirects to /callback
    if _CallbackHandler.captured_error:
        raise RuntimeError(f"eBay denied auth: {_CallbackHandler.captured_error}")
    code = _CallbackHandler.captured_code
    if not code:
        raise RuntimeError("No auth code received. Did the redirect URL match the RuName?")

    print("Got auth code — exchanging for refresh token…")
    resp = requests.post(
        OAUTH_BASE,
        headers={
            "Authorization": _basic_auth_header(app_id, cert_id),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": ru_name,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Token exchange failed [{resp.status_code}]: {resp.text}")
    payload = resp.json()

    state = EbayState.load()
    state.refresh_token = payload["refresh_token"]
    state.access_token = payload["access_token"]
    state.access_token_expires_at = time.time() + int(payload["expires_in"]) - 60
    state.save()
    print("Refresh token saved to", STATE_PATH)
    return state


def get_access_token():
    """Return a current access token, refreshing if expired. Raises if no refresh token."""
    state = EbayState.load()
    if not state.refresh_token:
        raise RuntimeError(
            "No eBay refresh token saved. Run: python -m discs ebay-setup"
        )
    if state.access_token and time.time() < state.access_token_expires_at:
        return state.access_token

    app_id, cert_id, _ = _credentials_from_env()
    resp = requests.post(
        OAUTH_BASE,
        headers={
            "Authorization": _basic_auth_header(app_id, cert_id),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": state.refresh_token,
            "scope": " ".join(SCOPES),
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Refresh failed [{resp.status_code}]: {resp.text}")
    payload = resp.json()
    state.access_token = payload["access_token"]
    state.access_token_expires_at = time.time() + int(payload["expires_in"]) - 60
    state.save()
    return state.access_token
