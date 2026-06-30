"""Daily recruiting digest — a snazzy HTML email tracking progress to the goal.

One email each morning to Justin: how close the pipeline is to the hiring
goal (default 12), who's on the doorstep (Offer / Interview), which
late-stage follow-ups have gone overdue, the funnel at a glance, and a
roll call of everyone already hired.

Sent multipart/alternative — HTML preferred, plain-text fallback for
accessibility and clients that can't render HTML.
"""

import smtplib
from datetime import date, datetime
from email.message import EmailMessage

from recruiting import config, notion

# Active funnel, narrowest goal last. "Passed" and un-staged rows are
# excluded from the funnel and reported separately.
FUNNEL = ["Initial Outreach", "Conversation", "Interview", "Offer", "Hired"]
LATE_STAGES = ["Offer", "Interview"]

# Palette
INK = "#0f172a"
MUTED = "#64748b"
LINE = "#e2e8f0"
GREEN = "#16a34a"
GREEN_SOFT = "#dcfce7"
AMBER = "#d97706"
RED = "#dc2626"
INDIGO = "#4f46e5"
VIOLET = "#7c3aed"


def _esc(s):
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _money(v):
    if not v:
        return ""
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


def _location(c):
    bits = [b for b in (c.get("city"), c.get("state")) if b]
    return ", ".join(bits)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def analyze(candidates, today, goal, grace_days):
    by_stage = {}
    for c in candidates:
        by_stage[c["stage"]] = by_stage.get(c["stage"], 0) + 1

    hired = [c for c in candidates if c["stage"] == "Hired"]
    offers = [c for c in candidates if c["stage"] == "Offer"]
    interviews = [c for c in candidates if c["stage"] == "Interview"]
    passed = by_stage.get("Passed", 0)

    active = [c for c in candidates
              if c["stage"] in FUNNEL and c["stage"] != "Hired"]

    def overdue_days(c):
        fu = c.get("next_followup")
        if not fu:
            return None
        d = (today - fu).days
        return d if d > grace_days else None

    # On the doorstep: Offer first, then Interview; most-overdue surfaces first.
    doorstep = []
    for c in offers + interviews:
        od = overdue_days(c)
        doorstep.append({**c, "overdue": od})
    doorstep.sort(key=lambda c: (
        0 if c["stage"] == "Offer" else 1,
        -(c["overdue"] or -10_000),
    ))

    overdue_late = [c for c in doorstep if c["overdue"] is not None]

    # Momentum
    new_7 = sum(1 for c in candidates
                if c.get("date_added") and (today - c["date_added"]).days <= 7)
    touched_today = sum(1 for c in candidates
                        if c.get("last_contact") == today)

    hired_count = len(hired)
    remaining = max(goal - hired_count, 0)
    pct = min(int(round(hired_count / goal * 100)), 100) if goal else 0

    return {
        "by_stage": by_stage,
        "hired": hired,
        "hired_count": hired_count,
        "offers": offers,
        "interviews": interviews,
        "passed": passed,
        "active_total": len(active),
        "doorstep": doorstep,
        "overdue_late": overdue_late,
        "new_7": new_7,
        "touched_today": touched_today,
        "goal": goal,
        "remaining": remaining,
        "pct": pct,
    }


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def _bar(pct, fill, track="#eef2f7", height=14, radius=7):
    """A rounded progress bar as a nested table (email-safe, no CSS bars)."""
    filled = max(0, min(100, pct))
    empty = 100 - filled
    # Two-cell table; widths as percentages render reliably across clients.
    cells = (
        f'<td width="{filled}%" bgcolor="{fill}" '
        f'style="height:{height}px;line-height:{height}px;font-size:0;'
        f'border-radius:{radius}px 0 0 {radius}px;">&nbsp;</td>'
    ) if filled > 0 else ""
    if empty > 0:
        rad = f"{radius}px" if filled == 0 else "0"
        cells += (
            f'<td width="{empty}%" bgcolor="{track}" '
            f'style="height:{height}px;line-height:{height}px;font-size:0;'
            f'border-radius:0 {rad} {rad} 0;">&nbsp;</td>'
        )
    return (
        f'<table role="presentation" width="100%" cellpadding="0" '
        f'cellspacing="0" style="border-collapse:separate;table-layout:fixed;">'
        f'<tr>{cells}</tr></table>'
    )


