#!/usr/bin/env python3
"""Quo (formerly OpenPhone) -> Notion communications sync.

Polls the Quo API for recent calls and text messages, fetches call
transcripts/summaries when available, matches the other party's phone number
against contact databases in Notion, and files everything into a
"Communications" database (one row per call / per text, transcript in the
page body).

Designed to run repeatedly via launchd (see install.sh). Each run is
incremental: a state file remembers the sync watermark, which items have
already been written, and which transcripts are still pending so they can be
back-filled into their Notion page once Quo finishes transcribing.

Stdlib only -- no pip installs needed.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

QUO_BASE = "https://api.openphone.com/v1"
NOTION_BASE = "https://api.notion.com/v1"

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/juddy/quo-notion-sync.json")
DEFAULT_STATE_PATH = os.path.expanduser(
    "~/.local/state/juddy/quo-notion-sync/state.json"
)

# How far to look back on the very first run.
DEFAULT_BACKFILL_HOURS = 72
# Overlap window so nothing is missed between runs (dedupe handles repeats).
OVERLAP_MINUTES = 30
# Give up on a pending transcript after this long.
PENDING_TRANSCRIPT_TTL_HOURS = 48
# Cap on remembered item IDs (dedupe ring buffer).
MAX_SEEN_IDS = 5000

VERBOSE = False


def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}Z] {msg}")
    sys.stdout.flush()


def debug(msg):
    if VERBOSE:
        log(f"debug: {msg}")


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_phone(raw):
    """Reduce a phone number to its last 10 digits for matching."""
    digits = "".join(c for c in (raw or "") if c.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


class ApiError(Exception):
    def __init__(self, status, body, url):
        super().__init__(f"HTTP {status} for {url}: {body[:500]}")
        self.status = status
        self.body = body
        self.url = url


def http_json(method, url, headers, payload=None, retries=3):
    data = json.dumps(payload).encode() if payload is not None else None
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        # Cloudflare in front of the Quo API rejects Python's default
        # User-Agent with error 1010, so send a real one.
        req.add_header("User-Agent", "juddy-quo-notion-sync/1.0")
        req.add_header("Accept", "application/json")
        for k, v in headers.items():
            req.add_header(k, v)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            # Retry on rate limits and server errors; fail fast otherwise.
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                debug(f"HTTP {e.code} from {url}, retrying in {wait}s")
                time.sleep(wait)
                last_err = ApiError(e.code, body, url)
                continue
            raise ApiError(e.code, body, url)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
                last_err = e
                continue
            raise
    raise last_err


# ---------------------------------------------------------------------------
# Quo (OpenPhone) API
# ---------------------------------------------------------------------------


class QuoClient:
    def __init__(self, api_key):
        # Quo API keys are sent as-is (no "Bearer" prefix).
        self.headers = {"Authorization": api_key}

    def _get(self, path, params=None, list_params=None):
        query = []
        for k, v in (params or {}).items():
            if v is not None:
                query.append((k, v))
        for k, values in (list_params or {}).items():
            for v in values:
                query.append((k, v))
        url = f"{QUO_BASE}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        return http_json("GET", url, self.headers)

    def _get_paginated(self, path, params=None, list_params=None, max_pages=20):
        items, token = [], None
        for _ in range(max_pages):
            p = dict(params or {})
            if token:
                p["pageToken"] = token
            resp = self._get(path, p, list_params)
            items.extend(resp.get("data") or [])
            token = resp.get("nextPageToken")
            if not token:
                break
        return items

    def phone_numbers(self):
        return self._get_paginated("/phone-numbers")

    def conversations_updated_after(self, watermark):
        """All conversations with activity after the watermark.

        Tries the server-side filter first; if the API rejects the param,
        falls back to paging until items are older than the watermark.
        """
        try:
            items = self._get_paginated(
                "/conversations",
                {"updatedAfter": iso(watermark), "maxResults": 100},
            )
        except ApiError as e:
            if e.status != 400:
                raise
            debug("conversations updatedAfter rejected; falling back to paging")
            items = []
            token = None
            for _ in range(30):
                p = {"maxResults": 100}
                if token:
                    p["pageToken"] = token
                resp = self._get("/conversations", p)
                page = resp.get("data") or []
                items.extend(page)
                token = resp.get("nextPageToken")
                oldest = min(
                    (parse_iso(c.get("updatedAt") or c.get("lastActivityAt"))
                     for c in page if c.get("updatedAt") or c.get("lastActivityAt")),
                    default=None,
                )
                if not token or (oldest and oldest < watermark):
                    break
        result = []
        for c in items:
            updated = parse_iso(c.get("updatedAt") or c.get("lastActivityAt"))
            if updated is None or updated >= watermark:
                result.append(c)
        return result

    def _list_activity(self, path, phone_number_id, participant, created_after):
        params = {
            "phoneNumberId": phone_number_id,
            "createdAfter": iso(created_after),
            "maxResults": 100,
        }
        try:
            return self._get_paginated(
                path, params, list_params={"participants": [participant]}
            )
        except ApiError as e:
            # Some deployments expect participants[] array syntax.
            if e.status == 400:
                return self._get_paginated(
                    path, params, list_params={"participants[]": [participant]}
                )
            raise

    def calls(self, phone_number_id, participant, created_after):
        return self._list_activity("/calls", phone_number_id, participant, created_after)

    def messages(self, phone_number_id, participant, created_after):
        return self._list_activity(
            "/messages", phone_number_id, participant, created_after
        )

    def call_transcript(self, call_id):
        """Returns the transcript object, or None if unavailable on this plan."""
        try:
            return self._get(f"/call-transcripts/{call_id}").get("data")
        except ApiError as e:
            if e.status in (402, 403, 404):
                return None
            raise

    def call_summary(self, call_id):
        try:
            return self._get(f"/call-summaries/{call_id}").get("data")
        except ApiError as e:
            if e.status in (402, 403, 404):
                return None
            raise


# ---------------------------------------------------------------------------
# Notion API
# ---------------------------------------------------------------------------


class NotionClient:
    def __init__(self, token, version="2022-06-28"):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": version,
        }

    def _call(self, method, path, payload=None):
        # Notion allows ~3 requests/sec; stay well under it.
        time.sleep(0.34)
        return http_json(method, f"{NOTION_BASE}{path}", self.headers, payload)

    def query_all(self, database_id, filter_=None):
        results, cursor = [], None
        while True:
            payload = {"page_size": 100}
            if filter_:
                payload["filter"] = filter_
            if cursor:
                payload["start_cursor"] = cursor
            resp = self._call("POST", f"/databases/{database_id}/query", payload)
            results.extend(resp.get("results") or [])
            if not resp.get("has_more"):
                return results
            cursor = resp.get("next_cursor")

    def find_by_rich_text(self, database_id, prop, value):
        resp = self._call(
            "POST",
            f"/databases/{database_id}/query",
            {"page_size": 1, "filter": {"property": prop, "rich_text": {"equals": value}}},
        )
        results = resp.get("results") or []
        return results[0] if results else None

    def create_page(self, database_id, properties, children=None):
        payload = {"parent": {"database_id": database_id}, "properties": properties}
        if children:
            payload["children"] = children[:100]
        page = self._call("POST", "/pages", payload)
        # Append any remaining blocks in batches of 100.
        rest = (children or [])[100:]
        for i in range(0, len(rest), 100):
            self.append_blocks(page["id"], rest[i : i + 100])
        return page

    def update_page(self, page_id, properties):
        return self._call("PATCH", f"/pages/{page_id}", {"properties": properties})

    def append_blocks(self, block_id, children):
        for i in range(0, len(children), 100):
            self._call(
                "PATCH",
                f"/blocks/{block_id}/children",
                {"children": children[i : i + 100]},
            )


def rt(text):
    """Rich text value, chunked to Notion's 2000-char limit."""
    text = text or ""
    return [
        {"text": {"content": text[i : i + 2000]}} for i in range(0, len(text), 2000)
    ] or [{"text": {"content": ""}}]


