"""Daily digest: HTML email to Justin each morning.

Sections (top → bottom): summary, closings in next 14 days, inbound
replies since last digest, Hot overdue, Warm overdue, Cold collapsed
to a count. Sorted by days-overdue desc, loan-amount tiebreak.

Sent as multipart/alternative — HTML preferred, plain-text fallback
preserved for accessibility and the rare client that can't render HTML.
"""

import smtplib
from datetime import datetime
from email.message import EmailMessage

from outreach import config, notion_client, scan

COMMISSION_RATE = 0.0125  # 125 bps
CLOSING_WINDOW_DAYS = 14


def _esc(s):
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _commission(loan):
    return (loan or 0) * COMMISSION_RATE


def _split_and_rank(overdue, today):
    """Split overdue by priority; sort each: days-overdue desc, loan desc tiebreak."""
    def key(r):
        days_overdue = (today - r["fu_date"]).days
        return (-days_overdue, -(r.get("loan") or 0))
    hot = sorted([r for r in overdue if r.get("priority") == "Hot"], key=key)
    warm = sorted([r for r in overdue if r.get("priority") == "Warm"], key=key)
    cold = sorted([r for r in overdue if r.get("priority") == "Cold"], key=key)
    return hot, warm, cold


def _summary_stats(overdue, today):
    if not overdue:
        return {"at_risk": 0, "total": 0, "hot": 0, "warm": 0, "cold": 0,
                "oldest_days": 0, "oldest_name": ""}
    counts = {"Hot": 0, "Warm": 0, "Cold": 0}
    at_risk = 0.0
    oldest = None
    for r in overdue:
        p = r.get("priority") or ""
        if p in counts:
            counts[p] += 1
        at_risk += _commission(r.get("loan"))
        if oldest is None or r["fu_date"] < oldest["fu_date"]:
            oldest = r
    return {
        "at_risk": at_risk,
        "total": len(overdue),
        "hot": counts["Hot"], "warm": counts["Warm"], "cold": counts["Cold"],
        "oldest_days": (today - oldest["fu_date"]).days,
        "oldest_name": oldest["name"],
    }


_CSS = """
body { margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont,
       'Segoe UI', Roboto, Arial, sans-serif; color: #111827; background: #f9fafb; }
.container { max-width: 680px; margin: 0 auto; background: white;
             border-radius: 12px; overflow: hidden;
             box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.header { background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
          color: white; padding: 24px 28px; }
.header h1 { margin: 0; font-size: 18px; font-weight: 600; letter-spacing: -0.01em; }
.header .date { margin-top: 4px; font-size: 13px; color: #9ca3af; }
.summary { padding: 20px 28px; background: #fafafa;
           border-bottom: 1px solid #e5e7eb; }
.summary table { width: 100%; border-collapse: collapse; }
.summary td { padding: 5px 0; font-size: 14px; vertical-align: top; }
.summary td.label { color: #6b7280; width: 220px; }
.summary td.value { font-weight: 600; color: #111827; }
.summary .money { color: #059669; font-variant-numeric: tabular-nums; }
.section { padding: 20px 28px; border-bottom: 1px solid #e5e7eb; }
.section:last-child { border-bottom: none; }
.section h2 { margin: 0 0 14px 0; font-size: 12px; font-weight: 700;
              letter-spacing: 0.06em; text-transform: uppercase; color: #374151; }
.section h2 .count { color: #9ca3af; font-weight: 500; margin-left: 6px; }
.section h2 .at-risk { color: #059669; font-weight: 500; margin-left: 6px; }
table.leads { width: 100%; border-collapse: collapse; }
table.leads td { padding: 9px 6px; border-bottom: 1px solid #f3f4f6;
                 vertical-align: middle; font-size: 13px; }
table.leads tr:last-child td { border-bottom: none; }
td.days { color: #6b7280; width: 56px; font-variant-numeric: tabular-nums; font-size: 12px; }
td.days.urgent { color: #dc2626; font-weight: 600; }
td.name { font-weight: 500; color: #111827; }
td.status { color: #6b7280; font-size: 12px; width: 110px; }
td.money { text-align: right; font-variant-numeric: tabular-nums;
           color: #059669; font-weight: 500; width: 80px; }
td.closing-date { color: #dc2626; font-weight: 600; width: 70px;
                  font-variant-numeric: tabular-nums; font-size: 12px; }
.pill { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px;
        font-weight: 600; }
.pill.warm { background: #fed7aa; color: #c2410c; }
.empty { color: #9ca3af; font-style: italic; font-size: 13px; margin: 0; }
.reply { padding: 10px 0; border-bottom: 1px solid #f3f4f6; }
.reply:last-child { border-bottom: none; }
.reply .head { color: #9ca3af; font-size: 12px; }
.reply .name { font-weight: 600; color: #111827; font-size: 14px; }
.reply .body { color: #374151; font-size: 13px; margin-top: 4px; }
.cold-summary { color: #6b7280; font-size: 13px; margin: 0; }
.cold-summary strong { color: #111827; }
.footer { padding: 14px 28px; font-size: 11px; color: #9ca3af;
          background: #fafafa; }
"""