def _stat(value, label, accent=INK):
    return (
        f'<td align="center" valign="top" style="padding:6px 4px;">'
        f'<div style="font:700 24px/1.1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        f'color:{accent};">{value}</div>'
        f'<div style="font:600 11px/1.3 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        f'color:{MUTED};text-transform:uppercase;letter-spacing:.04em;margin-top:4px;">{label}</div>'
        f'</td>'
    )


def _pill(text, bg, fg):
    return (
        f'<span style="display:inline-block;background:{bg};color:{fg};'
        f'font:700 11px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        f'padding:4px 8px;border-radius:999px;white-space:nowrap;">{text}</span>'
    )


def _doorstep_rows(doorstep):
    if not doorstep:
        return (f'<tr><td style="padding:14px 20px;font:400 14px/1.5 '
                f'-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{MUTED};">'
                f'No candidates in Offer or Interview right now.</td></tr>')
    rows = []
    for c in doorstep:
        stage = c["stage"]
        stage_bg, stage_fg = ((GREEN_SOFT, "#166534") if stage == "Offer"
                              else ("#fef9c3", "#854d0e"))
        meta_bits = [b for b in (
            c.get("role"), _location(c),
            (f'{c["units_2025"]:.0f}u' if c.get("units_2025") else None),
            _money(c.get("volume_2025")),
            (f'rec: {c["recruiter"]}' if c.get("recruiter") else None),
        ) if b]
        meta = "  ·  ".join(_esc(b) for b in meta_bits)
        if c["overdue"] is not None:
            pill = _pill(f'⏰ follow-up {c["overdue"]}d overdue', "#fee2e2", RED)
            flag = f'<div style="margin-top:4px;">{pill}</div>'
        else:
            flag = ""
        rows.append(
            f'<tr>'
            f'<td style="padding:12px 20px;border-top:1px solid {LINE};">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'<td valign="top">'
            f'<div style="font:700 15px/1.3 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{INK};">'
            f'{_esc(c["name"])}</div>'
            f'<div style="font:400 12px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{MUTED};margin-top:2px;">'
            f'{meta}</div>{flag}'
            f'</td>'
            f'<td valign="top" align="right" style="white-space:nowrap;padding-left:10px;">'
            f'{_pill(stage, stage_bg, stage_fg)}</td>'
            f'</tr></table>'
            f'</td></tr>'
        )
    return "".join(rows)


def _funnel_rows(by_stage):
    counts = [by_stage.get(s, 0) for s in FUNNEL]
    top = max(counts) or 1
    colors = {
        "Initial Outreach": "#94a3b8",
        "Conversation": "#38bdf8",
        "Interview": "#a78bfa",
        "Offer": "#fb923c",
        "Hired": GREEN,
    }
    rows = []
    for stage, n in zip(FUNNEL, counts):
        pct = int(round(n / top * 100))
        rows.append(
            f'<tr>'
            f'<td width="120" style="padding:5px 10px 5px 0;font:600 12px/1.3 '
            f'-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{INK};white-space:nowrap;">'
            f'{stage}</td>'
            f'<td style="padding:5px 0;">{_bar(pct, colors[stage], height=12, radius=6)}</td>'
            f'<td width="34" align="right" style="padding:5px 0 5px 10px;font:700 13px/1.3 '
            f'-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{INK};">{n}</td>'
            f'</tr>'
        )
    return "".join(rows)


def _hired_chips(hired):
    if not hired:
        return ""
    chips = "".join(
        f'<span style="display:inline-block;background:{GREEN_SOFT};color:#166534;'
        f'font:600 12px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        f'padding:6px 10px;border-radius:999px;margin:0 6px 6px 0;">✓ {_esc(c["name"])}</span>'
        for c in hired
    )
    return chips


