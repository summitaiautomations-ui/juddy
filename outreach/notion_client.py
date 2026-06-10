"""Minimal Notion client for the Mortgage Pipeline DB.

Fetches past-client records with DOB + phone, finds records by phone,
updates simple properties (date, select), and appends activity lines
back to a record's Notes property.
"""

import requests

from outreach.sms import normalize_phone

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

PAST_CLIENT_STATUSES = ("Funded", "Friends and Family")

# Notion caps rich_text content at 2000 chars per block.
NOTION_RICH_TEXT_LIMIT = 2000

# Map of property name → callable that builds the Notion API value shape.
# Used by update_simple_properties.
_PROPERTY_SHAPES = {
    "Last Contact": lambda v: {"date": {"start": v}},
    "Next Follow-Up": lambda v: {"date": {"start": v}},
    "Priority": lambda v: {"select": {"name": v}},
    "Status": lambda v: {"select": {"name": v}},
}


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": VERSION,
        "Content-Type": "application/json",
    }


def _title(prop):
    return "".join(rt.get("plain_text", "") for rt in prop.get("title", []))


def _rich_text(prop):
    return "".join(rt.get("plain_text", "") for rt in prop.get("rich_text", []))


def _select_name(prop):
    return ((prop or {}).get("select") or {}).get("name")


def _date_start(prop):
    return ((prop or {}).get("date") or {}).get("start")


def _to_rich_text_chunks(content):
    if len(content) <= NOTION_RICH_TEXT_LIMIT:
        return [{"type": "text", "text": {"content": content}}]
    return [
        {"type": "text", "text": {"content": content[i:i + NOTION_RICH_TEXT_LIMIT]}}
        for i in range(0, len(content), NOTION_RICH_TEXT_LIMIT)
    ]


def _query(token, database_id, body):
    """POST to /databases/{id}/query and yield each page result."""
    cursor = None
    while True:
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(
            f"{API}/databases/{database_id}/query",
            json=body, headers=_headers(token), timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        for page in data["results"]:
            yield page
        if not data.get("has_more"):
            return
        cursor = data["next_cursor"]


def fetch_past_clients_with_birthday(token, database_id):
    """Yield every past-client page that has both a DOB and a Phone."""
    body = {
        "filter": {
            "and": [
                {"or": [
                    {"property": "Status", "select": {"equals": s}}
                    for s in PAST_CLIENT_STATUSES
                ]},
                {"property": "Date of Birth", "date": {"is_not_empty": True}},
                {"property": "Phone", "phone_number": {"is_not_empty": True}},
            ],
        },
        "page_size": 100,
    }
    for page in _query(token, database_id, body):
        props = page["properties"]
        yield {
            "id": page["id"],
            "name": _title(props.get("Lead Name", {})),
            "phone": props.get("Phone", {}).get("phone_number"),
            "dob": _date_start(props.get("Date of Birth", {})),
            "notes": _rich_text(props.get("Notes", {})),
        }


def _record_from_page(page):
    props = page["properties"]
    return {
        "id": page["id"],
        "name": _title(props.get("Lead Name", {})),
        "priority": _select_name(props.get("Priority", {})),
        "status": _select_name(props.get("Status", {})),
        "phone": props.get("Phone", {}).get("phone_number"),
        "email": props.get("Email", {}).get("email"),
        "notes": _rich_text(props.get("Notes", {})),
    }


def find_by_phone(token, database_id, phone_digits):
    """Find an active pipeline record matching `phone_digits` (10-char).

    Filters out Dead/archived at the API layer, then compares normalized
    phone digits in Python to handle inconsistent stored formats.
    Returns the record dict or None.
    """
    body = {
        "filter": {
            "and": [
                {"property": "Phone", "phone_number": {"is_not_empty": True}},
                {"property": "Priority", "select": {"does_not_equal": "Dead"}},
            ],
        },
        "page_size": 100,
    }
    for page in _query(token, database_id, body):
        stored = page["properties"].get("Phone", {}).get("phone_number") or ""
        if normalize_phone(stored) == phone_digits:
            return _record_from_page(page)
    return None


def find_by_email(token, database_id, email_addr):
    """Find an active pipeline record whose Email matches `email_addr`
    case-insensitively. Returns the record dict or None."""
    if not email_addr:
        return None
    target = email_addr.strip().lower()
    body = {
        "filter": {
            "and": [
                {"property": "Email", "email": {"equals": target}},
                {"property": "Priority", "select": {"does_not_equal": "Dead"}},
            ],
        },
        "page_size": 5,
    }
    for page in _query(token, database_id, body):
        stored = (page["properties"].get("Email", {}).get("email") or "").strip().lower()
        if stored == target:
            return _record_from_page(page)
    return None


def is_engaged(notes_text):
    """True if the Notes already show any received message — used by nurture
    flows to stop sending automated texts once Justin takes over."""
    return "RCVD:" in (notes_text or "")


def fetch_overdue_followups(token, database_id, today_date):
    """Yield active records whose Next Follow-Up is on or before today."""
    body = {
        "filter": {
            "and": [
                {"property": "Next Follow-Up", "date": {"on_or_before": today_date.isoformat()}},
                {"property": "Priority", "select": {"does_not_equal": "Dead"}},
            ],
        },
        "sorts": [{"property": "Next Follow-Up", "direction": "ascending"}],
        "page_size": 100,
    }
    from datetime import datetime as _dt
    for page in _query(token, database_id, body):
        props = page["properties"]
        fu = _date_start(props.get("Next Follow-Up", {}))
        if not fu:
            continue
        try:
            fu_date = _dt.strptime(fu[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        yield {
            "id": page["id"],
            "name": _title(props.get("Lead Name", {})),
            "priority": _select_name(props.get("Priority", {})),
            "status": _select_name(props.get("Status", {})),
            "fu_date": fu_date,
        }


def update_simple_properties(token, page_id, updates):
    """Patch one or more properties on a page.

    updates: dict of {property_name: value}. Only properties in
    _PROPERTY_SHAPES are supported — caller gets KeyError for anything else,
    which surfaces typos at dev time rather than silently no-op'ing.
    """
    payload = {"properties": {
        name: _PROPERTY_SHAPES[name](value)
        for name, value in updates.items()
    }}
    r = requests.patch(
        f"{API}/pages/{page_id}",
        json=payload, headers=_headers(token), timeout=30,
    )
    r.raise_for_status()


def append_note(token, page_id, line):
    """Append `line` (on its own line) to the page's Notes property."""
    r = requests.get(f"{API}/pages/{page_id}", headers=_headers(token), timeout=30)
    r.raise_for_status()
    current = _rich_text(r.json()["properties"].get("Notes", {}))
    new = (current + "\n" + line) if current else line

    r = requests.patch(
        f"{API}/pages/{page_id}",
        json={"properties": {"Notes": {"rich_text": _to_rich_text_chunks(new)}}},
        headers=_headers(token), timeout=30,
    )
    r.raise_for_status()
