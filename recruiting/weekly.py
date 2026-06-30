"""Weekly recruiting funnel email.

A different lens from the daily digest: no goal or production targets, just
funnel health — Top / Middle / Bottom of funnel — with week-over-week
movement.

Movement (who advanced a stage, hired/passed this week) needs memory, so
each run saves a snapshot of every candidate's stage to
recruiting/.weekly_state.json (gitignored) and diffs against the previous
one. The first run establishes the baseline; comparisons start the week
after.
"""

import json
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from recruiting import config, notion
from recruiting.digest import _bar, _esc, _pill, INK, MUTED, LINE, RED, GREEN

STATE_FILE = Path(__file__).resolve().parent / ".weekly_state.json"

# Stage -> funnel bucket. Hired/Passed are terminal exits, not buckets.
BUCKETS = [
    ("Top of Funnel", ["Initial Outreach"], "#0ea5e9"),
    ("Middle of Funnel", ["Conversation", "Interview"], "#7c3aed"),
    ("Bottom of Funnel", ["Offer"], "#059669"),
]
STAGE_ORDER = {
    "Initial Outreach": 0, "Conversation": 1, "Interview": 2,
    "Offer": 3, "Hired": 4,
}


def _bucket_of(stage):
    for name, stages, _ in BUCKETS:
        if stage in stages:
            return name
    return None  # Hired, Passed, or unstaged


# ---------------------------------------------------------------------------
# Snapshot state
# ---------------------------------------------------------------------------

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (ValueError, OSError):
            return None
    return None


def save_state(candidates, today):
    snap = {
        "snapshot_date": today.isoformat(),
        "candidates": {c["id"]: {"stage": c["stage"], "name": c["name"]}
                       for c in candidates if c.get("id")},
    }
    STATE_FILE.write_text(json.dumps(snap, indent=2))


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(candidates, prev, today):
    # Current bucket + stage counts
    bucket_counts = {name: 0 for name, _, _ in BUCKETS}
    stage_counts = {}
    for c in candidates:
        stage_counts[c["stage"]] = stage_counts.get(c["stage"], 0) + 1
        b = _bucket_of(c["stage"])
        if b:
            bucket_counts[b] += 1

    # New into the pipeline this week (independent of snapshot)
    week_ago = today - timedelta(days=7)
    new_entries = sorted(
        [c for c in candidates
         if c.get("date_added") and c["date_added"] >= week_ago],
        key=lambda c: c["date_added"], reverse=True,
    )

    advanced, regressed, hired_wk, passed_wk = [], [], [], []
    bucket_deltas = {name: None for name, _, _ in BUCKETS}
    have_prev = bool(prev and prev.get("candidates"))

    if have_prev:
        prevc = prev["candidates"]
        # Bucket deltas vs last week
        prev_bucket = {name: 0 for name, _, _ in BUCKETS}
        for rec in prevc.values():
            b = _bucket_of(rec.get("stage"))
            if b:
                prev_bucket[b] += 1
        for name in bucket_deltas:
            bucket_deltas[name] = bucket_counts[name] - prev_bucket[name]

        # Per-candidate movement
        for c in candidates:
            old = prevc.get(c["id"])
            if not old:
                continue
            o, n = old.get("stage"), c["stage"]
            if o == n:
                continue
            move = {"name": c["name"], "from": o, "to": n}
            if n == "Hired":
                hired_wk.append(move)
            elif n == "Passed":
                passed_wk.append(move)
            else:
                oi, ni = STAGE_ORDER.get(o, -99), STAGE_ORDER.get(n, -99)
                (advanced if ni > oi else regressed).append(move)

    return {
        "bucket_counts": bucket_counts,
        "bucket_deltas": bucket_deltas,
        "stage_counts": stage_counts,
        "new_entries": new_entries,
        "advanced": advanced,
        "regressed": regressed,
        "hired_wk": hired_wk,
        "passed_wk": passed_wk,
        "have_prev": have_prev,
        "prev_date": prev.get("snapshot_date") if have_prev else None,
        "active_total": sum(bucket_counts.values()),
    }


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

SKY = "#0ea5e9"
VIOLET = "#7c3aed"
EMERALD = "#059669"
INDIGO = "#4f46e5"


def _delta_badge(d):
    if d is None:
        return ""
    if d > 0:
        return _pill(f"▲ +{d} this week", "#dcfce7", "#166534")
    if d < 0:
        return _pill(f"▼ {d} this week", "#fee2e2", RED)
    return _pill("no change", "#f1f5f9", MUTED)