def compose_html(today, a):
    goal, hired_count, remaining, pct = a["goal"], a["hired_count"], a["remaining"], a["pct"]
    pretty_date = today.strftime("%A, %B %-d, %Y")

    if remaining == 0:
        headline = f"🎉 Goal hit — {hired_count} hired!"
        sub = "You crossed the finish line. Time to set the next number."
    elif remaining == 1:
        headline = "1 hire to go"
        sub = "One more and the goal is in the books. Who's it going to be?"
    else:
        headline = f"{remaining} hires to go"
        sub = f"{a['active_total']} candidates still in play across the pipeline."

    overdue_n = len(a["overdue_late"])
    alert = ""
    if overdue_n:
        names = ", ".join(_esc(c["name"]) for c in a["overdue_late"][:3])
        more = f" +{overdue_n - 3} more" if overdue_n > 3 else ""
        alert = (
            f'<tr><td style="padding:0 24px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:#fef2f2;border:1px solid #fecaca;border-radius:12px;">'
            f'<tr><td style="padding:12px 16px;font:600 13px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{RED};">'
            f'⏰ {overdue_n} late-stage follow-up{"s" if overdue_n != 1 else ""} overdue — '
            f'<span style="font-weight:400;color:#7f1d1d;">{names}{more}</span></td></tr>'
            f'</table></td></tr><tr><td style="height:8px;font-size:0;">&nbsp;</td></tr>'
        )

    return f"""\
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only">
<title>Recruiting Pipeline</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">\
{hired_count}/{goal} hired · {remaining} to go · {a['active_total']} active in pipeline</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;background:#ffffff;border-radius:18px;overflow:hidden;box-shadow:0 1px 3px rgba(15,23,42,.08);">

  <!-- Header -->
  <tr><td bgcolor="{INDIGO}" style="background:{INDIGO};background-image:linear-gradient(135deg,{INDIGO},{VIOLET});padding:26px 24px;">
    <div style="font:700 12px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#c7d2fe;text-transform:uppercase;letter-spacing:.12em;">Summit Mortgage · Recruiting</div>
    <div style="font:800 22px/1.2 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#ffffff;margin-top:6px;">Pipeline Progress</div>
    <div style="font:400 13px/1.4 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#e0e7ff;margin-top:3px;">{pretty_date}</div>
  </td></tr>

  <!-- Hero: goal progress -->
  <tr><td style="padding:24px 24px 8px 24px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
      <td valign="bottom">
        <span style="font:800 44px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{INK};">{hired_count}</span>
        <span style="font:700 20px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{MUTED};"> / {goal} hired</span>
      </td>
      <td valign="bottom" align="right">
        <span style="font:800 16px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{GREEN};">{pct}%</span>
      </td>
    </tr></table>
    <div style="margin:12px 0 6px 0;">{_bar(pct, GREEN, height=16, radius=8)}</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="font:700 15px/1.3 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{INK};">{headline}</td>
    </tr><tr>
      <td style="font:400 13px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{MUTED};padding-top:2px;">{sub}</td>
    </tr></table>
  </td></tr>

  <!-- Stat strip -->
  <tr><td style="padding:14px 16px 18px 16px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
      style="background:#f8fafc;border:1px solid {LINE};border-radius:14px;"><tr>
      {_stat(a['active_total'], 'Active', INK)}
      {_stat(len(a['offers']), 'In Offer', AMBER)}
      {_stat(len(a['interviews']), 'Interview', VIOLET)}
      {_stat(a['new_7'], 'New / 7d', INDIGO)}
    </tr></table>
  </td></tr>

  {alert}

  <!-- On the doorstep -->
  <tr><td style="padding:6px 0 0 0;">
    <div style="padding:0 24px 8px 24px;font:800 13px/1.2 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{INK};text-transform:uppercase;letter-spacing:.06em;">
      🎯 On the doorstep <span style="color:{MUTED};font-weight:600;text-transform:none;letter-spacing:0;">— next hires likely come from here</span>
    </div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      {_doorstep_rows(a['doorstep'])}
    </table>
  </td></tr>

  <!-- Funnel -->
  <tr><td style="padding:22px 24px 6px 24px;">
    <div style="font:800 13px/1.2 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{INK};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px;">Funnel</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      {_funnel_rows(a['by_stage'])}
    </table>
    <div style="font:400 12px/1.4 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{MUTED};margin-top:8px;">{a['passed']} passed · {a['touched_today']} contacted today</div>
  </td></tr>

  <!-- Hired roll call -->
  <tr><td style="padding:18px 24px 6px 24px;">
    <div style="font:800 13px/1.2 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{INK};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px;">Hired so far</div>
    <div>{_hired_chips(a['hired'])}</div>
  </td></tr>

  <!-- Footer -->
  <tr><td style="padding:20px 24px 26px 24px;">
    <div style="border-top:1px solid {LINE};padding-top:14px;font:400 11px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#94a3b8;">
      Daily recruiting digest · generated from the Notion Recruiting Pipeline.<br>Goal: {goal} hires.
    </div>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""


def compose_plain(today, a):
    L = []
    L.append(f"RECRUITING PIPELINE — {today.strftime('%A, %B %-d, %Y')}")
    L.append("=" * 48)
    L.append(f"{a['hired_count']} / {a['goal']} hired  ({a['pct']}%)  —  "
             f"{a['remaining']} to go")
    L.append(f"{a['active_total']} active · {len(a['offers'])} offer · "
             f"{len(a['interviews'])} interview · {a['new_7']} new this week")
    L.append("")
    if a["overdue_late"]:
        L.append(f"!! {len(a['overdue_late'])} late-stage follow-ups overdue:")
        for c in a["overdue_late"]:
            L.append(f"   - {c['name']} ({c['stage']}, {c['overdue']}d overdue)")
        L.append("")
    L.append("ON THE DOORSTEP (Offer / Interview):")
    for c in a["doorstep"]:
        tag = f"  [{c['overdue']}d overdue]" if c["overdue"] is not None else ""
        L.append(f"   {c['stage']:<10} {c['name']}{tag}")
    L.append("")
    L.append("FUNNEL:")
    for s in FUNNEL:
        L.append(f"   {s:<18} {a['by_stage'].get(s, 0)}")
    L.append(f"   {'Passed':<18} {a['passed']}")
    L.append("")
    L.append("HIRED: " + ", ".join(c["name"] for c in a["hired"]))
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def _send_email(cfg, subject, html_body, plain_body):
    user = cfg["gmail"]["email"]
    pw = cfg["gmail"]["app_password"]
    recipients = cfg["digest"]["to_emails"]
    if not (user and pw and recipients):
        raise RuntimeError(
            "Recruiting digest email requires GMAIL_EMAIL, GMAIL_APP_PASSWORD, "
            "and RECRUITING_DIGEST_TO (or DIGEST_TO_EMAIL)."
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


def build(today=None, dry_run=False):
    """Fetch + analyze + render. Returns (subject, html, plain, analysis)."""
    cfg = config.load_config()
    today = today or datetime.now().date()
    candidates = list(notion.fetch_candidates(
        cfg["notion"]["token"], cfg["notion"]["database_id"]))
    a = analyze(candidates, today, cfg["hiring_goal"], cfg["overdue_grace_days"])
    if a["remaining"] == 0:
        subject = f"🎉 Recruiting: goal hit — {a['hired_count']}/{a['goal']} hired"
    else:
        subject = (f"Recruiting: {a['hired_count']}/{a['goal']} hired · "
                   f"{a['remaining']} to go · {today.isoformat()}")
    html = compose_html(today, a)
    plain = compose_plain(today, a)
    return subject, html, plain, a, cfg


def run(today=None, dry_run=False):
    subject, html, plain, a, cfg = build(today=today)
    if dry_run:
        print(plain)
        print(f"\n[dry-run] would send '{subject}' to "
              f"{', '.join(cfg['digest']['to_emails']) or '(no recipients set)'}")
        return
    _send_email(cfg, subject, html, plain)
    print(f"recruiting digest: sent — {a['hired_count']}/{a['goal']} hired, "
          f"{a['remaining']} to go, {len(a['overdue_late'])} overdue late-stage")
