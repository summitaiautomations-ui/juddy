"""Authenticated HTTP client for eBay Sell APIs.

Wraps requests with bearer-token auth, auto-refresh on 401, and clear
error messages that surface eBay's structured error payloads.
"""

import json

import requests

from discs.ebay import auth

MARKETPLACE_ID = "EBAY_US"
SELL_BASE = "https://api.ebay.com"


class EbayApiError(RuntimeError):
    def __init__(self, method, url, status, body):
        self.status = status
        self.body = body
        try:
            parsed = json.loads(body) if body else {}
            errors = parsed.get("errors") or []
            msgs = [
                f"  - {e.get('errorId')}: {e.get('message')} "
                f"({e.get('longMessage', '')})"
                for e in errors
            ]
            detail = "\n".join(msgs) if msgs else body[:500]
        except Exception:
            detail = body[:500]
        super().__init__(f"eBay {method} {url} → {status}\n{detail}")


def _headers(content_language="en-US"):
    return {
        "Authorization": f"Bearer {auth.get_access_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-Language": content_language,
        "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
    }


def _request(method, path, *, json_body=None, retry_on_401=True):
    url = SELL_BASE + path
    resp = requests.request(
        method,
        url,
        headers=_headers(),
        json=json_body,
        timeout=60,
    )
    if resp.status_code == 401 and retry_on_401:
        # Force-refresh: clear cached access token, try once more.
        state = auth.EbayState.load()
        state.access_token = ""
        state.access_token_expires_at = 0
        state.save()
        return _request(method, path, json_body=json_body, retry_on_401=False)
    if resp.status_code >= 400:
        raise EbayApiError(method, url, resp.status_code, resp.text)
    if resp.status_code == 204 or not resp.content:
        return {}
    return resp.json()


def get(path):
    return _request("GET", path)


def post(path, body):
    return _request("POST", path, json_body=body)


def put(path, body):
    return _request("PUT", path, json_body=body)


def delete(path):
    return _request("DELETE", path)
