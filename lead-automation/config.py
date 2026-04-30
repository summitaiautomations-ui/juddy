"""Config loader: env vars for secrets, config.json for templates/delays."""

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent


def _load_templates():
    path = SCRIPT_DIR / "config.json"
    if not path.exists():
        path = SCRIPT_DIR / "config.example.json"
    with open(path) as f:
        return json.load(f)


def _require(name):
    val = os.environ.get(name, "")
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def load_config():
    templates = _load_templates()
    return {
        "gmail": {
            "email": os.environ.get("GMAIL_EMAIL", ""),
            "app_password": os.environ.get("GMAIL_APP_PASSWORD", ""),
        },
        "simpletexting": {
            "api_key": os.environ.get("SIMPLETEXTING_API_KEY", ""),
            "account_phone": os.environ.get("SIMPLETEXTING_ACCOUNT_PHONE", ""),
        },
        "justin": {
            "personal_cell": os.environ.get("JUSTIN_PERSONAL_CELL", ""),
        },
        "dashboard": {
            "user": os.environ.get("DASHBOARD_USER", "leadnurture"),
            "password": os.environ.get("DASHBOARD_PASS", ""),
            "port": int(os.environ.get("DASHBOARD_PORT", "18790")),
        },
        **templates,
    }
