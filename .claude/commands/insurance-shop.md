---
description: Shop US auto-insurance — interview, coverage advice, ranked carrier shortlist with deep-links, and quote comparison.
argument-hint: "[optional: zip, state, vehicle, or 'compare' to skip to the comparison phase]"
allowed-tools: Task, Read, Write, WebSearch, WebFetch, Bash
---

You are launching the `auto-insurance-shopper` sub-agent for a US auto-insurance shopping session.

If the user passed arguments after the slash command, treat them as opening context (e.g. ZIP, vehicle, "compare"). If `$ARGUMENTS` is empty, start at Phase 1.

Hand control to the sub-agent now.

```
@auto-insurance-shopper

Begin a new shopping session. Opening context from the user (may be empty):
$ARGUMENTS

Read data/us-carriers.json, data/state-minimums.json, and data/discounts.json before your first message. If they are stale (>180 days) or missing for the user's state, re-verify with WebSearch against the user's state DOI and III.org.

Start with Phase 1 — the structured profile interview. Be concise: one numbered list, no preamble.
```
