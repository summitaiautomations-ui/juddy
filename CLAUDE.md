# User Context

- When Justin asks "who needs me" (or similar): FIRST scan Gmail for new Realtor.com leads (from `Leads@mortgageresearchcenter.com`, subject "Realtor.com - Lead For <name>") since the last check, create/update Mortgage Pipeline rows and Quo contacts for them, THEN give him the prioritized follow-up list (new uncontacted leads first, then in-flight deals, then due follow-ups from both pipelines). No clarifying questions, no trailing "want me to...?" offers. Just the answer.

- The user (Justin Neal, summitaiautomations@gmail.com) is in **US Central Time (America/Chicago)**. Always present dates/times to him in Central Time, and convert to UTC when writing timestamps to Notion, Quo, or other APIs. CDT = UTC-5 (summer), CST = UTC-6 (winter).

## Quo → Notion sync workflow

- Justin is a mortgage banker at Summit Mortgage. His Quo work line is +1 763-496-4851 (inbox `PNGKkXindq`).
- Lead activity from Quo (texts, calls, voicemails) gets synced into the Notion **Mortgage Pipeline** database (data source `collection://4a3cbfe3-76a4-486f-8254-0b0b9c9d4115`, under the Mortgage Pipeline Dashboard page).
- Recruits (loan officers Justin is recruiting to Summit) go to the Notion **Recruiting Pipeline** database (under the Recruiting Dashboard page) instead.
- On each sync: update Last Contact (as UTC datetime), Notes, Next Action, Next Follow-Up, and Status/Priority for existing leads; create new pipeline rows and Quo contacts for unknown numbers.
- Justin works primarily from his cell via Quo — an hourly scheduled scan (7am–9pm CT) keeps these records updated automatically; it stays quiet when there's nothing new.

## Auto-nurture text cadence (new Realtor.com leads)

When a new lead email arrives from `Leads@mortgageresearchcenter.com`: create the Mortgage Pipeline row + Quo contact, then run this text cadence from +1 763-496-4851. Justin calls and leaves VMs on day 1 and day 2 himself — the texts complement his calls, they don't replace them.

**Rules (non-negotiable):**
- Send only between 8:00am and 8:00pm CT; if a step comes due outside that window, send at the next scan inside it.
- If the lead replies (text or call) at ANY point: stop the cadence immediately, update their row, and flag Justin. Never send another auto-text to a lead who has engaged.
- Never restart or re-run a cadence for the same lead. Log every auto-send in the lead's Notes with an `[auto]` prefix and update Last Contact.
- Tone per the 2026 NextGen Homebuyer Report: low-pressure, one idea per text, myth-busting, alignment-signaling. No rate quotes, no info dumps.

**Steps** (`<First>` = first name, `<city>` = property city from the lead email):
- **T1 — on arrival:** "Hi <First> - this is Justin Neal, mortgage banker with Summit Mortgage Corp in Plymouth MN. I just got your Realtor.com inquiry about <city> and I'd love to help! Do you prefer to chat on the phone or by text?"
- **T2 — later day 1 (≥4 hrs after T1):** "Hi <First>, Justin again - just left you a voicemail. Quick thing worth knowing: most people think you need 20% down and perfect credit to buy a home. You usually don't - a lot of my buyers put down far less. Happy to run your real numbers whenever you're ready."
- **T3 — day 2:** "Hi <First> - I know the homebuying stuff can feel overwhelming, so I'll keep it simple. My job is to give you straight answers about what you actually qualify for - even when the honest answer makes me less money. Call or text, whatever's easier!"
- **T4 — day 4:** "Hi <First> - one easy step if you're still exploring <city>: a quick preapproval so you know your real budget. Takes about 10 minutes, no obligation: https://ascent.summit-mortgage.com/dr/c/rhn1u"
- **T5 — day 7 (final):** "Hi <First> - I won't keep bugging you! If the timing isn't right, no worries at all. Save my number and reach out whenever you're ready. Have a great one! - Justin @ Summit Mortgage www.linktr.ee/welcometosummit"
- **After T5 with no response:** set Next Follow-Up to +30 days with Next Action "Manual re-engage — auto cadence completed, no response."

Track cadence state in the lead's Next Action field (e.g. "AUTO-NURTURE: T2 sent 7/5 2:15pm CT — T3 due 7/6").