def _html_summary(s):
    return f"""
  <div class="summary">
    <table>
      <tr><td class="label">At-risk commission (overdue)</td>
          <td class="value"><span class="money">${s['at_risk']:,.0f}</span></td></tr>
      <tr><td class="label">Overdue follow-ups</td>
          <td class="value">{s['total']} <span style="color:#6b7280; font-weight:400;">({s['hot']} 🔥 · {s['warm']} 🌡 · {s['cold']} ❄️)</span></td></tr>
      <tr><td class="label">Oldest overdue</td>
          <td class="value">{s['oldest_days']}d <span style="color:#6b7280; font-weight:400;">({_esc(s['oldest_name'])})</span></td></tr>
    </table>
  </div>"""


def _html_closings(closings, today):
    if not closings:
        body = f'<p class="empty">No closings in the next {CLOSING_WINDOW_DAYS} days.</p>'
    else:
        rows = "".join(
            f'<tr><td class="closing-date">{c["closing_date"].strftime("%m/%d")}</td>'
            f'<td class="name">{_esc(c["name"])}</td>'
            f'<td class="status">{_esc(c.get("status") or "")}</td>'
            f'<td class="money">${_commission(c["loan"]):,.0f}</td></tr>'
            for c in closings
        )
        body = f'<table class="leads"><tbody>{rows}</tbody></table>'
    return f"""
  <div class="section">
    <h2>🚨 Closings (next {CLOSING_WINDOW_DAYS} days)<span class="count">({len(closings)})</span></h2>
    {body}
  </div>"""


def _html_replies(replies):
    if not replies:
        body = '<p class="empty">No new replies since the last digest.</p>'
    else:
        rows = []
        for r in replies:
            who = _esc(r.get("name") or f"(no Notion match — {r.get('phone') or r.get('from')})")
            bump = ' <span class="pill warm">→ Warm</span>' if r.get("priority_bumped") else ''
            preview = _esc((r.get("text") or r.get("body") or "").replace("\n", " ")[:160])
            rows.append(
                f'<div class="reply">'
                f'<div><span class="name">{who}</span>{bump} '
                f'<span class="head">· {_esc(r["received_at"])}</span></div>'
                f'<div class="body">{preview}</div></div>'
            )
        body = "".join(rows)
    return f"""
  <div class="section">
    <h2>💬 Inbound replies<span class="count">({len(replies)})</span></h2>
    {body}
  </div>"""


def _html_priority(label, emoji, items, today, empty_text):
    total = sum(_commission(i["loan"]) for i in items)
    if not items:
        body = f'<p class="empty">{empty_text}</p>'
    else:
        rows = "".join(
            (lambda d, c: (
                f'<tr><td class="days{(" urgent" if d >= 30 else "")}">{d}d</td>'
                f'<td class="name">{_esc(r["name"])}</td>'
                f'<td class="status">{_esc(r.get("status") or "")}</td>'
                f'<td class="money">${c:,.0f}</td></tr>'
            ))((today - r["fu_date"]).days, _commission(r["loan"]))
            for r in items
        )
        body = f'<table class="leads"><tbody>{rows}</tbody></table>'
    at_risk = f' <span class="at-risk">— ${total:,.0f}</span>' if total else ''
    return f"""
  <div class="section">
    <h2>{emoji} {label}<span class="count">({len(items)})</span>{at_risk}</h2>
    {body}
  </div>"""


def _html_cold(n):
    if n == 0:
        return ""
    return f"""
  <div class="section">
    <h2>❄️ Cold / stale<span class="count">({n})</span></h2>
    <p class="cold-summary"><strong>{n}</strong> cold leads have overdue follow-ups. Not surfaced individually here — open the Pipeline if you want to work them.</p>
  </div>"""


