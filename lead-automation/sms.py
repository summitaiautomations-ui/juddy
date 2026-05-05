"""
Outbound SMS gateway with built-in dedupe.

Invariant: never send the same text message to the same phone number twice,
regardless of which script (nurture_engine, lead_monitor, birthday_campaign)
initiates the send, and regardless of crashes, double-running daemons, or
state-file resets.

"Same text" is fuzzy on purpose. The real-world duplicates that motivated
this gateway included:
  - Two welcome messages 1h22m apart that differed only by a trailing emoji
    (lead_monitor sent the no-emoji version, nurture_engine sent the emoji
    version — different bytes, same message to a human).
  - Two market-update texts on consecutive Fridays whose opening paragraph
    differed but whose 3-sentence closing paragraph was byte-identical
    ("I'm around all weekend — if you see something you want to run
    numbers on..."). The recipient read them as the same text.

So dedupe runs at two levels:
  1. Normalized exact-match: strip emoji + non-ascii, collapse whitespace,
     lowercase. Catches the emoji/whitespace variants.
  2. Substantial-sentence overlap: split each message into sentences of
     >= MIN_SENTENCE_CHARS, normalize each, and block if any substantial
     sentence has already been sent to this number. Catches the shared
     closing-paragraph case.

Dedupe is enforced via sms_ledger.json — an append-only record of every
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

# Sentences shorter than this are too generic to dedupe on (e.g. "Hey Isiah!"
# at 10 chars normalized). Tight enough that medium-length clauses like
# "How's the search going?" (23 chars normalized) count — if Isiah's already
# heard that sentence, a different message that reuses it is a duplicate.
MIN_SENTENCE_CHARS = 20

# Sentences that look like a human greeting/closer are excluded from the
# dedupe set regardless of length (up to SALUTATION_MAX_CHARS), because we
# WANT the engine to text like a person. "Hey Isiah, how's it going?" should
# be free to recur naturally across messages; only substantive content
# should pin a message as a duplicate.
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
    """Strip emoji + non-ascii, collapse whitespace, lowercase. Two messages
    that humans would read as identical should normalize to the same string."""
    ascii_only = "".join(c for c in str(text) if ord(c) < 128)
    collapsed = re.sub(r"\s+", " ", ascii_only).strip().lower()
    return collapsed


def _is_salutation(normalized_sentence):
    """A short-ish sentence that opens or closes with a human-greeting
    pattern. Excluded from the dedupe set so warm openers and closers can
    recur naturally across messages."""
    if len(normalized_sentence) > SALUTATION_MAX_CHARS:
        return False
    return any(normalized_sentence.startswith(p) for p in SALUTATION_PREFIXES)


def _substantial_sentences(text):
    """Return the set of normalized sentences in `text` long enough to be
    distinctive AND not salutation-shaped. Sentence boundaries: . ! ? — \\n."""
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
    """Return the prior ledger entry that makes `message` a duplicate for
    `to_phone`, or None. Checks: same normalized text, OR any substantial
    sentence overlap with a prior send to this number in this namespace."""
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


def already_sent(to_phone, message, dedupe_namespace=""):
    """True iff a normalized-equivalent or sentence-overlapping message has
    already been delivered to this number with a 2xx in this namespace."""
    return _find_duplicate(_load_ledger(), to_phone, message, dedupe_namespace) is not None


def send_sms_once(config, to_phone, message, *, source, dedupe_namespace=""):
    """
    Send `message` to `to_phone` via SimpleTexting iff no
    normalized-equivalent or sentence-overlapping message has already been
    delivered to this number under the given namespace.

    Returns (status, response_text).

    Default namespace is empty — strict forever-dedupe. Pass
    `dedupe_namespace="year:2026"` (or similar) to scope dedupe to a window
    so legitimately-recurring messages (e.g. annual birthdays with a fixed
    template) can re-fire in a new window while still being blocked inside
    it.

    On a duplicate, returns (0, "skipped:duplicate ...") without calling the
    API. On a successful 2xx send, records the send in the ledger BEFORE
    returning, so callers cannot lose the dedupe record by crashing.
    """
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
        _record_sent(_key(to_phone, message, dedupe_namespace), to_phone, message, resp.status_code, source, dedupe_namespace)

    return resp.status_code, resp.text
