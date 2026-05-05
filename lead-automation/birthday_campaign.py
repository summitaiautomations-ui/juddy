#!/usr/bin/env python3
"""
Birthday campaign — sends a birthday freebie text 7 days before each
past client's birthday. Designed to be run daily via cron.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import requests

from config import load_config

SCRIPT_DIR = Path(__file__).resolve().parent
CONTACTS_PATH = SCRIPT_DIR / "nurture_contacts.json"
LOG_PATH = SCRIPT_DIR / "nurture_log.json"


def load_json(path, default=None):
    path = Path(path)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def send_sms(config, to_phone, message):
    url = "https://api-app2.simpletexting.com/v2/api/messages"
    headers = {
        "Authorization": f"Bearer {config['simpletexting']['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "contactPhone": to_phone,
        "accountPhone": config["simpletexting"]["account_phone"],
        "type": "SINGLE_SMS",
        "text": message,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    return resp.status_code, resp.text


def log_event(contact, status_code, response):
    logs = load_json(LOG_PATH, [])
    logs.append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "contact_name": contact.get("name", ""),
        "contact_phone": contact.get("phone", ""),
        "track": contact.get("track", ""),
        "step": "birthday_freebie_7d",
        "status": status_code,
        "response": response,
    })
    save_json(LOG_PATH, logs)


def already_sent_this_year(contact, year):
    logs = load_json(LOG_PATH, [])
    phone = str(contact.get("phone", ""))
    for entry in reversed(logs):
        if entry.get("step") != "birthday_freebie_7d":
            continue
        if str(entry.get("contact_phone", "")) != phone:
            continue
        if entry.get("timestamp", "").startswith(str(year)):
            return True
    return False


def first_name(full_name):
    parts = (full_name or "there").strip().split()
    return parts[0] if parts else "there"


def is_target_birthday(birthday_str, today):
    try:
        bday = datetime.strptime(birthday_str[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return False
    target = today + timedelta(days=7)
    return bday.month == target.month and bday.day == target.day


def main():
    config = load_config()
    contacts_data = load_json(CONTACTS_PATH, {"contacts": []})
    today = datetime.now()
    sent = 0
    skipped = 0

    template = config.get("birthday_freebie_text", "Hey {name} — happy early birthday!")

    for contact in contacts_data.get("contacts", []):
        if contact.get("contact_type") != "past_client":
            continue
        if contact.get("active") is False:
            continue
        if not contact.get("birthday"):
            continue
        if not contact.get("phone"):
            skipped += 1
            continue
        if not is_target_birthday(contact["birthday"], today):
            continue
        if already_sent_this_year(contact, today.year):
            skipped += 1
            continue

        msg = template.format(name=first_name(contact.get("name", "there")))
        print(f"Sending birthday freebie text to {contact.get('name')} ({contact.get('phone')})")
        status, resp = send_sms(config, contact["phone"], msg)
        log_event(contact, status, resp)

        if 200 <= status < 300:
            sent += 1
        else:
            print(f"  Failed: HTTP {status}")

    print(f"Done. Sent: {sent}, skipped: {skipped}")


if __name__ == "__main__":
    main()