def para(text):
    return {"type": "paragraph", "paragraph": {"rich_text": rt(text)}}


def heading(text):
    return {"type": "heading_2", "heading_2": {"rich_text": rt(text)}}


# ---------------------------------------------------------------------------
# Contact matching
# ---------------------------------------------------------------------------


def load_contact_index(notion, contact_dbs):
    """phone(last 10 digits) -> list of {page_id, name, db_config}."""
    index = {}
    for db in contact_dbs:
        try:
            pages = notion.query_all(db["database_id"])
        except ApiError as e:
            log(
                f"warning: cannot read contact database {db['database_id']} "
                f"(HTTP {e.status}). Is it shared with the integration?"
            )
            continue
        count = 0
        for page in pages:
            props = page.get("properties") or {}
            phone_prop = props.get(db["phone_property"]) or {}
            key = normalize_phone(phone_prop.get("phone_number"))
            if not key:
                continue
            title = ""
            for p in props.values():
                if p.get("type") == "title":
                    title = "".join(
                        t.get("plain_text", "") for t in p.get("title") or []
                    )
                    break
            index.setdefault(key, []).append(
                {"page_id": page["id"], "name": title, "db": db}
            )
            count += 1
        debug(f"indexed {count} phone numbers from {db.get('label', db['database_id'])}")
    return index


