"""
Wrappers around the Notion API for Jarvis's tool calls.

Each function returns a small dict (or list of dicts) sized for a butler reply,
not the firehose. Keeps the Claude tool-use turn cheap and the spoken answer
short.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from typing import Any

import requests

NOTION_VERSION = "2022-06-28"
DATABASE_ID = os.environ.get(
    "NOTION_DATABASE_ID", "e0a85bb7a0514af1b54992580e4bddb5"
)

# Stage -> auto-priority rule (mirrors the dashboard).
STAGE_PRIORITY = {"Offer": "Hot", "Interview": "Warm"}
STAGES = [
    "Initial Outreach", "Conversation", "Interview", "Offer", "Hired", "Passed",
]


def _headers() -> dict[str, str]:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_TOKEN not set")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _prop(p: dict | None) -> Any:
    if not p:
        return None
    t = p.get("type")
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in p.get(t, []))
    if t == "select":
        return p["select"]["name"] if p.get("select") else None
    if t == "number":
        return p.get("number")
    if t == "date":
        return p["date"]["start"] if p.get("date") else None
    if t in ("phone_number", "email", "url"):
        return p.get(t)
    return None


def _flatten(page: dict) -> dict:
    """Project a Notion page into the small shape Jarvis uses."""
    p = page.get("properties", {})
    return {
        "id": page["id"].replace("-", ""),
        "name": _prop(p.get("Candidate Name")),
        "stage": _prop(p.get("Stage")),
        "priority": _prop(p.get("Priority")),
        "units": _prop(p.get("2025 Units")),
        "volume": _prop(p.get("2025 Volume")),
        "company": _prop(p.get("Current Company")),
        "city": _prop(p.get("City")),
        "state": _prop(p.get("State")),
        "nmls": _prop(p.get("NMLS #")),
        "phone": _prop(p.get("Phone")),
        "recruiter": _prop(p.get("Assigned Recruiter")),
        "next_follow_up": _prop(p.get("Next Follow-Up")),
        "last_contact": _prop(p.get("Last Contact")),
        "notes": _prop(p.get("Notes")),
        "url": page.get("url"),
    }


# ---------- queries ----------


def search_candidate(query: str, limit: int = 3) -> list[dict]:
    """Find candidates whose name contains `query`. Case-insensitive."""
    body = {
        "filter": {
            "property": "Candidate Name",
            "title": {"contains": query},
        },
        "page_size": limit,
    }
    res = requests.post(
        f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
        headers=_headers(), json=body, timeout=10,
    )
    res.raise_for_status()
    return [_flatten(p) for p in res.json().get("results", [])]


def get_pipeline_summary() -> dict:
    """Roll up active pipeline by stage."""
    all_pages: list[dict] = []
    cursor: str | None = None
    while True:
        body: dict = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        res = requests.post(
            f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
            headers=_headers(), json=body, timeout=15,
        )
        res.raise_for_status()
        data = res.json()
        all_pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    by_stage: dict[str, dict[str, float]] = {
        s: {"count": 0, "volume": 0.0, "units": 0.0} for s in STAGES
    }
    hot = 0
    for page in all_pages:
        r = _flatten(page)
        s = r["stage"]
        if s in by_stage:
            by_stage[s]["count"] += 1
            by_stage[s]["volume"] += r["volume"] or 0
            by_stage[s]["units"] += r["units"] or 0
        if r["priority"] == "Hot" and s not in ("Passed", "Hired"):
            hot += 1
    return {
        "total": len(all_pages),
        "hot": hot,
        "by_stage": by_stage,
    }


def get_followups(within_days: int = 7) -> list[dict]:
    """Active candidates whose Next Follow-Up is <= today + within_days."""
    cutoff = (date.today() + timedelta(days=within_days)).isoformat()
    body = {
        "filter": {
            "and": [
                {"property": "Next Follow-Up", "date": {"on_or_before": cutoff}},
                {"property": "Stage", "select": {"does_not_equal": "Passed"}},
                {"property": "Stage", "select": {"does_not_equal": "Hired"}},
            ]
        },
        "sorts": [{"property": "Next Follow-Up", "direction": "ascending"}],
        "page_size": 25,
    }
    res = requests.post(
        f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
        headers=_headers(), json=body, timeout=10,
    )
    res.raise_for_status()
    today = date.today().isoformat()
    out = []
    for page in res.json().get("results", []):
        r = _flatten(page)
        r["overdue"] = r["next_follow_up"] and r["next_follow_up"] < today
        out.append(r)
    return out


# ---------- mutations ----------


def _set_prop(props: dict, name: str, value, *, dollar: bool = False) -> None:
    if value is None or value == "":
        return
    if name == "Candidate Name":
        props[name] = {"title": [{"text": {"content": str(value)}}]}
    elif name in ("Notes", "Engagement Notes", "Current Company",
                  "City", "State", "NMLS #", "Referral Source"):
        props[name] = {"rich_text": [{"text": {"content": str(value)}}]}
    elif name in ("2025 Units", "2025 Volume"):
        props[name] = {"number": float(value)}
    elif name in ("Stage", "Priority", "Source", "Assigned Recruiter",
                  "Role Type", "Nurture Stage", "Last Touchpoint Type",
                  "Preferred Channel"):
        props[name] = {"select": {"name": str(value)}}
    elif name in ("Next Follow-Up", "Last Contact", "Date Added"):
        props[name] = {"date": {"start": str(value)}}
    elif name == "Phone":
        props[name] = {"phone_number": str(value)}
    elif name == "Email":
        props[name] = {"email": str(value)}


def create_candidate(**fields) -> dict:
    """Add a new candidate page. `name` (str) is required; the rest is optional."""
    name = fields.pop("name", None)
    if not name:
        raise ValueError("name is required")
    fields.setdefault("Stage", "Initial Outreach")
    fields.setdefault("Nurture Stage", "Not Started")
    fields.setdefault("Date Added", date.today().isoformat())

    props: dict = {}
    _set_prop(props, "Candidate Name", name)
    # Friendly aliases for the common ones.
    alias = {
        "units": "2025 Units", "volume": "2025 Volume", "company": "Current Company",
        "nmls": "NMLS #", "phone": "Phone", "email": "Email", "city": "City",
        "state": "State", "recruiter": "Assigned Recruiter",
        "stage": "Stage", "priority": "Priority", "notes": "Notes",
        "source": "Source", "referral_source": "Referral Source",
        "next_follow_up": "Next Follow-Up", "role": "Role Type",
        "nurture": "Nurture Stage", "date_added": "Date Added",
    }
    for k, v in list(fields.items()):
        prop_name = alias.get(k, k)
        _set_prop(props, prop_name, v)

    body = {
        "parent": {"database_id": DATABASE_ID},
        "properties": props,
    }
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_headers(), json=body, timeout=10,
    )
    res.raise_for_status()
    return _flatten(res.json())


def update_candidate(page_id: str, **fields) -> dict:
    """Update fields on an existing page. `page_id` is the Notion page UUID
    (with or without dashes)."""
    alias = {
        "units": "2025 Units", "volume": "2025 Volume", "company": "Current Company",
        "nmls": "NMLS #", "phone": "Phone", "email": "Email", "city": "City",
        "state": "State", "recruiter": "Assigned Recruiter",
        "stage": "Stage", "priority": "Priority", "notes": "Notes",
        "name": "Candidate Name", "next_follow_up": "Next Follow-Up",
        "last_contact": "Last Contact", "engagement": "Engagement Notes",
    }
    props: dict = {}
    for k, v in fields.items():
        _set_prop(props, alias.get(k, k), v)
    res = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(), json={"properties": props}, timeout=10,
    )
    res.raise_for_status()
    return _flatten(res.json())


def move_stage(page_id: str, stage: str) -> dict:
    """Move a candidate to a new stage and apply the auto-priority rule
    (Offer => Hot, Interview => Warm, Passed => clear)."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    props: dict = {"Stage": {"select": {"name": stage}}}
    if stage == "Passed":
        props["Priority"] = {"select": None}
    elif stage in STAGE_PRIORITY:
        props["Priority"] = {"select": {"name": STAGE_PRIORITY[stage]}}
    res = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(), json={"properties": props}, timeout=10,
    )
    res.raise_for_status()
    return _flatten(res.json())
