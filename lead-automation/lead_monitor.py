#!/usr/bin/env python3
"""
Lead Monitor — Scans Gmail for new Realtor.com leads, sends welcome text via
SimpleTexting, nudges Justin via SMS, enrolls into nurture engine.
"""

import email
import imaplib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from email import policy
from pathlib import Path

import requests

from config import load_config
from nurture_engine import add_contact
from sms import send_sms_once

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_PATH = SCRIPT_DIR / "state.json"
LOG_PATH = SCRIPT_DIR / "lead_log.json"


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"processed_lead_ids": [], "last_check": None, "pending_followups": []}


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def log_lead(lead_data, actions):
    logs = []
    if LOG_PATH.exists():
        with open(LOG_PATH) as f:
            logs = json.load(f)
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lead": lead_data,
        "actions": actions,
    })
    with open(LOG_PATH, "w") as f:
        json.dump(logs, f, indent=2)


def parse_lead_email(msg):
    """Parse a Realtor.com lead notification email into structured data."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()

    if not body:
        return None

    def extract(pattern, text, default=""):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else default

    lead = {
        "lead_id": extract(r"\*Lead ID:\*\s*(\S+)", body),
        "lead_date": extract(r"\*Lead Date:\*\s*(.+?)(?:\s*\*)", body),
        "name": extract(r"\*\s*Lead Name:\*\s*(.+)", body),
        "phone": extract(r"\*Phone Number:\*\s*(\d+)", body),
        "email": extract(r"\*Email:\*\s*(\S+)", body),
        "credit": extract(r"\*Credit Rating:\*\s*(\S+)", body),
        "county_state": extract(r"\*Property County and State:\*\s*(.+)", body),
        "zip": extract(r"\*Property Zip:\*\s*(\d+)", body),
        "property_value": extract(r"\*Property Value:\*\s*(\d+)", body),
        "military": extract(r"\*Served in Military:\*\s*(\S+)", body),
        "bankruptcy": extract(r"\*Bankruptcy:\*\s*(\S+)", body),
        "loan_type": extract(r"\*Loan Type:\*\s*(\S+)", body),
        "has_agent": extract(r"\*Has Real Estate Agent:\*\s*(\S+)", body),
        "down_payment_pct": extract(r"\*Down Payment Percent:\*\s*(\d+)", body),
        "property_type": extract(r"\*Property Type:\*\s*(\S+)", body),
        "property_use": extract(r"\*Property Use:\*\s*(\S+)", body),
        "loan_product": extract(r"\*Loan Product:\*\s*(\S+)", body),
        "employment": extract(r"\*Employment Status:\*\s*(\S+)", body),
        "income": extract(r"\*Gross Income:\*\s*(\d+)", body),
        "first_time": extract(r"\*First Time purchase:\*\s*(\S+)", body),
        "living_situation": extract(r"\*Living Situation:\*\s*(\S+)", body),
        "purchase_status": extract(r"\*Purchase Status:\*\s*(\S+)", body),
        "down_payment": extract(r"\*Down Payment:\*\s*(\d+)", body),
        "city": extract(r"\*Property City:\*\s*(.+)", body),
    }

    if lead["county_state"]:
        parts = lead["county_state"].split(",")
        lead["state"] = parts[-1].strip() if len(parts) > 1 else ""
    else:
        lead["state"] = ""

    return lead if lead["lead_id"] and lead["phone"] else None


def send_sms(config, to_phone, message, *, source="lead_monitor"):
    return send_sms_once(config, to_phone, message, source=source)


def format_message(template, lead):
    full_name = lead.get("name", "there")
    first_name = full_name.split()[0] if full_name and full_name != "there" else "there"
    return template.format(
        name=first_name,
        phone=lead.get("phone", ""),
        email=lead.get("email", ""),
        city=lead.get("city", ""),
        state=lead.get("state", ""),
        property_value=lead.get("property_value", ""),
        credit=lead.get("credit", ""),
        income=lead.get("income", ""),
        down_payment=lead.get("down_payment", ""),
        first_time=lead.get("first_time", ""),
        has_agent=lead.get("has_agent", ""),
        lead_id=lead.get("lead_id", ""),
    )


def check_for_new_leads(config, state):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(config["gmail"]["email"], config["gmail"]["app_password"])
    mail.select("inbox")

    status, messages = mail.search(None, "FROM", '"realtor.com"')
    if status != "OK":
        mail.logout()
        return []

    ids = messages[0].split()
    new_leads = []

    for msg_id in ids:
        status, data = mail.fetch(msg_id, "(RFC822)")
        msg = email.message_from_bytes(data[0][1], policy=policy.default)
        lead = parse_lead_email(msg)

        if lead and lead["lead_id"] not in state["processed_lead_ids"]:
            new_leads.append(lead)

    mail.logout()
    return new_leads


def process_lead(config, lead):
    actions = []

    welcome_msg = format_message(config["welcome_text"], lead)
    print(f"[{datetime.now(timezone.utc).isoformat()}] Sending welcome text to {lead['name']} ({lead['phone']})")
    status_code, resp = send_sms(config, lead["phone"], welcome_msg, source="lead_monitor:welcome")
    actions.append({"type": "welcome_text", "to": lead["phone"], "status": status_code, "response": resp})
    print(f"  Welcome text sent: HTTP {status_code}")

    remaining_nudge = config["delays"]["nudge_text_seconds"] - config["delays"]["welcome_text_seconds"]
    if remaining_nudge > 0:
        print(f"  Waiting {remaining_nudge}s before sending nudge to Justin...")
        time.sleep(remaining_nudge)

    nudge_msg = format_message(config["nudge_text"], lead)
    print(f"  Sending call nudge to Justin ({config['justin']['personal_cell']})")
    status_code, resp = send_sms(config, config["justin"]["personal_cell"], nudge_msg, source="lead_monitor:nudge")
    actions.append({"type": "nudge_text", "to": config["justin"]["personal_cell"], "status": status_code, "response": resp})
    print(f"  Nudge sent: HTTP {status_code}")

    log_lead(lead, actions)

    try:
        add_contact(
            name=lead.get("name", "Unknown"),
            phone=lead.get("phone", ""),
            track="cold",
            email=lead.get("email", ""),
            city=lead.get("city", ""),
            state=lead.get("state", ""),
            property_value=lead.get("property_value", ""),
            credit=lead.get("credit", ""),
            income=lead.get("income", ""),
            down_payment=lead.get("down_payment", ""),
            first_time=lead.get("first_time", ""),
            has_agent=lead.get("has_agent", ""),
            lead_id=lead.get("lead_id", ""),
            contact_type="lead",
        )
        print(f"  Enrolled {lead['name']} in nurture engine (cold track)", flush=True)
    except Exception as e:
        print(f"  Nurture enrollment error: {e}", flush=True)

    return actions


def _digits(value):
    digits = "".join(c for c in str(value) if c.isdigit())
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    return digits


def check_inbound_replies(config, state):
    contacts_path = SCRIPT_DIR / "nurture_contacts.json"
    if "last_inbound_id" not in state:
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
                    state["last_inbound_id"] = data["content"][0]["id"]
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
            if msg["id"] == state["last_inbound_id"]:
                break
            if msg.get("directionType") == "MO":
                new_inbound.append(msg)

        if not new_inbound:
            return

        state["last_inbound_id"] = messages[0]["id"]

        contacts = []
        if contacts_path.exists():
            with open(contacts_path) as f:
                contacts = json.load(f).get("contacts", [])

        known_leads = {}
        for c in contacts:
            if c.get("contact_type", "lead") != "lead":
                continue
            digits = _digits(c.get("phone", ""))
            if len(digits) == 10:
                known_leads[digits] = c

        for msg in reversed(new_inbound):
            phone = msg.get("contactPhone", "unknown")
            text = msg.get("text", "(no text)")
            phone_digits = _digits(phone)

            lead = known_leads.get(phone_digits)
            if not lead:
                print(f"Non-lead reply ignored for {phone_digits}: {text}", flush=True)
                continue

            lead_name = f"{lead.get('name', phone_digits)} ({phone_digits})"
            alert = (
                f"💬 Lead replied!\nFrom: {lead_name}\nMessage: {text}\n\n"
                f"Reply in SimpleTexting or call {phone_digits}"
            )

            before = len(state.get("pending_followups", []))
            state["pending_followups"] = [
                fu for fu in state.get("pending_followups", [])
                if _digits(fu["lead"].get("phone", "")) != phone_digits
            ]
            removed = before - len(state["pending_followups"])
            if removed > 0:
                alert += f"\n\n✅ Auto-stopped {removed} scheduled follow-up(s)."

            send_sms(config, config["justin"]["personal_cell"], alert, source="lead_monitor:reply_alert")
    except Exception as e:
        print(f"Inbound check error: {e}", flush=True)


def check_pending_followups(config, state):
    if "pending_followups" not in state:
        state["pending_followups"] = []
        return

    now = datetime.now(timezone.utc)
    remaining = []

    template_map = {
        "followup_1h": config.get("followup_1h_text", ""),
        "followup_day2": config.get("followup_day2_text", ""),
        "followup_day3": config.get("followup_day3_text", ""),
        "followup_24h": config.get("followup_1h_text", config.get("followup_24h_text", "")),
    }

    for fu in state["pending_followups"]:
        send_at = datetime.fromisoformat(fu["send_at"])
        if now >= send_at:
            lead = fu["lead"]
            fu_type = fu.get("type", "followup_24h")
            template = template_map.get(fu_type, "")
            if not template:
                continue
            followup_msg = format_message(template, lead)
            status_code, resp = send_sms(config, lead["phone"], followup_msg, source=f"lead_monitor:{fu_type}")
            print(f"  {fu_type} sent to {lead['name']}: HTTP {status_code}", flush=True)
            log_lead(lead, [{"type": fu_type, "to": lead["phone"], "status": status_code, "response": resp}])
        else:
            remaining.append(fu)

    state["pending_followups"] = remaining


def run_once(config=None):
    if config is None:
        config = load_config()
    state = load_state()

    # First-run guard: if processed_lead_ids is empty, this is initial
    # startup against an existing inbox. Record every lead ID we find as
    # already-processed instead of texting all of them.
    is_first_run = not state.get("processed_lead_ids")

    check_pending_followups(config, state)
    check_inbound_replies(config, state)

    new_leads = check_for_new_leads(config, state)

    if is_first_run and new_leads:
        for lead in new_leads:
            state["processed_lead_ids"].append(lead["lead_id"])
        print(
            f"[{datetime.now(timezone.utc).isoformat()}] First run: seeded "
            f"{len(new_leads)} existing lead IDs as already-processed. "
            f"No texts sent.",
            flush=True,
        )
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        return 0

    if not new_leads:
        print(f"[{datetime.now(timezone.utc).isoformat()}] No new leads found.", flush=True)
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        return 0

    print(f"[{datetime.now(timezone.utc).isoformat()}] Found {len(new_leads)} new lead(s)!", flush=True)

    for lead in new_leads:
        time.sleep(config["delays"]["welcome_text_seconds"])
        process_lead(config, lead)
        state["processed_lead_ids"].append(lead["lead_id"])

    state["last_check"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return len(new_leads)


def run_daemon(interval=60):
    config = load_config()
    print(f"Lead Monitor started. Checking every {interval}s...", flush=True)
    print(f"Gmail: {config['gmail']['email']}", flush=True)
    print(f"SimpleTexting #: {config['simpletexting']['account_phone']}", flush=True)
    print(f"Nudge to: {config['justin']['personal_cell']}", flush=True)

    while True:
        try:
            run_once(config)
        except Exception as e:
            print(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: {e}", flush=True)
        sys.stdout.flush()
        time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        run_daemon()