def _bucket_card(name, stages, color, count, delta, stage_counts, top):
    inner = "  ·  ".join(
        f'{s} {stage_counts.get(s, 0)}' for s in stages
    )
    width = int(round(count / top * 100)) if top else 0
    return (
        f'<tr><td style="padding:8px 0;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:#ffffff;border:1px solid {LINE};border-left:4px solid {color};'
        f'border-radius:12px;"><tr><td style="padding:14px 16px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td valign="middle">'
        f'<div style="font:800 13px/1.2 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        f'color:{color};text-transform:uppercase;letter-spacing:.05em;">{name}</div>'
        f'<div style="font:400 12px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        f'color:{MUTED};margin-top:3px;">{_esc(inner)}</div>'
        f'</td>'
        f'<td valign="middle" align="right" style="white-space:nowrap;padding-left:10px;">'
        f'<div style="font:800 30px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{INK};">{count}</div>'
        f'</td></tr></table>'
        f'<div style="margin:10px 0 8px 0;">{_bar(width, color, height=10, radius=5)}</div>'
        f'<div>{_delta_badge(delta)}</div>'
        f'</td></tr></table>'
        f'</td></tr>'
    )


def _move_list(title, moves, accent, arrow=True, cap=12):
    if not moves:
        return ""
    shown, extra = moves[:cap], max(0, len(moves) - cap)
    rows = []
    for m in shown:
        if arrow and m.get("from") and m.get("to"):
            detail = (f'<span style="color:{MUTED};"> · {_esc(m["from"])} '
                      f'→ {_esc(m["to"])}</span>')
        else:
            detail = ""
        rows.append(
            f'<div style="padding:5px 0;font:400 13px/1.4 -apple-system,Segoe UI,'
            f'Roboto,Helvetica,Arial,sans-serif;color:{INK};border-top:1px solid {LINE};">'
            f'{_esc(m["name"])}{detail}</div>'
        )
    if extra:
        rows.append(
            f'<div style="padding:5px 0;font:600 13px/1.4 -apple-system,Segoe UI,'
            f'Roboto,Helvetica,Arial,sans-serif;color:{MUTED};border-top:1px solid {LINE};">'
            f'+{extra} more</div>'
        )
    return (
        f'<tr><td style="padding:10px 24px 0 24px;">'
        f'<div style="font:800 12px/1.2 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        f'color:{accent};text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;">'
        f'{title} <span style="color:{MUTED};font-weight:700;">({len(moves)})</span></div>'
        f'{"".join(rows)}</td></tr>'
    )


