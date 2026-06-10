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
            "to_email": os.environ.get("DIGEST_TO_EMAIL", ""),
        },
        "justin": {
            "personal_cell": os.environ.get("JUSTIN_PERSONAL_CELL", ""),
        },
        "birthday_message_template": os.environ.get(
            "BIRTHDAY_MESSAGE_TEMPLATE",
            "Hey {name} — happy early birthday!",
        ),
        "nudge_message_template": os.environ.get(
            "NUDGE_MESSAGE_TEMPLATE",
            "{name} replied — your turn.",
        ),
    }
