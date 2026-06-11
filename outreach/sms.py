"""
Outbound SMS gateway with built-in dedupe.

Invariant: never send the same text message to the same phone number twice,
regardless of which flow initiates the send and regardless of crashes or
double-running daemons.

"Same text" is fuzzy on purpose. Real-world duplicates that motivated this
gateway included:
  - Two welcome messages differing only by a trailing emoji.
  - Two market-update texts whose closing paragraph was byte-identical but
    whose opening differed.

So dedupe runs at two levels:
  1. Normalized exact-match: strip emoji + non-ascii, collapse whitespace,
     lowercase. Catches the emoji/whitespace variants.
  2. Substantial-sentence overlap: split each message into sentences of
     >= MIN_SENTENCE_CHARS, normalize each, and block if any substantial
     sentence has already been sent to this number in this namespace.

Dedupe is enforced via sms_ledger.json — append-only record of every
SimpleTexting send that returned 2xx. The ledger is written BEFORE
send_sms_once returns, so a crash between send and caller-side persistence
cannot cause the same message to fire twice on the next tick.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
LEDGER_PATH = SCRIPT_DIR / "sms_ledger.json"

# Sentences shorter than this are too generic to dedupe on.
MIN_SENTENCE_CHARS = 20

# Salutations and closers shorter than this are excluded from dedupe so they
# can recur naturally across messages without flagging dupes.
SALUTATION_MAX_CHARS = 60
SALUTATION_PREFIXES = (
    "hey ", "hey,", "hi ", "hi,", "hello", "howdy", "yo ",
    "good morning", "good afternoon", "good evening",
    "morning,", "afternoon,", "evening,",
    "hope you", "hope your", "hope all",
    "just checking in", "just wanted to check",
    "just circling back", "just wanted to circle",
    "thanks", "thank you", "talk soon", "talk later",
    "have a great", "have a good",
)


def normalize_phone(value):
    digits = "".join(c for c in str(value) if c.isdigit())
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    return digits


def _normalize_text(text):
    ascii_only = "".join(c for c in str(text) if ord(c) < 128)
    return re.sub(r"\s+", " ", ascii_only).strip().lower()


def _is_salutation(normalized_sentence):
    if len(normalized_sentence) > SALUTATION_MAX_CHARS:
        return False
    return any(normalized_sentence.startswith(p) for p in SALUTATION_PREFIXES)


def _substantial_sentences(text):
    pieces = re.split(r"(?<=[.!?])\s+|\s+—\s+|\n+", str(text))
    out = set()
    for p in pieces:
        n = _normalize_text(p)
        if len(n) >= MIN_SENTENCE_CHARS and not _is_salutation(n):
            out.add(n)
    return out


def _msg_hash(text):
    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()


def _key(to_phone, message, namespace=""):
    suffix = f":{namespace}" if namespace else ""
    return f"{normalize_phone(to_phone)}:{_msg_hash(message)}{suffix}"


def _load_ledger():
    if LEDGER_PATH.exists():
        with open(LEDGER_PATH) as f:
            return json.load(f)
    return {"sent": {}}


def _record_sent(key, to_phone, message, status, source, namespace):
    ledger = _load_ledger()
    ledger.setdefault("sent", {})[key] = {
        "phone": normalize_phone(to_phone),
        "text": message,
        "normalized": _normalize_text(message),
        "sentences": sorted(_substantial_sentences(message)),
        "namespace": namespace,
        "first_sent_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source": source,
    }
    tmp = LEDGER_PATH.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(ledger, f, indent=2)
    os.replace(tmp, LEDGER_PATH)


def _find_duplicate(ledger, to_phone, message, namespace):
    phone = normalize_phone(to_phone)
    msg_norm = _normalize_text(message)
    msg_sentences = _substantial_sentences(message)

    for entry in ledger.get("sent", {}).values():
        if entry.get("phone") != phone:
            continue
        if entry.get("namespace", "") != namespace:
            continue
        if entry.get("normalized") == msg_norm:
            return entry
        prior_sentences = set(entry.get("sentences", []))
        if msg_sentences & prior_sentences:
            return entry
    return None


def has_sent_today(to_phone, today_iso):
    """True iff any successful SMS landed on this phone today.

    Used by the daily-cap safeguard so day-2+ nurture flows can never
    layer a second automated text onto a lead in the same day. Day 1
    flows (welcome + info touch) are exempt because they pass
    enforce_daily_cap=False — that's the intended 2-touch sequence.
    """
    phone = normalize_phone(to_phone)
    for entry in _load_ledger().get("sent", {}).values():
        if entry.get("phone") != phone:
            continue
        if str(entry.get("first_sent_at", "")).startswith(today_iso):
            return True
    return False


def send_sms_once(config, to_phone, message, *, source, dedupe_namespace="", enforce_daily_cap=False):
    """
    Send `message` to `to_phone` via SimpleTexting iff no normalized-equivalent
    or sentence-overlapping message has already been delivered to this number
    under the given namespace.

    Returns (status, response_text). status=0 on a dedupe skip (no API call).

    Pass dedupe_namespace="birthday:2026" (or similar) to scope dedupe to a
    window so legitimately-recurring messages (annual birthdays, weekly
    market updates) can re-fire in a new window.

    Pass enforce_daily_cap=True to short-circuit if any other SMS has
    already landed on this phone today. Day-1 flows (welcome, info touch)
    leave it False so the two-touch sequence isn't blocked; everything
    else (day-2 nurture, Friday recap, …) should pass True so a lead
    never gets more than one automated text per day after day 1.

    On a successful 2xx, the ledger entry is written BEFORE returning, so
    callers cannot lose the dedupe record by crashing.
    """
    if enforce_daily_cap:
        today_iso = datetime.now(timezone.utc).date().isoformat()
        if has_sent_today(to_phone, today_iso):
            return (
                0,
                "skipped:daily_cap (one automated SMS per lead per day after day 1)",
            )

    ledger = _load_ledger()
    prior = _find_duplicate(ledger, to_phone, message, dedupe_namespace)
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
        _record_sent(
            _key(to_phone, message, dedupe_namespace),
            to_phone, message, resp.status_code, source, dedupe_namespace,
        )

    return resp.status_code, resp.text
