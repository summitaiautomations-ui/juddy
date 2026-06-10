"""Day-1 info touch: a 'here's more about me + Summit Mortgage + linktree'
SMS, sent a couple of hours after the welcome, during business hours.

Runs hourly via launchd. For each lead added today whose Notes contain
the welcome marker but not yet the info-touch marker, and where at least
MIN_GAP_HOURS has elapsed since the welcome timestamp, send the
info-touch SMS and append the marker.

Per Justin's explicit ask: send regardless of whether the lead has
already replied. The "engagement = stop nurture" rule applies to
later flows, not this Day-1 touch.

Suppressed until INFO_TOUCH_MESSAGE_TEMPLATE is set in .env. Outside
business hours, exits cleanly without sending.
"""

import re
from datetime import datetime, timedelta

from outreach import config, notion_client, sms

MIN_GAP_HOURS = 2

# Matches both `[YYYY-MM-DD HH:MM]` and `[YYYY-MM-DD]` variants of the
# welcome marker so we degrade gracefully on records that predate the
# datetime-stamped note.
_WELCOME_PATTERN = re.compile(
    r"\[(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}):(\d{2}))?\][^\n]*AUTO welcome SMS sent"
)


def _parse_welcome_time(notes):
    m = _WELCOME_PATTERN.search(notes or "")
    if not m:
        return None
    date_str, hh, mm = m.group(1), m.group(2), m.group(3)
    if hh and mm:
        return datetime.strptime(f"{date_str} {hh}:{mm}", "%Y-%m-%d %H:%M")
    return datetime.strptime(date_str, "%Y-%m-%d")


def _first_name(full_name):
    parts = (full_name or "there").strip().split()
    return parts[0] if parts else "there"


def run(now=None):
    cfg = config.load_config()
    now = now or datetime.now()

    bh_start = int(cfg.get("business_hours_start") or 9)
    bh_end = int(cfg.get("business_hours_end") or 17)
    if not (bh_start <= now.hour < bh_end):
        print(f"day1_info: outside business hours ({bh_start}-{bh_end}); skipping")
        return

    template = cfg.get("info_touch_message_template") or ""
    if not template:
        print("day1_info: INFO_TOUCH_MESSAGE_TEMPLATE not set; skipping")
        return

    today = now.date()
    sent = too_soon = failed = no_phone = 0

    for lead in notion_client.find_leads_for_info_touch(
        cfg["notion"]["token"], cfg["notion"]["database_id"], today,
    ):
        welcome_at = _parse_welcome_time(lead.get("notes", ""))
        if welcome_at and (now - welcome_at) < timedelta(hours=MIN_GAP_HOURS):
            too_soon += 1
            continue
        if not lead.get("phone"):
            no_phone += 1
            continue

        body = template.format(name=_first_name(lead["name"]))
        status, resp = sms.send_sms_once(
            cfg, lead["phone"], body,
            source="day1_info_touch",
            dedupe_namespace=f"info_touch:{lead['id']}",
        )

        stamp = now.strftime("%Y-%m-%d %H:%M")
        if 200 <= status < 300:
            sent += 1
            notion_client.append_note(
                cfg["notion"]["token"], lead["id"],
                f"[{stamp}] AUTO info touch SMS sent.",
            )
        elif status == 0:
            # ledger dedupe skip — still mark so the filter excludes them next run
            notion_client.append_note(
                cfg["notion"]["token"], lead["id"],
                f"[{stamp}] AUTO info touch SMS skipped (ledger dedupe).",
            )
        else:
            failed += 1
            print(f"failed: {lead['name']} HTTP {status}: {resp[:200]}")

    print(
        f"day1_info {now.strftime('%Y-%m-%d %H:%M')}: "
        f"sent={sent} too_soon={too_soon} no_phone={no_phone} failed={failed}"
    )
