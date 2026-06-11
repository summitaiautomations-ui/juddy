# Playbook — Recruiting Pipeline (B2B)

Recruiting loan officers, branch managers, and operations talent to Summit
Mortgage Corp. Audience is **business-to-business** (other mortgage
professionals), so outreach may be sent when the permission mode allows — but
always personalise and always log.

Pipeline IDs and exact field names: see `pipelines.json` (`recruiting`).

## Stages (`Stage` property)

`Initial Outreach → Conversation → Interview → Offer → Hired` (or `Passed`).
Exclude `Hired` and `Passed` from active nurture.

## Warming track (`Nurture Stage` property)

`Not Started → Touch 1 → Touch 2 → Touch 3 → Touch 4 → Touch 5 → Engaged → Converted`.
Advance one step each time you complete a touch and the candidate hasn't yet
replied. Once they actively reply, move them to `Engaged` and follow Justin's
lead on cadence rather than the drip.

**Default cadence while warming:** space touches ~3–5 business days apart. Set
`Next Follow-Up` accordingly after each touch.

## Touch content by step

A recruiting candidate is a producer being courted, not a borrower. Tone:
peer-to-peer, respectful of their book of business, curious about their pain
points. Use `Current Company`, `Pain Points`, `2025 Units`/`2025 Volume`, and
`City`/`State` to personalise.

- **Touch 1 — Intro.** Why you're reaching out (saw their production / a
  referral / their market), one specific reason Summit might be worth a look,
  soft ask for a 10-minute call.
- **Touch 2 — Value/credibility.** A concrete differentiator (tech, comp,
  support, leadership) tied to a pain point they'd recognise.
- **Touch 3 — Social proof.** A peer who made a similar move and the outcome
  (real examples only).
- **Touch 4 — Direct, low-pressure ask.** Coffee/lunch/15-min call; make
  declining easy.
- **Touch 5 — Respectful break.** "I'll stop here for now — door's open."
  Then set a longer-dated `Next Follow-Up` (e.g. 30–60 days) and lower
  `Priority` if appropriate.

## Channels (`Preferred Channel`)

Honor the candidate's preferred channel. Email → Gmail. Simply Texting /
Telegram / LinkedIn / Phone → draft the message or call script for Justin.
Record what you used in `Last Touchpoint Type`.

## Intake (adding a candidate)

When Justin dictates a new candidate, create a record with at least
`Candidate Name`, and fill what's given: `Current Company`, `Role Type`
(Loan Officer / Branch Manager / Operations), `City`/`State`, contact fields,
`Source`, `Assigned Recruiter`, `Priority`, `Date Added` = today,
`Stage` = Initial Outreach, `Nurture Stage` = Not Started, and a `Next Follow-Up`.

## Logging checklist (every touch)

`Last Contact` = today · `Last Touchpoint Type` = channel used · advance
`Nurture Stage` · set next `Next Follow-Up` · append a dated line to `Notes`.
