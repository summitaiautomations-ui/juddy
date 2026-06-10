"""Daily digest: emails Justin one summary per day of new replies and
overdue follow-ups. Runs once a day via launchd.

Reads the inbound_ledger.json digest queue populated by scan.py, pulls
overdue follow-ups from Notion, composes a plain-text email, sends via
Gmail SMTP, and clears the queue only after a successful send.
"""

import smtplib
from datetime import datetime
from email.message import EmailMessage

from outreach import config, notion_client, scan


def _compose(state, today, overdue):
    lines = [f"juddy outreach digest — {today.isoformat()}", ""]

    replies = state.get("digest_queue", [])
    lines.append(f"INBOUND REPLIES (since last digest): {len(replies)}")
    if replies:
        for r in replies:
            who = r["name"] or f"(no Notion match — {r['phone']})"
            bump = " [→ Warm]" if r.get("priority_bumped") else ""
            preview = r["text"].replace("\n", " ")[:140]
            lines.append(f"  • {r['received_at']}  {who}{bump}")
            lines.append(f"    {preview}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append(f"OVERDUE FOLLOW-UPS: {len(overdue)}")
    if overdue:
        for o in overdue:
            days = (today - o["fu_date"]).days
            lines.append(
                f"  • {o['name']} — {o['priority']} — {o['status']} — {days}d overdue"
            )
    else:
        lines.append("  (none)")

    return "\n".join(lines)


def _send_email(cfg, subject, body):
    user = cfg["gmail"]["email"]
    pw = cfg["gmail"]["app_password"]
    to = cfg["digest"]["to_email"]
    if not (user and pw and to):
        raise RuntimeError(
            "Digest email requires GMAIL_EMAIL, GMAIL_APP_PASSWORD, DIGEST_TO_EMAIL"
        )

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(msg)


def run(today=None):
    cfg = config.load_config()
    today = today or datetime.now().date()
    state = scan.load_state()

    overdue = list(notion_client.fetch_overdue_followups(
        cfg["notion"]["token"], cfg["notion"]["database_id"], today,
    ))

    body = _compose(state, today, overdue)
    _send_email(cfg, f"Outreach digest {today.isoformat()}", body)

    reply_count = len(state.get("digest_queue", []))
    state["digest_queue"] = []
    scan.save_state(state)
    print(f"digest: sent — replies={reply_count} overdue={len(overdue)}")
