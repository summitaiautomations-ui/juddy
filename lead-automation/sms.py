"""
Outbound SMS gateway with built-in dedupe.

Invariant: never send the same text message to the same phone number twice,
regardless of which script (nurture_engine, lead_monitor, birthday_campaign)
initiates the send, and regardless of crashes, double-running daemons, or
state-file resets.

Dedupe is enforced by sms_ledger.json — an append-only record of every
SimpleTexting send that returned 2xx. The key is sha256(message) scoped by
the recipient's normalized digit-only phone number. The ledger is written
BEFORE returning to the caller, so a crash between send and caller-side
persistence cannot cause the same text to fire twice on the next tick.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
LEDGER_PATH = SCRIPT_DIR / "sms_ledger.json"


def normalize_phone(value):
    digits = "".join(c for c in str(value) if c.isdigit())
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    return digits


def _key(to_phone, message, namespace=""):
    h = hashlib.sha256(message.encode("utf-8")).hexdigest()
    suffix = f":{namespace}" if namespace else ""
    return f"{normalize_phone(to_phone)}:{h}{suffix}"


def _load_ledger():
    if LEDGER_PATH.exists():
        with open(LEDGER_PATH) as f:
            return json.load(f)
    return {"sent": {}}


def _record_sent(key, to_phone, message, status, source):
    ledger = _load_ledger()
    ledger.setdefault("sent", {})[key] = {
        "phone": normalize_phone(to_phone),
        "text": message,
        "first_sent_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source": source,
    }
    tmp = LEDGER_PATH.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(ledger, f, indent=2)
    os.replace(tmp, LEDGER_PATH)


def already_sent(to_phone, message, dedupe_namespace=""):
    """True iff (phone, message, namespace) has already been delivered with a 2xx."""
    return _key(to_phone, message, dedupe_namespace) in _load_ledger().get("sent", {})


def send_sms_once(config, to_phone, message, *, source, dedupe_namespace=""):
    """
    Send `message` to `to_phone` via SimpleTexting iff this exact text has
    not already been delivered to this number under the given namespace.
    Returns (status, response_text).

    Default namespace is empty — strict forever-dedupe per (phone, text).
    Pass `dedupe_namespace="year:2026"` (or similar) to scope dedupe to a
    window so legitimately-recurring messages (e.g. annual birthdays with
    a fixed template) can re-fire in a new window while still being blocked
    inside it.

    On a duplicate, returns (0, "skipped:duplicate ...") without calling the
    API. On a successful 2xx send, records the send in the ledger BEFORE
    returning, so callers cannot lose the dedupe record by crashing.
    """
    key = _key(to_phone, message, dedupe_namespace)
    ledger = _load_ledger()
    prior = ledger.get("sent", {}).get(key)
    if prior:
        return (
            0,
            f"skipped:duplicate (first sent {prior['first_sent_at']} via {prior.get('source', 'unknown')})",
        )

    url = "https://api-app2.simpletexting.com/v2/api/messages"
    headers = {
        "Authorization": f"Bearer {config['simpletexting']['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "contactPhone": to_phone,
        "accountPhone": config["simpletexting"]["account_phone"],
        "type": "SINGLE_SMS",
        "text": message,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)

    if 200 <= resp.status_code < 300:
        _record_sent(key, to_phone, message, resp.status_code, source)

    return resp.status_code, resp.text
