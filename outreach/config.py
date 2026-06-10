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
        "birthday_message_template": os.environ.get(
            "BIRTHDAY_MESSAGE_TEMPLATE",
            "Hey {name} — happy early birthday!",
        ),
    }
