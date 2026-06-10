"""Scan Gmail for new lead replies, log to Notion, auto-bump priority,
and SMS-nudge Justin so he can take over the conversation.

Runs every 10 minutes via launchd. State persists in inbound_ledger.json
so we never re-process the same email twice. First run captures the
current max UID as a baseline and exits without processing — no
back-fill of historical email.
"""

import email
import email.utils
import imaplib
import json
from datetime import datetime, timezone
from pathlib import Path

from outreach import config, notion_client, realtor_com, sms

SCRIPT_DIR = Path(__file__).resolve().parent
LEDGER_PATH = SCRIPT_DIR / "inbound_ledger.json"

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# Excerpt of incoming body we attach to the Notion Note. Full body lives
# in the digest email anyway.
BODY_EXCERPT_CHARS = 500


def load_state():
    if LEDGER_PATH.exists():
        with open(LEDGER_PATH) as f:
            return json.load(f)
    return {"last_uid": None, "digest_queue": []}


def save_state(state):
    tmp = LEDGER_PATH.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    tmp.replace(LEDGER_PATH)


def _imap_connect(cfg):
    m = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    m.login(cfg["gmail"]["email"], cfg["gmail"]["app_password"])
    m.select("INBOX", readonly=True)
    return m


def _extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload is not None:
                    return payload.decode("utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode("utf-8", errors="replace") if payload else ""


def _fetch_new(mail, last_uid):
    """Return [(uid, from_addr, subject, body)] for UIDs > last_uid.

    When last_uid is None, returns a single sentinel with the current max
    UID so the caller can baseline without processing the backlog.
    """
    typ, data = mail.uid("search", None, "ALL")
    if typ != "OK" or not data or not data[0]:
        return []
    all_uids = data[0].split()
    if not all_uids:
        return []
    if last_uid is None:
        return [(all_uids[-1].decode(), None, None, None)]

    last_int = int(last_uid)
    new_uids = [u for u in all_uids if int(u) > last_int]

    out = []
    for uid_bytes in new_uids:
        typ, msg_data = mail.uid("fetch", uid_bytes, "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        from_addr = email.utils.parseaddr(msg.get("From", ""))[1].lower()
        subject = msg.get("Subject", "") or ""
        body = _extract_body(msg)
        out.append((uid_bytes.decode(), from_addr, subject, body))
    return out


def _send_welcome(cfg, lead_phone, lead_name, lead_id):
    """Send the initial outreach SMS to a freshly-arrived Realtor.com lead.

    Suppressed until WELCOME_MESSAGE_TEMPLATE is set in .env — leads are
    still created in Notion, but no SMS fires. Dedupe namespace is the
    Realtor.com Lead ID so the same lead can never be welcomed twice.
    """
    template = cfg.get("welcome_message_template") or ""
    if not template:
        return 0, "skipped:WELCOME_MESSAGE_TEMPLATE not set"
    body = template.format(name=realtor_com.first_name(lead_name))
    return sms.send_sms_once(
        cfg, lead_phone, body,
        source="lead_welcome",
        dedupe_namespace=f"welcome:{lead_id}",
    )


def _process_realtor_lead(cfg, body, state, today_iso):
    """Parse a Realtor.com email, create the Notion record (if not already
    in the pipeline), and fire the welcome SMS (if template configured).
    """
    lead = realtor_com.parse(body)
    if not lead:
        state["digest_queue"].append({
            "received_at": today_iso,
            "kind": "realtor_lead_malformed",
            "matched": False,
        })
        return "malformed"

    existing = notion_client.find_by_phone(
        cfg["notion"]["token"], cfg["notion"]["database_id"],
        sms.normalize_phone(lead["phone"]),
    )
    if existing:
        notion_client.append_note(
            cfg["notion"]["token"], existing["id"],
            f"[{today_iso}] Realtor.com re-received this lead (existing record). "
            f"Lead ID {lead['lead_id']}. No welcome fired.",
        )
        state["digest_queue"].append({
            "received_at": today_iso,
            "kind": "realtor_lead_duplicate",
            "name": existing["name"],
            "lead_id": lead["lead_id"],
            "matched": True,
        })
        return "duplicate"

    page_id = notion_client.create_lead(
        cfg["notion"]["token"], cfg["notion"]["database_id"],
        lead, realtor_com.build_notes_summary(lead),
    )

    status, resp = _send_welcome(cfg, lead["phone"], lead["name"], lead["lead_id"])
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if 200 <= status < 300:
        outcome = "welcomed"
        notion_client.append_note(
            cfg["notion"]["token"], page_id,
            f"[{stamp}] AUTO welcome SMS sent.",
        )
    else:
        outcome = "no_welcome"
        notion_client.append_note(
            cfg["notion"]["token"], page_id,
            f"[{stamp}] AUTO welcome SMS NOT sent ({resp[:200]}).",
        )

    state["digest_queue"].append({
        "received_at": today_iso,
        "kind": "realtor_lead_new",
        "name": lead["name"],
        "phone": lead["phone"],
        "lead_id": lead["lead_id"],
        "welcomed": outcome == "welcomed",
        "matched": True,
    })
    return outcome


def _send_nudge(cfg, lead_name, lead_phone):
    """SMS Justin's personal cell so he can take over the conversation.

    Dedupe namespace is per-day-per-lead so repeated scans (or multiple
    emails from the same lead in a day) don't fire multiple nudges.
    """
    target = (cfg.get("justin") or {}).get("personal_cell")
    if not target:
        return
    template = cfg.get("nudge_message_template") or "{name} replied — your turn."
    body = template.format(
        name=lead_name or "(unknown)",
        phone=lead_phone or "(no phone)",
    )
    today_iso = datetime.now().date().isoformat()
    sms.send_sms_once(
        cfg, target, body,
        source="reply_nudge",
        dedupe_namespace=f"nudge:{today_iso}:{lead_phone or 'unknown'}",
    )


def _process_reply(cfg, from_addr, subject, body, state, today_iso):
    record = notion_client.find_by_email(
        cfg["notion"]["token"], cfg["notion"]["database_id"], from_addr,
    )

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    excerpt = (body or "").strip().replace("\r", "")[:BODY_EXCERPT_CHARS]
    note_line = f"[{timestamp} via Gmail] RCVD: {subject} — {excerpt}"

    if record is None:
        state["digest_queue"].append({
            "received_at": timestamp,
            "from": from_addr,
            "name": None,
            "subject": subject,
            "body": excerpt,
            "matched": False,
        })
        return "unknown"

    notion_client.append_note(cfg["notion"]["token"], record["id"], note_line)

    updates = {"Last Contact": today_iso}
    bumped = False
    if record.get("priority") == "Cold":
        updates["Priority"] = "Warm"
        bumped = True
    notion_client.update_simple_properties(
        cfg["notion"]["token"], record["id"], updates,
    )

    _send_nudge(cfg, record["name"], record.get("phone"))

    state["digest_queue"].append({
        "received_at": timestamp,
        "from": from_addr,
        "name": record["name"],
        "subject": subject,
        "body": excerpt,
        "matched": True,
        "priority_bumped": bumped,
    })
    return "logged"


def run(today=None):
    cfg = config.load_config()
    today = (today or datetime.now().date()).isoformat()
    state = load_state()

    if not cfg["gmail"]["email"] or not cfg["gmail"]["app_password"]:
        raise RuntimeError(
            "Gmail scan requires GMAIL_EMAIL and GMAIL_APP_PASSWORD in .env"
        )

    mail = _imap_connect(cfg)
    try:
        results = _fetch_new(mail, state["last_uid"])
    finally:
        try:
            mail.logout()
        except Exception:
            pass

    if not results:
        print("scan: no new mail")
        return

    if state["last_uid"] is None:
        state["last_uid"] = results[0][0]
        save_state(state)
        print(f"scan: baseline set to UID {state['last_uid']} — no replies processed on first run")
        return

    state["last_uid"] = str(max(int(r[0]) for r in results))

    counts = {"reply": 0, "unknown_reply": 0, "welcomed": 0,
              "no_welcome": 0, "duplicate_lead": 0, "malformed_lead": 0}
    for uid, from_addr, subject, body in results:
        if realtor_com.is_realtor_lead_email(from_addr, subject):
            outcome = _process_realtor_lead(cfg, body, state, today)
            if outcome == "welcomed":
                counts["welcomed"] += 1
            elif outcome == "no_welcome":
                counts["no_welcome"] += 1
            elif outcome == "duplicate":
                counts["duplicate_lead"] += 1
            else:
                counts["malformed_lead"] += 1
        else:
            outcome = _process_reply(cfg, from_addr, subject, body, state, today)
            if outcome == "logged":
                counts["reply"] += 1
            else:
                counts["unknown_reply"] += 1

    save_state(state)
    print(
        f"scan: reply={counts['reply']} unknown_reply={counts['unknown_reply']} "
        f"welcomed={counts['welcomed']} no_welcome={counts['no_welcome']} "
        f"dup_lead={counts['duplicate_lead']} malformed={counts['malformed_lead']}"
    )
