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


class NotionAccessError(RuntimeError):
    pass


def _check(r, database_id):
    """Turn Notion's terse 401/403/404 into an actionable message."""
    if r.status_code in (401, 403, 404):
        raise NotionAccessError(
            f"Notion returned {r.status_code} for the Recruiting Pipeline DB "
            f"({database_id}).\n"
            "  In Notion this almost always means the integration behind your "
            "NOTION_TOKEN has not been given access to this database.\n"
            "  Fix: open the Recruiting Pipeline database in Notion → top-right "
            "••• menu → Connections → add the same integration you use for the "
            "Mortgage Pipeline, then re-run.\n"
            "  (401 instead means the token itself is wrong.)"
        )
    r.raise_for_status()


def whoami(token):
    """Return the integration's display name (Notion bot user) for this token."""
    r = requests.get(f"{API}/users/me", headers=_headers(token), timeout=30)
    if r.status_code == 401:
        raise NotionAccessError("401 from Notion — NOTION_TOKEN is invalid.")
    r.raise_for_status()
    data = r.json()
    bot = data.get("name") or "(unnamed integration)"
    owner = (((data.get("bot") or {}).get("owner") or {}).get("workspace_name"))
    return bot, owner


def db_meta(token, database_id):
    """Fetch the database object (title etc.); raises NotionAccessError on 4xx."""
    r = requests.get(
        f"{API}/databases/{database_id}",
        headers=_headers(token), timeout=30,
    )
    _check(r, database_id)
    return r.json()


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
        _check(r, database_id)
        data = r.json()
        for page in data["results"]:
            yield _flatten(page)
        if not data.get("has_more"):
            return
        cursor = data["next_cursor"]