def touch_last_contact(notion, match, when_iso):
    prop = match["db"].get("last_contact_property")
    if not prop:
        return
    try:
        notion.update_page(
            match["page_id"], {prop: {"date": {"start": when_iso}}}
        )
    except ApiError as e:
        log(f"warning: could not update '{prop}' on {match['name']}: HTTP {e.status}")


# ---------------------------------------------------------------------------
# Building Notion rows
# ---------------------------------------------------------------------------


def transcript_blocks(transcript):
    blocks = [heading("Transcript")]
    for seg in transcript.get("dialogue") or []:
        speaker = seg.get("identifier") or seg.get("userId") or "Speaker"
        blocks.append(para(f"{speaker}: {seg.get('content', '')}"))
    if len(blocks) == 1:
        blocks.append(para("(empty transcript)"))
    return blocks


def summary_text(summary):
    if not summary:
        return ""
    parts = list(summary.get("summary") or [])
    steps = summary.get("nextSteps") or []
    if steps:
        parts.append("Next steps: " + "; ".join(steps))
    return " ".join(parts)


def build_call_row(call, external, quo_number, matches, transcript, summary):
    when = call.get("createdAt") or call.get("completedAt")
    direction = "Incoming" if call.get("direction") == "incoming" else "Outgoing"
    is_voicemail = bool(call.get("voicemail"))
    missed = call.get("status") in ("missed", "no-answer") and not is_voicemail
    contact_name = matches[0]["name"] if matches else external
    kind = "Voicemail" if is_voicemail else "Call"
    title = f"{'Missed call' if missed else kind} — {contact_name} — {when[:10] if when else ''}"

    if transcript and (transcript.get("dialogue") or []):
        t_status = "Completed"
    elif transcript and transcript.get("status") in ("in-progress", "processing"):
        t_status = "Pending"
    else:
        t_status = "Unavailable"

    props = {
        "Name": {"title": rt(title)},
        "Type": {"select": {"name": kind}},
        "Direction": {"select": {"name": direction}},
        "Phone": {"phone_number": external or None},
        "Quo Number": {"phone_number": quo_number or None},
        "Quo ID": {"rich_text": rt(call.get("id", ""))},
        "Transcript Status": {"select": {"name": t_status}},
    }
    if when:
        props["When"] = {"date": {"start": when}}
    if call.get("duration") is not None:
        props["Duration (s)"] = {"number": call["duration"]}
    s_text = summary_text(summary)
    if s_text:
        props["Summary"] = {"rich_text": rt(s_text[:1900])}
    for m in matches:
        rel_prop = m["db"].get("relation_property")
        if rel_prop:
            props.setdefault(rel_prop, {"relation": []})
            props[rel_prop]["relation"].append({"id": m["page_id"]})

    children = []
    if s_text:
        children += [heading("AI Summary"), para(s_text)]
    if transcript and (transcript.get("dialogue") or []):
        children += transcript_blocks(transcript)
    elif t_status == "Pending":
        children.append(para("Transcript pending — will be added automatically."))
    return props, children, t_status