def compose_html(today, a):
    start = today - timedelta(days=6)
    rng = f"{start.strftime('%b %-d')} – {today.strftime('%b %-d, %Y')}"
    top = max(a["bucket_counts"].values()) or 1

    cards = "".join(
        _bucket_card(name, stages, color, a["bucket_counts"][name],
                     a["bucket_deltas"][name], a["stage_counts"], top)
        for name, stages, color in BUCKETS
    )

    if a["have_prev"]:
        movement = (
            _move_list("🎉 Hired this week", a["hired_wk"], GREEN)
            + _move_list("▲ Advanced a stage", a["advanced"], INDIGO)
            + _move_list("✨ New into pipeline", a["new_entries"], SKY, arrow=False)
            + _move_list("✖ Passed this week", a["passed_wk"], RED)
            + _move_list("▼ Slipped back", a["regressed"], "#b45309")
        )
        if not movement:
            movement = (
                f'<tr><td style="padding:12px 24px;font:400 14px/1.5 -apple-system,'
                f'Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{MUTED};">'
                f'No stage changes since last week.</td></tr>'
            )
        baseline = ""
    else:
        movement = _move_list("✨ New into pipeline", a["new_entries"], SKY, arrow=False)
        baseline = (
            f'<tr><td style="padding:0 24px 4px 24px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;">'
            f'<tr><td style="padding:12px 16px;font:600 13px/1.5 -apple-system,Segoe UI,'
            f'Roboto,Helvetica,Arial,sans-serif;color:{INDIGO};">'
            f'📌 Baseline saved — week-over-week movement starts in next week\'s email.'
            f'</td></tr></table></td></tr><tr><td style="height:8px;font-size:0;">&nbsp;</td></tr>'
        )

    return f"""\
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only">
<title>Recruiting Funnel · Weekly</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">\
{a['active_total']} active in funnel · {len(a['new_entries'])} new this week</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;background:#ffffff;border-radius:18px;overflow:hidden;box-shadow:0 1px 3px rgba(15,23,42,.08);">

  <tr><td bgcolor="{INDIGO}" style="background:{INDIGO};background-image:linear-gradient(135deg,{INDIGO},{VIOLET});padding:26px 24px;">
    <div style="font:700 12px/1 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#c7d2fe;text-transform:uppercase;letter-spacing:.12em;">Summit Mortgage · Recruiting</div>
    <div style="font:800 22px/1.2 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#ffffff;margin-top:6px;">Weekly Funnel Review</div>
    <div style="font:400 13px/1.4 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#e0e7ff;margin-top:3px;">{rng}</div>
  </td></tr>

  <tr><td style="padding:18px 24px 4px 24px;">
    <div style="font:400 13px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{MUTED};">
      <b style="color:{INK};">{a['active_total']}</b> active in the funnel · <b style="color:{INK};">{len(a['new_entries'])}</b> new this week</div>
  </td></tr>

  {baseline}

  <tr><td style="padding:6px 24px 4px 24px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{cards}</table>
  </td></tr>

  <tr><td style="height:6px;font-size:0;">&nbsp;</td></tr>
  {movement}

  <tr><td style="padding:22px 24px 26px 24px;">
    <div style="border-top:1px solid {LINE};padding-top:14px;font:400 11px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#94a3b8;">
      Weekly recruiting funnel · generated from the Notion Recruiting Pipeline.
    </div>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""


def compose_plain(today, a):
    start = today - timedelta(days=6)
    L = [f"RECRUITING FUNNEL — WEEK OF {start.strftime('%b %-d')}–{today.strftime('%b %-d, %Y')}",
         "=" * 52,
         f"{a['active_total']} active in funnel · {len(a['new_entries'])} new this week", ""]
    for name, stages, _ in BUCKETS:
        d = a["bucket_deltas"][name]
        dtxt = "" if d is None else (f"  ({'+' if d > 0 else ''}{d} wk)")
        inner = ", ".join(f"{s} {a['stage_counts'].get(s, 0)}" for s in stages)
        L.append(f"{name}: {a['bucket_counts'][name]}{dtxt}")
        L.append(f"   {inner}")
    L.append("")
    if not a["have_prev"]:
        L.append("(Baseline saved — week-over-week movement starts next week.)")
        L.append("")

    def block(title, moves, arrow=True):
        if not moves:
            return
        L.append(f"{title} ({len(moves)}):")
        for m in moves:
            tail = (f"  {m['from']} -> {m['to']}"
                    if arrow and m.get("from") else "")
            L.append(f"   {m['name']}{tail}")
        L.append("")

    block("HIRED THIS WEEK", a["hired_wk"])
    block("ADVANCED", a["advanced"])
    block("NEW INTO PIPELINE", a["new_entries"], arrow=False)
    block("PASSED THIS WEEK", a["passed_wk"])
    block("SLIPPED BACK", a["regressed"])
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Send / run
# ---------------------------------------------------------------------------

def _send_email(cfg, subject, html_body, plain_body):
    user = cfg["gmail"]["email"]
    pw = cfg["gmail"]["app_password"]
    recipients = cfg["digest"]["to_emails"]
    if not (user and pw and recipients):
        raise RuntimeError(
            "Weekly email requires GMAIL_EMAIL, GMAIL_APP_PASSWORD, and "
            "RECRUITING_DIGEST_TO (or DIGEST_TO_EMAIL)."
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


def build(today=None):
    cfg = config.load_config()
    today = today or datetime.now().date()
    candidates = list(notion.fetch_candidates(
        cfg["notion"]["token"], cfg["notion"]["database_id"]))
    prev = load_state()
    a = analyze(candidates, prev, today)
    subject = (f"Recruiting funnel · {a['active_total']} active · "
               f"+{len(a['new_entries'])} new · week of {today.isoformat()}")
    html = compose_html(today, a)
    plain = compose_plain(today, a)
    return subject, html, plain, a, cfg, candidates


def run(today=None, dry_run=False):
    subject, html, plain, a, cfg, candidates = build(today=today)
    if dry_run:
        print(plain)
        print(f"\n[dry-run] would send '{subject}' to "
              f"{', '.join(cfg['digest']['to_emails']) or '(no recipients set)'}")
        print("[dry-run] snapshot NOT saved")
        return
    _send_email(cfg, subject, html, plain)
    save_state(candidates, today or datetime.now().date())
    print(f"weekly funnel: sent — active={a['active_total']} "
          f"new={len(a['new_entries'])} advanced={len(a['advanced'])} "
          f"hired={len(a['hired_wk'])} passed={len(a['passed_wk'])}")
