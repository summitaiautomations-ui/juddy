# User Context

- When Justin asks "who needs me" (or similar): FIRST scan Gmail for new Realtor.com leads (from `Leads@mortgageresearchcenter.com`, subject "Realtor.com - Lead For <name>") since the last check, create/update Mortgage Pipeline rows and Quo contacts for them, THEN give him the prioritized follow-up list (new uncontacted leads first, then in-flight deals, then due follow-ups from both pipelines). No clarifying questions, no trailing "want me to...?" offers. Just the answer.

- The user (Justin Neal, summitaiautomations@gmail.com) is in **US Central Time (America/Chicago)**. Always present dates/times to him in Central Time, and convert to UTC when writing timestamps to Notion, Quo, or other APIs. CDT = UTC-5 (summer), CST = UTC-6 (winter).

## Quo → Notion sync workflow

- Justin is a mortgage banker at Summit Mortgage. His Quo work line is +1 763-496-4851 (inbox `PNGKkXindq`).
- Lead activity from Quo (texts, calls, voicemails) gets synced into the Notion **Mortgage Pipeline** database (data source `collection://4a3cbfe3-76a4-486f-8254-0b0b9c9d4115`, under the Mortgage Pipeline Dashboard page).
- Recruits (loan officers Justin is recruiting to Summit) go to the Notion **Recruiting Pipeline** database (under the Recruiting Dashboard page) instead.
- On each sync: update Last Contact (as UTC datetime), Notes, Next Action, Next Follow-Up, and Status/Priority for existing leads; create new pipeline rows and Quo contacts for unknown numbers.
- Justin works primarily from his cell via Quo — an hourly scheduled scan (7am–9pm CT, trigger `trig_01Q21hRZTX9WhBsbwTV46NGm`) keeps these records updated automatically; it stays quiet when there's nothing new.
