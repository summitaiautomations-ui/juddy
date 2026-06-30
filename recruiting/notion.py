"""Minimal Notion reader for the Recruiting Pipeline DB.

Pulls every candidate page and flattens the properties the digest cares
about into plain dicts. Mirrors the style of outreach/notion_client.py but
is self-contained so the recruiting module has no cross-project imports.
"""

from datetime import date

import requests

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": VERSION,
        "Content-Type": "application/json",
    }


def _title(prop):
    return "".join(rt.get("plain_text", "") for rt in (prop or {}).get("title", [])).strip()


def _text(prop):
    return "".join(rt.get("plain_text", "") for rt in (prop or {}).get("rich_text", [])).strip()


def _select(prop):
    return ((prop or {}).get("select") or {}).get("name")


def _date(prop):
    start = ((prop or {}).get("date") or {}).get("start")
    if not start:
        return None
    # Notion dates may be "2026-06-30" or a full ISO datetime; keep the day.
    try:
        return date.fromisoformat(start[:10])
    except ValueError:
        return None


def _number(prop):
    return (prop or {}).get("number")


def _flatten(page):
    p = page.get("properties", {})
    return {
        "id": page.get("id"),
        "url": page.get("url"),
        "name": _title(p.get("Candidate Name")) or "(unnamed)",
        "stage": _select(p.get("Stage")),
        "recruiter": _select(p.get("Assigned Recruiter")),
        "priority": _select(p.get("Priority")),
        "role": _select(p.get("Role Type")),
        "company": _text(p.get("Current Company")),
        "city": _text(p.get("City")),
        "state": _text(p.get("State")),
        "source": _select(p.get("Source")),
        "units_2025": _number(p.get("2025 Units")),
        "volume_2025": _number(p.get("2025 Volume")),
        "next_followup": _date(p.get("Next Follow-Up")),
        "last_contact": _date(p.get("Last Contact")),
        "date_added": _date(p.get("Date Added")),
    }


def fetch_candidates(token, database_id):
    """Yield a flat dict for every page in the recruiting database."""
    body = {"page_size": 100}
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
            yield _flatten(page)
        if not data.get("has_more"):
            return
        cursor = data["next_cursor"]
