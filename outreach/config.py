"""Load secrets from .env at the repo root."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def _require(name):
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def load_config():
    return {
        "simpletexting": {
            "api_key": _require("SIMPLETEXTING_API_KEY"),
            "account_phone": _require("SIMPLETEXTING_ACCOUNT_PHONE"),
        },
        "notion": {
            "token": _require("NOTION_TOKEN"),
            "database_id": _require("NOTION_MORTGAGE_PIPELINE_DB"),
        },
        "gmail": {
            "email": os.environ.get("GMAIL_EMAIL", ""),
            "app_password": os.environ.get("GMAIL_APP_PASSWORD", ""),
        },
        "digest": {
            "to_emails": [
                e.strip() for e in os.environ.get("DIGEST_TO_EMAIL", "").split(",")
                if e.strip()
            ],
        },
        "justin": {
            "personal_cell": os.environ.get("JUSTIN_PERSONAL_CELL", ""),
        },
        "birthday_message_template": os.environ.get(
            "BIRTHDAY_MESSAGE_TEMPLATE",
            "Hi - It's Justin Neal from my work cell. Happy early birthday {name}!",
        ),
        "nudge_message_template": os.environ.get(
            "NUDGE_MESSAGE_TEMPLATE",
            "{name} replied — your turn.",
        ),
        # Empty default — welcome SMS is suppressed until Justin sets this
        # in .env. New leads are still added to Notion either way.
        "welcome_message_template": os.environ.get("WELCOME_MESSAGE_TEMPLATE", ""),
        # Empty default — Day-1 info touch is suppressed until set.
        "info_touch_message_template": os.environ.get("INFO_TOUCH_MESSAGE_TEMPLATE", ""),
        # Business-hours window for the info touch (24-hour local time).
        # 9 AM – 9 PM per Justin's preference; welcome SMS is exempt.
        "business_hours_start": os.environ.get("BUSINESS_HOURS_START", "9"),
        "business_hours_end": os.environ.get("BUSINESS_HOURS_END", "21"),
    }
