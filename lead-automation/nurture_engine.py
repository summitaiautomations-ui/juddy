#!/usr/bin/env python3
"""
Nurture Engine v2 — Multi-tier SMS nurture sequences with auto-promote/demote.
Tracks: hot, warm, cold, active_preapproval, past_client.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import load_config
from sms import send_sms_once

SCRIPT_DIR = Path(__file__).resolve().parent
TRACKS_PATH = SCRIPT_DIR / "nurture_tracks.json"
CONTACTS_PATH = SCRIPT_DIR / "nurture_contacts.json"
NURTURE_LOG_PATH = SCRIPT_DIR / "nurture_log.json"


def load_json(path, default=None):
    path = Path(path)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_tracks():
    return load_json(TRACKS_PATH, {}).get("tracks", {})


def load_contacts():
    return load_json(CONTACTS_PATH, {"contacts": []})


def save_contacts(data):
    save_json(CONTACTS_PATH, data)


def log_nurture(contact, step_id, status_code, response):
    logs = load_json(NURTURE_LOG_PATH, [])
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "contact_name": contact.get("name", ""),
        "contact_phone": contact.get("phone", ""),
        "track": contact.get("track", ""),
        "step": step_id,
        "status": status_code,
        "response": response,
    })
    save_json(NURTURE_LOG_PATH, logs)


def send_sms(config, to_phone, message, *, source="nurture_engine"):
    return send_sms_once(config, to_phone, message, source=source)


def format_message(template, contact):
    full_name = contact.get("name", "there")
    first_name = full_name.split()[0] if full_name and full_name != "there" else "there"
    return template.format(
        name=first_name,
        phone=contact.get("phone", ""),
        email=contact.get("email", ""),
        city=contact.get("city", ""),
        state=contact.get("state", ""),
        property_value=contact.get("property_value", ""),
        credit=contact.get("credit", ""),
        income=contact.get("income", ""),
        down_payment=contact.get("down_payment", ""),
        first_time=contact.get("first_time", ""),
        has_agent=contact.get("has_agent", ""),
    )


def send_nudge(config, message, *, source="nurture_engine:nudge"):
    return send_sms(config, config["justin"]["personal_cell"], message, source=source)


def _digits(value):
    digits = "".join(c for c in str(value) if c.isdigit())
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    return digits


def process_contacts(config, tracks, contacts_data):
    now = datetime.now(timezone.utc)
    updated = False

    for contact in contacts_data.get("contacts", []):
        if not contact.get("active", True):
            continue

        track_id = contact.get("track", "")
        track = tracks.get(track_id)
        if not track:
            continue

        try:
            enrolled_at = datetime.fromisoformat(contact["enrolled_at"])
        except (KeyError, ValueError):
            continue
        completed_steps = contact.get("completed_steps", [])

        for step in track["steps"]:
            if step["id"] in completed_steps:
                continue

            fire_at = enrolled_at.timestamp() + step["delay_seconds"]
            if now.timestamp() < fire_at:
                continue

            msg = format_message(step["message"], contact)

            source = f"nurture_engine:{track_id}/{step['id']}"
            if step["channel"] == "sms":
                print(f"[{now.isoformat()}] Sending {track_id}/{step['id']} to {contact['name']}", flush=True)
                status, resp = send_sms(config, contact["phone"], msg, source=source)
                log_nurture(contact, step["id"], status, resp)
            elif step["channel"] == "nudge":
                status, resp = send_nudge(config, msg, source=source)
                log_nurture(contact, step["id"], status, resp)

            completed_steps.append(step["id"])
            contact["completed_steps"] = completed_steps
            # Persist immediately so a crash between sends cannot re-fire a
            # step that already went out. send_sms_once gives us hard dedupe
            # at the API boundary, but saving per-send keeps the in-memory
            # contact state honest if the loop dies mid-tick.
            save_contacts(contacts_data)
            updated = True

            if len(completed_steps) >= len(track["steps"]):
                contact["active"] = False
                contact["completed_at"] = now.isoformat()

            break

    if updated:
        save_contacts(contacts_data)


def check_demotions(contacts_data):
    """Hot→Warm after 14d ghost; Warm→Cold after 30d ghost."""
    now = datetime.now(timezone.utc)
    updated = False
    nurture_logs = load_json(NURTURE_LOG_PATH, [])

    for contact in contacts_data.get("contacts", []):
        if not contact.get("active", False):
            continue

        track = contact.get("track", "")
        phone_digits = _digits(contact.get("phone", ""))

        last_sms_time = None
        for entry in reversed(nurture_logs):
            if _digits(entry.get("contact_phone", "")) == phone_digits and entry.get("status") == 201:
                try:
                    last_sms_time = datetime.fromisoformat(entry["timestamp"])
                except ValueError:
                    pass
                break

        if not last_sms_time:
            try:
                last_sms_time = datetime.fromisoformat(contact["enrolled_at"])
            except (KeyError, ValueError):
                continue

        days_since = (now - last_sms_time).total_seconds() / 86400

        if track == "hot" and days_since >= 14:
            contact["track"] = "warm"
            contact["enrolled_at"] = now.isoformat()
            contact["completed_steps"] = ["welcome", "nudge_justin"]
            contact["demoted_from"] = "hot"
            contact["demoted_at"] = now.isoformat()
            contact["demoted_reason"] = f"no_response_{int(days_since)}_days"
            updated = True
        elif track == "warm" and days_since >= 30:
            contact["track"] = "cold"
            contact["enrolled_at"] = now.isoformat()
            contact["completed_steps"] = ["welcome", "nudge_justin"]
            contact["demoted_from"] = "warm"
            contact["demoted_at"] = now.isoformat()
            contact["demoted_reason"] = f"no_response_{int(days_since)}_days"
            updated = True

    if updated:
        save_contacts(contacts_data)


def check_inbound_deactivation(config, contacts_data):
    """Cold→Warm on reply; hot/warm replies deactivate (direct contact mode)."""
    if not contacts_data.get("last_inbound_id"):
        try:
            url = "https://api-app2.simpletexting.com/v2/api/messages?type=INBOX&size=1"
            headers = {
                "Authorization": f"Bearer {config['simpletexting']['api_key']}",
                "Content-Type": "application/json",
            }
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("content"):
                    contacts_data["last_inbound_id"] = data["content"][0]["id"]
                    save_contacts(contacts_data)
        except Exception as e:
            print(f"Inbound init error: {e}", flush=True)
        return

    try:
        url = "https://api-app2.simpletexting.com/v2/api/messages?type=INBOX&size=20"
        headers = {
            "Authorization": f"Bearer {config['simpletexting']['api_key']}",
            "Content-Type": "application/json",
        }
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return

        data = resp.json()
        messages = data.get("content", [])
        if not messages:
            return

        new_inbound = []
        for msg in messages:
            if msg["id"] == contacts_data["last_inbound_id"]:
                break
            if msg.get("directionType") == "MO":
                new_inbound.append(msg)

        if not new_inbound:
            return

        contacts_data["last_inbound_id"] = messages[0]["id"]

        for msg in reversed(new_inbound):
            phone = msg.get("contactPhone", "")
            phone_digits = _digits(phone)
            text = msg.get("text", "(no text)")

            for contact in contacts_data.get("contacts", []):
                if contact.get("contact_type", "lead") != "lead":
                    continue
                if _digits(contact.get("phone", "")) != phone_digits:
                    continue

                track = contact.get("track", "")
                now_iso = datetime.now(timezone.utc).isoformat()

                if track == "cold" and contact.get("active", False):
                    contact["track"] = "warm"
                    contact["enrolled_at"] = now_iso
                    contact["completed_steps"] = ["welcome", "nudge_justin"]
                    contact["promoted_from"] = "cold"
                    contact["promoted_at"] = now_iso
                    contact["promoted_reason"] = "inbound_reply"
                    alert = (
                        f"⬆️ Lead PROMOTED to Warm!\nFrom: {contact['name']} ({phone})\n"
                        f"Message: {text}\n\nMoved Cold → Warm."
                    )
                    send_sms(config, config["justin"]["personal_cell"], alert, source="nurture_engine:inbound_alert")
                elif contact.get("active", False):
                    contact["active"] = False
                    contact["deactivated_reason"] = "inbound_reply"
                    contact["deactivated_at"] = now_iso
                    alert = (
                        f"💬 Lead replied!\nFrom: {contact['name']} ({phone})\n"
                        f"Message: {text}\n\n✅ Auto-stopped nurture."
                    )
                    send_sms(config, config["justin"]["personal_cell"], alert, source="nurture_engine:inbound_alert")

        save_contacts(contacts_data)
    except Exception as e:
        print(f"Inbound check error: {e}", flush=True)


def add_contact(name, phone, track, **kwargs):
    contacts_data = load_contacts()
    phone_digits = _digits(phone)

    for c in contacts_data.get("contacts", []):
        if _digits(c.get("phone", "")) == phone_digits and c.get("active", False):
            print(f"Contact {name} ({phone}) already active in {c['track']} track")
            return False

    contact = {
        "name": name,
        "phone": phone,
        "track": track,
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "completed_steps": [],
        "contact_type": kwargs.pop("contact_type", "lead"),
        **kwargs,
    }

    contacts_data.setdefault("contacts", []).append(contact)
    save_contacts(contacts_data)
    print(f"Added {name} ({phone}) to {track} track")
    return True


def deactivate_contact(phone):
    contacts_data = load_contacts()
    phone_digits = _digits(phone)

    for contact in contacts_data.get("contacts", []):
        if _digits(contact.get("phone", "")) == phone_digits and contact.get("active", False):
            contact["active"] = False
            contact["deactivated_reason"] = "manual"
            contact["deactivated_at"] = datetime.now(timezone.utc).isoformat()
            save_contacts(contacts_data)
            print(f"Deactivated {contact['name']} ({phone})")
            return True

    print(f"No active contact found for {phone}")
    return False


def reactivate_contact(phone, track=None):
    contacts_data = load_contacts()
    phone_digits = _digits(phone)

    for contact in contacts_data.get("contacts", []):
        if _digits(contact.get("phone", "")) == phone_digits:
            contact["active"] = True
            contact["enrolled_at"] = datetime.now(timezone.utc).isoformat()
            contact["completed_steps"] = []
            if track:
                contact["track"] = track
            for k in ("deactivated_reason", "deactivated_at", "completed_at"):
                contact.pop(k, None)
            save_contacts(contacts_data)
            print(f"Reactivated {contact['name']} ({phone}) on {contact['track']} track")
            return True

    print(f"No contact found for {phone}")
    return False


def list_contacts():
    contacts_data = load_contacts()
    tracks = load_tracks()

    for contact in contacts_data.get("contacts", []):
        status = "✅ Active" if contact.get("active", False) else "⏸️ Inactive"
        track_name = tracks.get(contact.get("track", ""), {}).get("name", contact.get("track", ""))
        completed = len(contact.get("completed_steps", []))
        total = len(tracks.get(contact.get("track", ""), {}).get("steps", []))
        print(f"  {status} | {contact['name']} ({contact['phone']}) | {track_name} | {completed}/{total} steps")


def run_daemon(interval=60):
    config = load_config()
    tracks = load_tracks()
    demotion_counter = 0

    print(f"Nurture Engine v2 started. Checking every {interval}s...", flush=True)
    print(f"Tracks loaded: {', '.join(tracks.keys())}", flush=True)

    while True:
        try:
            contacts_data = load_contacts()
            check_inbound_deactivation(config, contacts_data)
            process_contacts(config, tracks, contacts_data)

            demotion_counter += 1
            if demotion_counter >= 30:
                demotion_counter = 0
                check_demotions(load_contacts())
        except Exception as e:
            print(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: {e}", flush=True)

        sys.stdout.flush()
        time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "daemon":
        run_daemon()
    elif sys.argv[1] == "add":
        name = sys.argv[2]
        phone = sys.argv[3]
        track = sys.argv[4]
        kwargs = {}
        for arg in sys.argv[5:]:
            k, v = arg.split("=", 1)
            kwargs[k] = v
        add_contact(name, phone, track, **kwargs)
    elif sys.argv[1] == "deactivate":
        deactivate_contact(sys.argv[2])
    elif sys.argv[1] == "reactivate":
        track = sys.argv[3] if len(sys.argv) > 3 else None
        reactivate_contact(sys.argv[2], track)
    elif sys.argv[1] == "list":
        list_contacts()
    else:
        print(f"Unknown command: {sys.argv[1]}")
        sys.exit(1)
