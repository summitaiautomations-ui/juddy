"""Load secrets from ~/juddy/.env (shared with outreach)."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def load():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Missing ANTHROPIC_API_KEY in ~/juddy/.env. "
            "Get one at https://console.anthropic.com/settings/keys"
        )
    return {"anthropic_api_key": api_key}
