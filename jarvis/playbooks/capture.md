# Playbook — Conversation Capture

You are given a transcript of a real conversation Justin had — a call, meeting,
or voice note, often from a Plaud recorder or a mic recording. It may be messy:
one audio channel, no speaker labels, filler words, transcription errors. Read
it generously and extract what matters.

## Produce

1. **TL;DR** — 2–3 sentences on what the conversation was and what came of it.
2. **Highlights** — the concrete facts: decisions, numbers, dates, names,
   commitments, objections, anything Justin would want on the record.
3. **Next steps** — specific action items, with an owner and a due date where the
   conversation implies one.
4. **Pipeline update** — try to match the conversation to a person in the
   Recruiting or Mortgage pipeline (match by name, then confirm with
   company / role / loan details from the foundation's `pipelines.json`).
   - **Confident match:** append a dated highlight line to that record's
     `Notes`, set `Last Contact` = today and the channel used, and update
     `Stage`/`Status`, `Next Action`, and `Next Follow-Up` if the conversation
     changed them.
   - **No confident match / new person:** say so and propose creating a record
     with the details you heard — leave it for Justin to confirm. Do not create
     or guess a record silently.

## Rules

- **Capture only — never send.** Logging highlights and updating stages is fine;
  do not send any outbound message as part of capture, even if the conversation
  implies a follow-up is due. (A follow-up gets handled later by the nurture
  loop, draft-first.)
- **Don't fabricate.** If a name, number, or detail is unclear in the
  transcript, mark it uncertain rather than inventing it. If the audio was too
  noisy to be reliable, say what you could and couldn't extract.
- **PII stays internal.** Sensitive details (DOB, SSN fragments, full account
  numbers) belong only in private Notes, never anywhere outbound.
- Honor every guardrail in the foundation.

Keep the spoken-facing summary short; the detail goes into Notion.
