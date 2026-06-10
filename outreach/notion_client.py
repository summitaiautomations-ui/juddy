"""Minimal Notion client for the Mortgage Pipeline DB.

Fetches past-client records with DOB + phone, and appends activity lines
back to a record's Notes property.
"""

import requests

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

PAST_CLIENT_STATUSES = ("Funded", "Friends and Family")

# Notion caps rich_text content at 2000 chars per block.
NOTION_RICH_TEXT_LIMIT = 2000


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


def _to_rich_text_chunks(content):
    if len(content) <= NOTION_RICH_TEXT_LIMIT:
        return [{"type": "text", "text": {"content": content}}]
    return [
        {"type": "text", "text": {"content": content[i:i + NOTION_RICH_TEXT_LIMIT]}}
        for i in range(0, len(content), NOTION_RICH_TEXT_LIMIT)
    ]


def fetch_past_clients_with_birthday(token, database_id):
    """Yield every past-client page that has both a DOB and a Phone."""
    cursor = None
    while True:
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
        if cursor:
            body["start_cursor"] = cursor

        r = requests.post(
            f"{API}/databases/{database_id}/query",
            json=body, headers=_headers(token), timeout=30,
        )
        r.raise_for_status()
        data = r.json()

        for page in data["results"]:
            props = page["properties"]
            yield {
                "id": page["id"],
                "name": _title(props.get("Lead Name", {})),
                "phone": props.get("Phone", {}).get("phone_number"),
                "dob": (props.get("Date of Birth", {}).get("date") or {}).get("start"),
                "notes": _rich_text(props.get("Notes", {})),
            }

        if not data.get("has_more"):
            return
        cursor = data["next_cursor"]


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
