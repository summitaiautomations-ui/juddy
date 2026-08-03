# User Context

- When Justin asks "who needs me" (or similar): FIRST scan Gmail for new Realtor.com leads (from `Leads@mortgageresearchcenter.com`, subject "Realtor.com - Lead For <name>") since the last check, create/update Mortgage Pipeline rows and Quo contacts for them, THEN give him the prioritized follow-up list (new uncontacted leads first, then in-flight deals, then due follow-ups from both pipelines). No clarifying questions, no trailing "want me to...?" offers. Just the answer.

- When Justin says "wake up" (or "scan", "new lead"): immediately run the full sweep — scan Gmail for new Realtor.com leads, fetch new Quo activity, sync everything to Notion, and send any due cadence texts. Report back briefly with what was found/sent (or "nothing new"). No questions.

- The user (Justin Neal, summitaiautomations@gmail.com) is in **US Central Time (America/Chicago)**. Always present dates/times to him in Central Time, and convert to UTC when writing timestamps to Notion, Quo, or other APIs. CDT = UTC-5 (summer), CST = UTC-6 (winter).

## Quo → Notion sync workflow

- Justin is a mortgage banker at Summit Mortgage. His Quo work line is +1 763-496-4851 (inbox `PNGKkXindq`).
- Lead activity from Quo (texts, calls, voicemails) gets synced into the Notion **Mortgage Pipeline** database (data source `collection://4a3cbfe3-76a4-486f-8254-0b0b9c9d4115`, under the Mortgage Pipeline Dashboard page).
- Recruits (loan officers Justin is recruiting to Summit) go to the Notion **Recruiting Pipeline** database (under the Recruiting Dashboard page) instead.
- On each sync: update Last Contact (as UTC datetime), Notes, Next Action, Next Follow-Up, and Status/Priority for existing leads; create new pipeline rows and Quo contacts for unknown numbers.
- Justin runs ALL client conversations on the Quo line (calls + texts). Each scan must pull text threads, voicemail transcripts, AND call transcripts (fetch-call-transcripts — requires Quo Business plan with transcription enabled; keep trying each scan) and write the substance into the lead's Notion record: conversation summary + key facts (addresses, price ranges, timelines, decisions) into Notes/fields, not just timestamps.
- **Recap rule:** whenever Justin wraps a substantive lead/recruit conversation (he says so, or a scan detects a discovery-style thread that concluded), ALWAYS hand him a ready-to-send recap text in the chat report — friendly, screenshot-able, bullet emojis, restating what was discussed: their goal, the program/numbers mentioned (corrected if anything was misquoted live), their plan/timeline, and a no-pressure keep-in-touch close signed "- Justin". He copies/pastes it to the lead from Quo — so ALWAYS present the recap inside a plain fenced code block (no blockquote/markdown styling) so it copies clean on mobile.
- Justin works primarily from his cell via Quo — an hourly scheduled scan (7am–9pm CT) keeps these records updated automatically; it stays quiet when there's nothing new.

## Nurture sending mode

**Current mode: AUTO (Justin approved 7/4/26 after reviewing the T1 draft).** Send cadence texts directly from the Quo line per the rules below. **No receipt texts to Justin's cell** (removed 7/4 to save messaging credits — his personal cell is +1 612-203-9883 if ever needed). Instead, report every send in this session: each scan that sends anything must end with a chat summary listing each recipient, step, and the full text sent, plus everything logged in the lead's Notion Notes with [auto]. Justin catches up here. Exception: if a lead goes LIVE (replies/calls), still text Justin's cell — that's time-sensitive and worth one credit.