def _compose_html(today, summary, closings, hot, warm, cold_count, replies):
    return "".join([
        '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'<style>{_CSS}</style></head><body><div class="container">',
        f'<div class="header"><h1>juddy outreach digest</h1>',
        f'<div class="date">{today.strftime("%A, %B %d, %Y")}</div></div>',
        _html_summary(summary),
        _html_closings(closings, today),
        _html_replies(replies),
        _html_priority("Hot leads overdue", "🔥", hot, today, "No hot leads overdue. 🎉"),
        _html_priority("Warm leads overdue", "🌡", warm, today, "No warm leads overdue."),
        _html_cold(cold_count),
        f'<div class="footer">Generated by outreach/digest.py · {today.isoformat()}</div>',
        '</div></body></html>',
    ])


def _compose_plain(today, summary, closings, hot, warm, cold_count, replies):
    lines = [
        f"juddy outreach digest — {today.isoformat()}", "",
        "SUMMARY",
        f"  At-risk commission (overdue): ${summary['at_risk']:,.0f}",
        f"  Overdue follow-ups:           {summary['total']} ({summary['hot']} Hot, {summary['warm']} Warm, {summary['cold']} Cold)",
        f"  Oldest overdue:               {summary['oldest_days']}d ({summary['oldest_name']})",
        "",
        f"=== CLOSINGS (next {CLOSING_WINDOW_DAYS} days)  ({len(closings)}) ===",
    ]
    if closings:
        for c in closings:
            lines.append(
                f"  {c['closing_date'].strftime('%m/%d')}  "
                f"{c['name'][:28]:<28} ${_commission(c['loan']):>7,.0f}   "
                f"{c.get('status') or ''}"
            )
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append(f"=== INBOUND REPLIES  ({len(replies)}) ===")
    if replies:
        for r in replies:
            who = r.get("name") or f"(no match — {r.get('phone') or r.get('from')})"
            bump = " [-> Warm]" if r.get("priority_bumped") else ""
            preview = (r.get("text") or r.get("body") or "").replace("\n", " ")[:140]
            lines.append(f"  {r['received_at']}  {who}{bump}")
            lines.append(f"    {preview}")
    else:
        lines.append("  (none)")
    lines.append("")

    def section(label, items):
        total = sum(_commission(i["loan"]) for i in items)
        lines.append(f"=== {label}  ({len(items)})  ${total:,.0f} ===")
        if items:
            for r in items:
                days = (today - r["fu_date"]).days
                lines.append(
                    f"  {days:>3}d  {r['name'][:28]:<28} "
                    f"${_commission(r['loan']):>7,.0f}   {r.get('status') or ''}"
                )
        else:
            lines.append("  (none)")
        lines.append("")

    section("HOT LEADS OVERDUE", hot)
    section("WARM LEADS OVERDUE", warm)

    lines.append(f"=== COLD / STALE  ({cold_count}) ===")
    lines.append(f"  {cold_count} cold leads overdue — open the Pipeline if you want to work them.")

    return "\n".join(lines)


def _send_email(cfg, subject, html_body, plain_body):
    user = cfg["gmail"]["email"]
    pw = cfg["gmail"]["app_password"]
    recipients = cfg["digest"]["to_emails"]
    if not (user and pw and recipients):
        raise RuntimeError(
            "Digest email requires GMAIL_EMAIL, GMAIL_APP_PASSWORD, DIGEST_TO_EMAIL"
        )
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype="html")
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
    closings = list(notion_client.fetch_upcoming_closings(
        cfg["notion"]["token"], cfg["notion"]["database_id"], today, CLOSING_WINDOW_DAYS,
    ))
    hot, warm, cold = _split_and_rank(overdue, today)
    summary = _summary_stats(overdue, today)
    replies = state.get("digest_queue", [])

    html = _compose_html(today, summary, closings, hot, warm, len(cold), replies)
    plain = _compose_plain(today, summary, closings, hot, warm, len(cold), replies)

    _send_email(cfg, f"Outreach digest · {today.isoformat()}", html, plain)

    reply_count = len(replies)
    state["digest_queue"] = []
    scan.save_state(state)

    print(
        f"digest: sent — replies={reply_count} closings={len(closings)} "
        f"hot={len(hot)} warm={len(warm)} cold={len(cold)}"
    )