def build_message_row(msg, external, quo_number, matches):
    when = msg.get("createdAt")
    direction = "Incoming" if msg.get("direction") == "incoming" else "Outgoing"
    text = msg.get("text") or msg.get("content") or msg.get("body") or ""
    contact_name = matches[0]["name"] if matches else external
    arrow = "from" if direction == "Incoming" else "to"
    title = f"Text {arrow} {contact_name} — {when[:10] if when else ''}"

    props = {
        "Name": {"title": rt(title)},
        "Type": {"select": {"name": "Text"}},
        "Direction": {"select": {"name": direction}},
        "Phone": {"phone_number": external or None},
        "Quo Number": {"phone_number": quo_number or None},
        "Quo ID": {"rich_text": rt(msg.get("id", ""))},
        "Summary": {"rich_text": rt(text[:1900])},
    }
    if when:
        props["When"] = {"date": {"start": when}}
    for m in matches:
        rel_prop = m["db"].get("relation_property")
        if rel_prop:
            props.setdefault(rel_prop, {"relation": []})
            props[rel_prop]["relation"].append({"id": m["page_id"]})
    return props, [para(text)] if text else []


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def load_state(path):
    state = {"last_sync": None, "seen_ids": [], "pending_transcripts": []}
    try:
        with open(path) as f:
            state.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return state


def save_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    state["seen_ids"] = state["seen_ids"][-MAX_SEEN_IDS:]
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Main sync
# ---------------------------------------------------------------------------


def external_participants(item, own_numbers):
    """Participants of a call/conversation that are not our own Quo lines."""
    out = []
    for p in item.get("participants") or []:
        number = p if isinstance(p, str) else p.get("phoneNumber") or p.get("number")
        if number and normalize_phone(number) not in own_numbers:
            out.append(number)
    return out