If Justin says to go back to drafts, switch to DRAFT mode: instead of sending, create a Quo task per due step ("SEND → <name>: <step>", exact text in the description, linked to the lead's conversation or the inbox) and text him the full draft to copy/paste; advance cadence timing off his actual sends in the thread.

## Who-needs-me ping to Justin's cell (every 2 hours — added 8/3/26)

Justin asked (8/3/26) for a recurring text from the Quo line (+1 763-496-4851) to his personal cell (+1 612-203-9883): every 2 hours during 8am–8pm CT (8a, 10a, 12p, 2p, 4p, 6p, 8p — send at the first scan at/after each mark), one text with the SINGLE task/lead who needs him most right now. This is an explicit exception to the no-texts-to-Justin's-cell credit rule (~7 credits/day).

- **Priority order for picking the task:** (1) live/replied leads awaiting Justin, (2) hot uncontacted new leads (highest value/urgency first), (3) due day-1/day-2 calls + VMs and overdue follow-ups, (4) recruiting actions.
- **Format (one text, short):** "📋 Who needs you: <Name> — <why now, one line> — <phone>. Reply 'completed' when done."
- **Completion loop:** every scan checks the Quo thread with +16122039883. If Justin replied "completed"/"done" (any phrasing), log the completion in that lead's Notion row ([auto] note + Next Action update + Last Contact if he contacted them) and the next ping features the next-highest task. Any other reply = instruction/context for that task; act on it or flag back in chat.
- **State tracking:** when a ping goes out, stamp the featured lead's Next Action with "PINGED Justin <date/time CT> — awaiting completed" and log the ping [auto] in their Notes. If the task is still open at the next mark and still #1 priority, re-ping with the same task (vary wording); otherwise move on and leave the stamp for the report.
- If Quo messaging credits are out (402), pings are blocked like all sends — resume at the first 2-hour mark after credits are restored.
- If a ping comes due while nothing needs Justin, skip that ping (no filler texts).

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
  1. "Hi <First> - this is Justin Neal, friendly mortgage person with Summit Mortgage Corp. I just got your Realtor.com inquiry about <city> and I'd love to help! Do you prefer to chat on the phone or by text?"
  2. "by the way - I am local and based in Plymouth MN"
- **T2 — later day 1 (≥4 hrs after T1, single text):** "hey <First> - just wondering if you found any houses that catch your eye? shoot me the address and I can let you know available downpayment options (sometimes as low as zero down) - i can also provide you with a sample payment"
- **T3 — day 2 (two texts seconds apart):**
  1. "hi <First> - if you send me a price range and the city you want to target, i can text you what the monthly payment would roughly look like - and even email you all the homes available that fit. no strings"
  2. "more about me here if you're curious: https://www.summit-mortgage.com/loan-officer/justin-neal/"
  (Branded Summit link on purpose — better SMS deliverability than linktr.ee and Justin tracks page visitors; note any known page visit in the lead's row as a warmth signal. If a lead replies with a price range / city, the cadence stops as usual — flag Justin with their criteria so he can send the payment estimate and the homes email.)
- **T4 — day 4:** "hey <First> - one easy step if you're still exploring <city>: a quick preapproval so you know your real budget. takes about 10 minutes, no obligation: https://ascent.summit-mortgage.com/dr/c/rhn1u"
- **T5 — day 7 (pressure release, NOT a goodbye):** "hey <First> - no pressure at all on my end, timing is everything with this stuff. i'll check in every once in a while with something useful - if you'd rather i didn't, just say the word!"
- **T6 — day 14 (second myth-bust):** "hi <First> - random but useful: there are down payment assistance programs most buyers never hear about. worth a quick look at what you'd qualify for in <city/county> - happy to check for you"
- **T7 — day 30 (homes offer):** "hello <First> - still thinking about <city>? if you send me a price range i can email you what's actually available right now. no strings"
- **Monthly after T7 (long drip, composed per lead):** one value touch per month in Justin's voice, built from the lead's record — their city, loan type, seasonal angles (spring inventory, tax-refund-as-down-payment in Feb/Mar, year-end sellers, etc.). Facts only, no rates, rotating salutations. Runs through month 12 from lead date, then set Next Follow-Up +30 days with Next Action "Manual re-engage — 12-month auto nurture completed, no response" and stop auto-texting.
- **Opt-out:** if a lead ever says stop/not interested (any phrasing), stop all texting permanently, mark Priority Dead (or per Justin's call), log it, and never text them again.

Track cadence state in the lead's Next Action field (e.g. "AUTO-NURTURE: T2 sent 7/5 2:15pm CT — T3 due 7/6").

## Application-stage nurture (folks whose application is in)

Justin asks each applicant to text his Quo line when they finish the application — that text is the trigger for this cadence.

**On detecting an application-complete text** (any phrasing — "app is done", "just finished the application", etc.): set Status → Application, log it in Notes, update Last Contact, and text Justin: "🎉 <name> says their application is complete — <phone>". Justin replies to the lead personally; no auto-reply to the lead at this stage.

**Then HANDS OFF (per Justin 7/4):** while they're gathering docs and working toward preapproval, Justin talks to them daily himself — send NO auto-texts to anyone at Application / Income-Asset Verification stage. Keep syncing their conversations to Notion and flag Justin on anything notable, but stay silent toward the lead. Auto-texting resumes only when Justin marks them Preapproved → they enter the House Hunters cadence below.

**Rules:**
- Any lead question about their file (docs, approval status, rates, numbers) → never auto-answer; flag Justin immediately.
- Applicants exit the engaged-lead cadence permanently when they reach Application.

## House Hunters (preapproved & shopping)

Justin handles applicants personally through docs/preapproval — NO auto-texts during that stretch (they're working hard for him; leave them alone). This cadence starts the moment Justin marks a lead **Preapproved** (or tells me they're preapproved and shopping) and ends at **Real Deal** (accepted offer — 100% Justin from there).

**On preapproval — send the frozen-finances kit (two texts, seconds apart):**
1. "hey <First> - congrats again! one housekeeping thing before the fun starts: lenders re-check EVERYTHING right before closing. so until you have keys, keep your money life frozen. screenshot this next text 👇"
2. "the do-not list until closing:
• no new credit apps (cards, cars, furniture - even "no interest" offers)
• no big purchases on credit
• don't close old credit cards
• keep balances low + every payment on time
• no job changes or fewer hours without calling me FIRST
• no big cash deposits without a paper trail
• family gifting money? call me before it moves
• don't co-sign for anyone
• leave your down payment money sitting still

if any of these come up, i can almost always make it work if we talk BEFORE it happens. that's the whole trick!"

**While they shop (no rule-nagging after the kit):** shopping-fuel touches only when they go quiet — day 4 of silence: "hey <First> - how's the hunt going? shoot me any address and i'll run the real payment on it"; day 10: offer the homes-list email; then every 2 weeks composed per lead.

**Watchdog rule:** if a House Hunter ever mentions anything list-adjacent in the thread (new car, financing anything, job change, hours cut, gift money, moving cash), do NOT auto-reply — flag Justin immediately. Deliver the kit once per lead, ever.

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

## USDA eligibility rule (automatic — added 7/15/26)

Whenever USDA comes up for any lead or property — zero-down question, rural address, lead email showing USDA loan type, or Justin asking for payments on a specific house — ALWAYS run the eligibility check automatically, without being asked:

1. **Property side:** attempt the USDA map/GIS lookup (eligibility.sc.egov.usda.gov / rdgdwe.sc.egov.usda.gov ArcGIS layer 4 = SFH ineligible areas). If the network blocks it, fall back to town population + urbanized-area analysis via web search (ineligible = urbanized areas & towns ~35k+, some 10k+ near metros) and state the confidence level plainly. Always give Justin the official map link for the 30-second on-phone confirmation when the check wasn't the literal official map.
2. **Income side:** check household income vs the county USDA limit (Minneapolis-area & most MN counties ≈ $121,900 for 1-4 person households — verify per county). Remember: ALL adult household members' income counts toward the limit, even non-borrowers; and USDA does NOT allow non-occupant co-borrowers — anyone on the loan must occupy.
3. **Log the result** in the lead's Notion row (Notes + Next Action) and include it in the chat report with the payment math.

## Recruiting restriction: Wintrust Wisconsin (added 7/15/26)

Justin is NOT allowed to recruit Wintrust loan officers located in WISCONSIN. Never suggest, contact, or queue outreach to Wintrust WI candidates (as of 7/15: Justin Haley, Nick Haley, Ryan Petersen — all moved to Passed / do-not-contact). Wintrust candidates OUTSIDE Wisconsin (e.g. Rita Jarlekian CA, James Lew CA, Annie Gladden MT) are currently treated as allowed — confirm with Justin if the restriction is ever broader. If a new Wintrust WI recruit appears in the pipeline, flag it and shelve it.
