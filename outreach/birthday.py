"""Birthday flow: text past clients 7 days before their birthday.

Designed to be run daily. Idempotent per year via two layers:
  1. sms.py's namespaced dedupe ledger (namespace = "birthday:YYYY")
  2. A year-stamped Notes line written on every successful send, checked
     before sending so re-installs / ledger resets don't double-fire.
"""

from datetime import datetime, timedelta

from outreach import config, notion_client, sms

LEAD_DAYS = 7
YEAR_NOTE_MARKER = "🎂 Birthday freebie text sent"


def first_name(full_name):
    parts = (full_name or "there").strip().split()
    return parts[0] if parts else "there"


def is_birthday_in_window(dob_str, today, lead_days=LEAD_DAYS):
    try:
        dob = datetime.strptime(dob_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    target = today + timedelta(days=lead_days)
    return dob.month == target.month and dob.day == target.day


def already_noted_this_year(notes, year):
    year_stamp = f"[{year}-"
    for line in (notes or "").splitlines():
        if YEAR_NOTE_MARKER in line and year_stamp in line:
            return True
    return False


def run(today=None):
    cfg = config.load_config()
    today = today or datetime.now().date()
    template = cfg["birthday_message_template"]

    sent = 0
    skipped_already_noted = 0
    skipped_sms_dedupe = 0
    failed = 0

    for client in notion_client.fetch_past_clients_with_birthday(
        cfg["notion"]["token"], cfg["notion"]["database_id"],
    ):
        if not is_birthday_in_window(client["dob"], today):
            continue
        if already_noted_this_year(client["notes"], today.year):
            skipped_already_noted += 1
            continue

        msg = template.format(name=first_name(client["name"]))
        status, resp = sms.send_sms_once(
            cfg, client["phone"], msg,
            source="birthday_campaign",
            dedupe_namespace=f"birthday:{today.year}",
        )

        if status == 0:
            skipped_sms_dedupe += 1
            continue
        if 200 <= status < 300:
            sent += 1
            notion_client.append_note(
                cfg["notion"]["token"], client["id"],
                f"[{today.isoformat()}] {YEAR_NOTE_MARKER} (7 days out from {client['dob']}).",
            )
        else:
            failed += 1
            print(f"failed: {client['name']} ({client['phone']}) HTTP {status}: {resp[:200]}")

    print(
        f"birthday {today}: sent={sent} "
        f"already_noted={skipped_already_noted} "
        f"sms_dedupe={skipped_sms_dedupe} failed={failed}"
    )
