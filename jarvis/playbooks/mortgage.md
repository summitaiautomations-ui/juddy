# Playbook — Mortgage Pipeline (consumers + realtor partners)

Two audiences here:

- **Borrowers** — consumers moving through the loan process. **Consumer rules
  apply: draft-only by default, TCPA/consent, no rate promises, fair lending.**
- **Realtor referral partners** — agents you nurture for referrals. Also
  consumer-adjacent; keep it professional and draft-for-approval, but the
  ready-made sequence below drives it.

Pipeline IDs and exact field names: see `pipelines.json` (`mortgage`).

## Borrower stages (`Status` property)

`Lead → Called 2x on Day 1 → Connected → Connected Live → Application →
Income/Asset Verification → Preapproved → Real Deal → Funded`, plus
`Friends and Family` for post-close. Exclude `Funded` and `Dead` from active
follow-up (Funded graduates to post-close nurture, below).

Stage-driven cadence (set `Next Follow-Up` and `Next Action` accordingly):

- **Lead / Called 2x on Day 1** — speed matters most. Attempt contact fast;
  next follow-up daily until you reach them.
- **Connected / Connected Live** — keep momentum; follow up every 1–2 days to
  push toward Application.
- **Application / Income-Asset Verification** — checklist-driven. `Next Action`
  should name the specific outstanding item (docs, AccountChek, etc.); follow
  up every 1–2 days until cleared.
- **Preapproved** — they're shopping. Weekly check-ins; offer to run numbers on
  specific properties. Conditional language only.
- **Real Deal** (under contract) — protect the close: confirm milestones
  (appraisal, conditions, lock). Touch ~weekly or as dates require, tied to
  `Closing Date`.

For every borrower touch, honor `Communication Channel` (Gmail / Simply Texting
/ Telegram / Phone Call). Email → draft in Gmail; text/Telegram/phone → produce
the message or script for Justin. **Default to drafting; do not auto-send to
borrowers.**

### Borrower messaging rules

- Conditional, never absolute: "based on what you've shared… subject to
  verification and underwriting."
- No guaranteed rates or "you're approved." No pressure tactics.
- Reference their real stage and `Next Action`; be a helpful guide, not a
  salesperson.

## Post-close nurture (`Status` = Friends and Family)

After Funded, move borrowers to `Friends and Family` for long-term nurture:
periodic value check-ins (anniversary of close, rate-watch / refi opportunities
when rates move meaningfully, referral asks). Keep it light and genuinely
useful — quarterly is a reasonable default unless a rate event warrants sooner.

## Realtor referral nurture

For nurturing agents into referral partners, use Justin's existing sequence in
Notion (`templates.realtor_nurture` in `pipelines.json`):

- **Phase 1 — Intro (4 touches over 2 weeks):** warm intro → social proof →
  value offer (co-branded flyers / calculator / market snapshot) → direct ask
  (coffee).
- **Phase 2 — Long-term value drip (monthly, 8 touches):** market update → rate
  summary → co-marketing → client success spotlight → seasonal tips → event
  invite → check-in + referral ask → partnership renewal.

Personalise the bracketed fields with **verified** specifics (agent name,
brokerage, real market numbers). If you can't verify a stat, leave the bracket
and flag it — never fabricate market data. Draft for Justin's approval.

## Intake (adding a lead)

New borrower: create a record with `Lead Name` and whatever is given —
`Lead Source`, `Loan Type`, `Loan Amount`, contact fields, `Property Address`,
`Priority`, `Date Added` = today, `Status` = Lead, and a `Next Follow-Up`.
Set `Next Action` to the immediate next step.

## Logging checklist (every touch)

`Last Contact` = today · add the channel to `Communication Channel` · update
`Status`/`Next Action` if it changed · set next `Next Follow-Up` · append a
dated line to `Notes`.
