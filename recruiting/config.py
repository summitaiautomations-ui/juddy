"""Load recruiting-digest secrets and settings from .env at the repo root.

Reuses the same .env the outreach/ project uses — NOTION_TOKEN and the
Gmail app-password live there already. Only two recruiting-specific keys
are new: NOTION_RECRUITING_DB and RECRUITING_DIGEST_TO.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# The Recruiting Pipeline database (Justin's Notion). Hard-coded as the
# default so the digest runs with nothing but a token configured; override
# in .env if the database is ever rebuilt.
DEFAULT_RECRUITING_DB = "e0a85bb7-a051-4af1-b549-92580e4bddb5"


def _require(name):
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def load_config():
    # Recipients: prefer the recruiting-specific list, fall back to the
    # shared DIGEST_TO_EMAIL the outreach digest already uses.
    to_raw = (os.environ.get("RECRUITING_DIGEST_TO")
              or os.environ.get("DIGEST_TO_EMAIL", ""))
    return {
        "notion": {
            "token": _require("NOTION_TOKEN"),
            "database_id": (os.environ.get("NOTION_RECRUITING_DB", "").strip()
                            or DEFAULT_RECRUITING_DB),
        },
        "gmail": {
            "email": os.environ.get("GMAIL_EMAIL", ""),
            "app_password": os.environ.get("GMAIL_APP_PASSWORD", ""),
        },
        "digest": {
            "to_emails": [e.strip() for e in to_raw.split(",") if e.strip()],
        },
        # The number of hires that counts as "mission accomplished".
        "hiring_goal": int(os.environ.get("HIRING_GOAL", "12")),
        # Target caliber: each hire should have produced this many units/month
        # last year (2-3 u/mo). 2025 Units is an annual figure, so u/mo = /12.
        "target_upm_min": float(os.environ.get("TARGET_UPM_MIN", "2")),
        "target_upm_high": float(os.environ.get("TARGET_UPM_HIGH", "3")),
        # A follow-up older than this many days is flagged as overdue.
        "overdue_grace_days": int(os.environ.get("RECRUITING_OVERDUE_DAYS", "0")),
    }
