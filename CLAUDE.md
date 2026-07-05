# User Context

- When Justin asks "who needs me" (or similar): FIRST scan Gmail for new Realtor.com leads (from `Leads@mortgageresearchcenter.com`, subject "Realtor.com - Lead For <name>") since the last check, create/update Mortgage Pipeline rows and Quo contacts for them, THEN give him the prioritized follow-up list (new uncontacted leads first, then in-flight deals, then due follow-ups from both pipelines). No clarifying questions, no trailing "want me to...?" offers. Just the answer.

- When Justin says "wake up" (or "scan", "new lead"): immediately run the full sweep — scan Gmail for new Realtor.com leads, fetch new Quo activity, sync everything to Notion, and send any due cadence texts. Report back briefly with what was found/sent (or "nothing new"). No questions.

- The user (Justin Neal, summitaiautomations@gmail.com) is in **US Central Time (America/Chicago)**. Always present dates/times to him in Central Time, and convert to UTC when writing timestamps to Notion, Quo, or other APIs. CDT = UTC-5 (summer), CST = UTC-6 (winter).

## Quo → Notion sync workflow

- Justin is a mortgage banker at Summit Mortgage. His Quo work line is +1 763-496-4851 (inbox `PNGKkXindq`).
- Lead activity from Quo (texts, calls, voicemails) gets synced into the Notion **Mortgage Pipeline** database (data source `collection://4a3cbfe3-76a4-486f-8254-0b0b9c9d4115`, under the Mortgage Pipeline Dashboard page).
- Recruits (loan officers Justin is recruiting to Summit) go to the Notion **Recruiting Pipeline** database (under the Recruiting Dashboard page) instead.
- On each sync: update Last Contact (as UTC datetime), Notes, Next Action, Next Follow-Up, and Status/Priority for existing leads; create new pipeline rows and Quo contacts for unknown numbers.
- Justin works primarily from his cell via Quo — an hourly scheduled scan (7am–9pm CT) keeps these records updated automatically; it stays quiet when there's nothing new.

## Nurture sending mode

**Current mode: AUTO (Justin approved 7/4/26 after reviewing the T1 draft).** Send cadence texts directly from the Quo line per the rules below. Immediately after each send, text a receipt from the Quo line to Justin's personal cell **+1 612-203-9883**: "✅ Sent T1 to Brooke Niebeling (651-558-7290): <full text that was sent>" — always include the full sent text so he sees exactly what went out. If several sends happen in one scan, send one receipt per lead, back-to-back.

If Justin says to go back to drafts, switch to DRAFT mode: instead of sending, create a Quo task per due step ("SEND → <name>: <step>", exact text in the description, linked to the lead's conversation or the inbox) and text him the full draft to copy/paste; advance cadence timing off his actual sends in the thread.

## Auto-nurture text cadence (new Realtor.com leads)

When a new lead email arrives from `Leads@mortgageresearchcenter.com`: create the Mortgage Pipeline row + Quo contact, then run this text cadence from +1 763-496-4851. Justin calls and leaves VMs on day 1 and day 2 himself — the texts complement his calls, they don't replace them.

**Rules (non-negotiable):**
- Send only between 8:00am and 8:00pm CT; if a step comes due outside that window, send at the next scan inside it.
- If the lead replies (text or call) at ANY point: stop the cadence immediately, update their row, and flag Justin. Never send another auto-text to a lead who has engaged.
- Never restart or re-run a cadence for the same lead. Log every auto-send in the lead's Notes with an `[auto]` prefix and update Last Contact.
- Tone per the 2026 NextGen Homebuyer Report: low-pressure, one idea per text, myth-busting, alignment-signaling. No rate quotes, no info dumps.
- **Friend approach (applies to every text after T1, in all cadences):** casual openers; no capitalized sentence starts (lowercase "i" is fine and preferred); keep proper nouns capitalized (names, cities, Summit); never reintroduce yourself after first contact ("Justin again" etc. is banned); write like a friend texting — not a rep working a script. T1 keeps the professional intro and normal capitalization since it's first contact.
- **Salutation rotation:** vary openers across a lead's texts — rotate among "hi <First> -", "hey <First> -", "hello <First> -", and "morning <First> -" (that last one only if it's actually morning in CT). NEVER open with just their bare first name. Never use the same opener twice in a row for the same lead. The salutations written in the step templates below are defaults — swap them per this rule as needed.

**Steps** (`<First>` = first name, `<city>` = property city from the lead email):
- **T1 — on arrival (two texts, seconds apart):**
  1. "Hi <First> - this is Justin Neal, mortgage banker with Summit Mortgage. I just got your Realtor.com inquiry about <city> and I'd love to help! Do you prefer to chat on the phone or by text?"
  2. "by the way - I am local and based in Plymouth MN"
- **T2 — later day 1 (≥4 hrs after T1, single text):** "hey <First> - just wondering if you found any houses that catch your eye? shoot me the address and I can let you know available downpayment options (sometimes as low as zero down) - i can also provide you with a sample payment"
- **T3 — day 2 (two texts seconds apart):**
  1. "hey <First> - i know the mortgage stuff can feel overwhelming, so i keep things simple. what's the #1 question on your mind about buying?"
  2. "and if you want to know who you'd be working with, here's a bit about me: https://www.summit-mortgage.com/loan-officer/justin-neal/"
  (Branded Summit link on purpose — better SMS deliverability than linktr.ee and Justin tracks page visitors; note any known page visit in the lead's row as a warmth signal.)
- **T4 — day 4:** "hey <First> - one easy step if you're still exploring <city>: a quick preapproval so you know your real budget. takes about 10 minutes, no obligation: https://ascent.summit-mortgage.com/dr/c/rhn1u"
- **T5 — day 7 (final):** "hey <First> - i won't keep bugging you! if the timing isn't right, no worries at all. save my number and reach out whenever you're ready. have a great one! - Justin @ Summit Mortgage www.linktr.ee/welcometosummit"
- **After T5 with no response:** set Next Follow-Up to +30 days with Next Action "Manual re-engage — auto cadence completed, no response."

Track cadence state in the lead's Next Action field (e.g. "AUTO-NURTURE: T2 sent 7/5 2:15pm CT — T3 due 7/6").

## Engaged-lead nurture cadence (leads who replied, then went quiet)

For Mortgage Pipeline leads with Status **Connected** or **Connected Live** whose last two-way exchange was within the past 30 days, and who then go silent. Texts are composed per lead from their Notion record (property, loan type, where the conversation left off) in Justin's voice — short, one idea, casual with dashes/exclamations.

**Steps (days of silence since last exchange):**
- **Day 3:** personal check-in referencing their specific situation (e.g. "Hi Kevin - any luck finding other homes in Eveleth? Happy to check any address for you.")
- **Day 7:** one-step value nudge — preapproval link if no application yet (https://ascent.summit-mortgage.com/dr/c/rhn1u), or offer to run updated numbers.
- **Day 14:** soft check-in with a relevant, factual note (their area, their program) — no rate quotes.
- **Day 30, then monthly:** brief "still here when you're ready" touch.

**Rules (in addition to the non-negotiables above — quiet hours, reply kill switch, [auto] logging):**
- Stops permanently if the lead advances to Application or beyond — active deals get Justin's personal attention, not drip texts.
- Skips leads Justin has explicitly paused (e.g. Michael Dumonceaux) and anyone marked Dead.
- Leads whose engagement is older than 30 days stay on Justin's manual call list — do not auto-text them.
- Composed texts must stick to facts already in the lead's record: no rates, no approval promises, no commitments. If the right message is unclear, flag Justin instead of sending.