def run_sync(config, state_path, dry_run=False, backfill_hours=None):
    quo = QuoClient(config["quo_api_key"])
    notion = NotionClient(
        config["notion_token"], config.get("notion_version", "2022-06-28")
    )
    comms_db = config["communications_database_id"]
    state = load_state(state_path)
    seen = set(state["seen_ids"])
    now = datetime.now(timezone.utc)

    last_sync = parse_iso(state["last_sync"])
    if last_sync:
        watermark = last_sync - timedelta(minutes=OVERLAP_MINUTES)
    else:
        hours = backfill_hours or config.get("backfill_hours", DEFAULT_BACKFILL_HOURS)
        watermark = now - timedelta(hours=hours)
        log(f"first run: backfilling the last {hours}h")

    # 1. Our phone numbers.
    numbers = quo.phone_numbers()
    if not numbers:
        log("error: no Quo phone numbers visible to this API key")
        return 1
    pn_by_id = {}
    own_numbers = set()
    for n in numbers:
        num = n.get("number") or n.get("phoneNumber") or ""
        pn_by_id[n["id"]] = num
        own_numbers.add(normalize_phone(num))
    debug(f"quo lines: {sorted(pn_by_id.values())}")

    # 2. Contact index from Notion.
    contact_index = load_contact_index(notion, config.get("contact_databases") or [])
    log(f"contact index: {len(contact_index)} distinct phone numbers")

    # 3. Conversations with recent activity -> (line, participant) pairs to poll.
    convos = quo.conversations_updated_after(watermark)
    pairs = set()
    for c in convos:
        pn_id = c.get("phoneNumberId")
        if pn_id not in pn_by_id:
            continue
        for ext in external_participants(c, own_numbers):
            pairs.add((pn_id, ext))
    log(f"{len(convos)} active conversations -> {len(pairs)} (line, contact) pairs")

    created = 0

    def file_row(item_id, props, children):
        nonlocal created
        if dry_run:
            log(f"dry-run: would create row for {item_id}: "
                f"{props['Name']['title'][0]['text']['content']}")
            return None
        existing = notion.find_by_rich_text(comms_db, "Quo ID", item_id)
        if existing:
            debug(f"{item_id} already in Notion, skipping")
            return existing["id"]
        page = notion.create_page(comms_db, props, children)
        created += 1
        return page["id"]

    # 4. Calls and messages per pair.
    poll_calls = config.get("poll_calls", True)
    poll_messages = config.get("poll_messages", True)
    for pn_id, ext in sorted(pairs):
        quo_number = pn_by_id[pn_id]
        matches = contact_index.get(normalize_phone(ext), [])

        if poll_calls:
            for call in quo.calls(pn_id, ext, watermark):
                if call["id"] in seen:
                    continue
                if call.get("status") not in (None, "completed", "missed", "no-answer",
                                              "answered", "forwarded"):
                    continue  # in-progress call; pick it up next run
                transcript = summary = None
                if call.get("duration"):
                    transcript = quo.call_transcript(call["id"])
                    summary = quo.call_summary(call["id"])
                props, children, t_status = build_call_row(
                    call, ext, quo_number, matches, transcript, summary
                )
                page_id = file_row(call["id"], props, children)
                seen.add(call["id"])
                when = call.get("createdAt")
                if page_id and t_status == "Pending":
                    state["pending_transcripts"].append(
                        {"call_id": call["id"], "page_id": page_id,
                         "since": iso(now)}
                    )
                if matches and when and not dry_run:
                    for m in matches:
                        touch_last_contact(notion, m, when)

        if poll_messages:
            for msg in quo.messages(pn_id, ext, watermark):
                if msg["id"] in seen:
                    continue
                props, children = build_message_row(msg, ext, quo_number, matches)
                file_row(msg["id"], props, children)
                seen.add(msg["id"])
                when = msg.get("createdAt")
                if matches and when and not dry_run:
                    for m in matches:
                        touch_last_contact(notion, m, when)

    # 5. Retry pending transcripts.
    still_pending = []
    for item in state.get("pending_transcripts") or []:
        age = now - (parse_iso(item.get("since")) or now)
        if age > timedelta(hours=PENDING_TRANSCRIPT_TTL_HOURS):
            log(f"giving up on transcript for call {item['call_id']}")
            if not dry_run:
                try:
                    notion.update_page(
                        item["page_id"],
                        {"Transcript Status": {"select": {"name": "Unavailable"}}},
                    )
                except ApiError:
                    pass
            continue
        transcript = quo.call_transcript(item["call_id"])
        if transcript and (transcript.get("dialogue") or []):
            log(f"transcript ready for call {item['call_id']}, updating page")
            if not dry_run:
                notion.append_blocks(item["page_id"], transcript_blocks(transcript))
                summary = quo.call_summary(item["call_id"])
                props = {"Transcript Status": {"select": {"name": "Completed"}}}
                s_text = summary_text(summary)
                if s_text:
                    props["Summary"] = {"rich_text": rt(s_text[:1900])}
                notion.update_page(item["page_id"], props)
        else:
            still_pending.append(item)
    state["pending_transcripts"] = still_pending

    # 6. Save state.
    state["last_sync"] = iso(now)
    state["seen_ids"] = list(seen)
    if not dry_run:
        save_state(state_path, state)
    log(
        f"done: {created} new row(s) in Notion, "
        f"{len(still_pending)} transcript(s) still pending"
    )
    return 0


def main():
    global VERBOSE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    ap.add_argument("--state", default=DEFAULT_STATE_PATH)
    ap.add_argument("--dry-run", action="store_true",
                    help="log what would be written without touching Notion")
    ap.add_argument("--backfill-hours", type=int, default=None,
                    help="override lookback window for a first run")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    VERBOSE = args.verbose or os.environ.get("QUO_SYNC_VERBOSE") == "1"

    try:
        with open(args.config) as f:
            config = json.load(f)
    except FileNotFoundError:
        log(f"error: config not found at {args.config}. "
            "Copy config.example.json there and fill in your keys.")
        return 1
    except json.JSONDecodeError as e:
        log(f"error: config is not valid JSON: {e}")
        return 1

    for key in ("quo_api_key", "notion_token", "communications_database_id"):
        if not config.get(key) or "YOUR_" in str(config.get(key)):
            log(f"error: '{key}' is not set in {args.config}")
            return 1

    try:
        return run_sync(config, args.state, args.dry_run, args.backfill_hours)
    except ApiError as e:
        log(f"error: {e}")
        if e.status == 401:
            log("hint: check quo_api_key (Quo) / notion_token (Notion) in the config")
        return 1


if __name__ == "__main__":
    sys.exit(main())
