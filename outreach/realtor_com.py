"""Realtor.com lead-notification email parser.

The notification body is plain text with `*Field Name:* value` patterns.
This module owns: detection, field extraction, and a one-pass Notes
summary for the new Notion record.
"""

import re


def is_realtor_lead_email(from_addr, subject):
    """True if this email looks like a Realtor.com new-lead notification.

    Only checks the FROM domain — Realtor.com varies its subject lines
    across campaigns. The body parser is strict enough that non-lead
    emails return None there if they slip through here.
    """
    return "realtor.com" in (from_addr or "").lower()


_FIELDS = {
    "lead_id": r"\*Lead ID:\*\s*(\S+)",
    "lead_date": r"\*Lead Date:\*\s*(.+?)(?:\s*\*|\n)",
    "name": r"\*\s*Lead Name:\*\s*(.+)",
    "phone": r"\*Phone Number:\*\s*(\d+)",
    "email": r"\*Email:\*\s*(\S+)",
    "credit": r"\*Credit Rating:\*\s*(\S+)",
    "county_state": r"\*Property County and State:\*\s*(.+)",
    "zip": r"\*Property Zip:\*\s*(\d+)",
    "property_value": r"\*Property Value:\*\s*(\d+)",
    "military": r"\*Served in Military:\*\s*(\S+)",
    "bankruptcy": r"\*Bankruptcy:\*\s*(\S+)",
    "loan_type": r"\*Loan Type:\*\s*(\S+)",
    "has_agent": r"\*Has Real Estate Agent:\*\s*(\S+)",
    "down_payment_pct": r"\*Down Payment Percent:\*\s*(\d+)",
    "property_type": r"\*Property Type:\*\s*(\S+)",
    "property_use": r"\*Property Use:\*\s*(\S+)",
    "loan_product": r"\*Loan Product:\*\s*(\S+)",
    "employment": r"\*Employment Status:\*\s*(\S+)",
    "income": r"\*Gross Income:\*\s*(\d+)",
    "first_time": r"\*First Time purchase:\*\s*(\S+)",
    "living_situation": r"\*Living Situation:\*\s*(\S+)",
    "purchase_status": r"\*Purchase Status:\*\s*(\S+)",
    "down_payment": r"\*Down Payment:\*\s*(\d+)",
    "city": r"\*Property City:\*\s*(.+)",
}


def parse(body):
    """Parse a Realtor.com lead body.

    Returns the full lead dict, or None if either Lead ID or Phone is
    missing — we need both to act on the lead.
    """
    if not body:
        return None

    out = {}
    for key, pattern in _FIELDS.items():
        m = re.search(pattern, body)
        out[key] = m.group(1).strip() if m else ""

    if out["county_state"]:
        parts = out["county_state"].split(",")
        out["state"] = parts[-1].strip() if len(parts) > 1 else ""
    else:
        out["state"] = ""

    if not out["lead_id"] or not out["phone"]:
        return None
    return out


def first_name(full_name):
    parts = (full_name or "there").strip().split()
    return parts[0] if parts else "there"


def build_notes_summary(lead):
    """A one-block summary of what Realtor.com told us about this lead.

    Designed to be the FIRST entry in the Notion Notes field so the
    record is useful at-a-glance the moment it's created. Subsequent
    activity gets appended below as dated `[YYYY-MM-DD]` lines.
    """
    return (
        f"Source: Realtor.com Lead ID {lead['lead_id']} ({lead.get('lead_date', '')})\n"
        f"Credit: {lead.get('credit') or '?'} | Income: ${lead.get('income') or '?'} | "
        f"First-time buyer: {lead.get('first_time') or '?'}\n"
        f"Property value: ${lead.get('property_value') or '?'} | "
        f"Down: ${lead.get('down_payment') or '?'} ({lead.get('down_payment_pct') or '?'}%)\n"
        f"Property: {lead.get('city', '')}, {lead.get('state', '')} "
        f"{lead.get('zip', '')} ({lead.get('property_type') or '?'}, "
        f"{lead.get('property_use') or '?'})\n"
        f"Loan: {lead.get('loan_product') or '?'} | "
        f"Has agent: {lead.get('has_agent') or '?'}\n"
        f"Living: {lead.get('living_situation') or '?'} | "
        f"Military: {lead.get('military') or '?'} | "
        f"BK: {lead.get('bankruptcy') or '?'} | "
        f"Employment: {lead.get('employment') or '?'}"
    )
