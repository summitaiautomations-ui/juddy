"""Minimal Notion client for the Mortgage Pipeline DB.

Fetches past-client records with DOB + phone, finds records by phone or
email, creates new lead records from Realtor.com data, updates simple
properties (date, select), and appends activity lines to Notes.
"""

from datetime import datetime, timedelta

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


_LOAN_TYPE_MAP = {
    "conventional": "Conventional",
    "fha": "FHA",
    "va": "VA",
    "usda": "USDA",
    "jumbo": "Jumbo",
}


def _safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def create_lead(token, database_id, lead, summary_notes):
    """Create a new pipeline page from a parsed Realtor.com lead.

    Pre-fills Lead Name, Phone, Email, Status=Lead, Priority=Hot,
    Lead Source=Realtor.com, Date Added, Last Contact, Loan Type
    (if mappable), Loan Amount, Property Address, and Notes.

    Returns the new page ID.
    """
    today = datetime.now().date().isoformat()
    name = lead.get("name") or "(unknown)"
    phone = lead.get("phone") or ""
    email_addr = lead.get("email") or ""

    properties = {
        "Lead Name": {"title": [{"type": "text", "text": {"content": name}}]},
        "Status": {"select": {"name": "Lead"}},
        "Priority": {"select": {"name": "Hot"}},
        "Lead Source": {"select": {"name": "Realtor.com"}},
        "Date Added": {"date": {"start": today}},
        "Last Contact": {"date": {"start": today}},
    }

    if phone:
        properties["Phone"] = {"phone_number": phone}
    if email_addr:
        properties["Email"] = {"email": email_addr}

    loan_type = _LOAN_TYPE_MAP.get((lead.get("loan_product") or "").lower())
    if loan_type:
        properties["Loan Type"] = {"select": {"name": loan_type}}

    property_value = _safe_int(lead.get("property_value"))
    if property_value:
        properties["Loan Amount"] = {"number": property_value}

    address_parts = [lead.get("city", ""), lead.get("state", ""), lead.get("zip", "")]
    address = ", ".join(p for p in address_parts if p)
    if address:
        properties["Property Address"] = {
            "rich_text": [{"type": "text", "text": {"content": address}}],
        }

    properties["Notes"] = {"rich_text": _to_rich_text_chunks(summary_notes)}

    r = requests.post(
        f"{API}/pages",
        json={"parent": {"database_id": database_id}, "properties": properties},
        headers=_headers(token), timeout=30,
    )
    r.raise_for_status()
    return r.json()["id"]


def find_leads_for_info_touch(token, database_id, today_date):
    """Yield leads added today that got their welcome but not the info touch.

    Driven entirely by the marker lines in the Notes property — no
    separate state file needed.
    """
    body = {
        "filter": {
            "and": [
                {"property": "Date Added", "date": {"equals": today_date.isoformat()}},
                {"property": "Notes", "rich_text": {"contains": "AUTO welcome SMS sent"}},
                {"property": "Notes", "rich_text": {"does_not_contain": "AUTO info touch SMS"}},
            ],
        },
        "page_size": 100,
    }
    for page in _query(token, database_id, body):
        yield _record_from_page(page)


def fetch_overdue_followups(token, database_id, today_date):
    """Yield active records whose Next Follow-Up is on or before today.

    Each record carries name, priority, status, loan amount, and fu_date so
    the digest can rank by days-overdue and at-risk commission.
    """
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
    for page in _query(token, database_id, body):
        props = page["properties"]
        fu = _date_start(props.get("Next Follow-Up", {}))
        if not fu:
            continue
        try:
            fu_date = datetime.strptime(fu[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        yield {
            "id": page["id"],
            "name": _title(props.get("Lead Name", {})),
            "priority": _select_name(props.get("Priority", {})),
            "status": _select_name(props.get("Status", {})),
            "loan": props.get("Loan Amount", {}).get("number"),
            "fu_date": fu_date,
        }


def fetch_upcoming_closings(token, database_id, today_date, window_days=14):
    """Yield records with Closing Date within today..today+window_days."""
    end_date = today_date + timedelta(days=window_days)
    body = {
        "filter": {
            "and": [
                {"property": "Closing Date", "date": {"on_or_after": today_date.isoformat()}},
                {"property": "Closing Date", "date": {"on_or_before": end_date.isoformat()}},
                {"property": "Priority", "select": {"does_not_equal": "Dead"}},
            ],
        },
        "sorts": [{"property": "Closing Date", "direction": "ascending"}],
        "page_size": 100,
    }
    for page in _query(token, database_id, body):
        props = page["properties"]
        close = _date_start(props.get("Closing Date", {}))
        if not close:
            continue
        try:
            close_date = datetime.strptime(close[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        yield {
            "id": page["id"],
            "name": _title(props.get("Lead Name", {})),
            "priority": _select_name(props.get("Priority", {})),
            "status": _select_name(props.get("Status", {})),
            "loan": props.get("Loan Amount", {}).get("number"),
            "closing_date": close_date,
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
