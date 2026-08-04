# Disc Diver — project memory

Disc golf reselling operation. Juddy dives lakes for lost discs, cleans them, and resells.

## Key facts (remember these)
- **Storefront "text me to buy" line: 612-203-9883 (Juddy's cell)** — used on the storefront's "I want this disc!" buttons, shipnote, and footer. (Quo/OpenPhone line 763-495-4851 is NOT working / abandoned — do not use it anywhere.)
- **Storefront:** discdiver.com (GitHub Pages, served from `docs/index.html`).
- **Juddy's personal email (on storefront + contact options): juddyneal@gmail.com** (note the spelling — juddy, not juddi). Each disc card has an "or email me" button that auto-fills the same disc inquiry as the text button. There is also a contact bar (Text + Or email me; no Call button).
- **Brand:** "Disc Diver". Socials — YouTube @funny_juddy, TikTok @disc_diver, Instagram @funny_juddy, Facebook /juddy.
- **Location / pickup:** Free local pickup in Coon Rapids, MN.
- **Shipping:** flat **~$8.50 for a single disc** (safe + profitable — a single disc is always ~$5 domestic, so never hand-calc singles). **Multiple discs & international are quoted per-order** (compare rates in Pirate Ship — UPS Ground often wins on 2+ disc boxes, USPS Ground Advantage on singles under 1 lb). All shipping is finalized over text, so the site number is just a starting anchor. Standard single-disc pack: 9.5×11 bubble mailer, ~8 oz. International (e.g. Canada) needs a customs form + HS code **9506.99** and runs 3–4× domestic — always quote the buyer first.
- **Sales flow:** buyer taps "I want this disc!" → texts 612-203-9883 → payment & shipping handled offline (no cart/checkout).
- **Storefront promo (live): "Buy 3 discs — shipping's on me · grab a 4th & take $5 off."** Tiered: 3+ discs = free shipping (Juddy covers the label, mix & match); adding a 4th disc = free shipping PLUS $5 off the order. Purpose is to inch orders 3→4 discs. The math: avg disc ~$9.50, multi-disc label ~$11 (3) / ~$12 (4), $0 COGS (lake-found). A 4th disc adds ~$9.50 revenue for only ~$1 more shipping, so even after the $5 off Juddy nets ~+$3.50/order vs a 3-disc order. Kept 3-disc free-ship as the base ON PURPOSE so 3-disc orders aren't lost (the $5 off only triggers at 4, so 3-disc buyers are unaffected). The $5 is a flat order discount (NOT a cheap 4th disc) so nobody can grab a $20+ collectible for near-free. Banner sits above the listings. Individual prices kept as-is (spread $5-24). (Prior live banner briefly read "Spend $35 or more" — replaced 2026-08-04.)

## How Juddy works with you (durable preferences — honor these)
- **Juddy runs terminal commands by copy-paste ONLY.** Every command you hand him must be complete and foolproof: NO placeholders to substitute (`<your-path>`, `<branch>`, etc.), no "edit this line first" steps. If a value is unknown (e.g. a path on his Mac), make the command discover it itself (`find`, `$(…)`) so it works pasted verbatim. Prefer one copy-paste block.
- **Be proactive.** Offer useful automations/improvements on your own initiative — don't wait to be asked.
- Juddy is non-technical about git/shell — explain in plain terms and keep steps to a minimum.
- **I nudge HIM for missing disc details — never the other way around (durable rule).** When cataloging or reviewing discs, BEFORE Juddy puts them away I must proactively call out anything missing so he can grab it while the disc is still in hand. Specifically, every disc listing should have: **flight numbers, weight, and condition.**
  - **Flight numbers:** always include them. If I don't know them, look them up (web). If I still can't find them, ASK Juddy and he'll check the disc.
  - **Weight & condition:** if either is missing, tell Juddy up front and ask for it — don't quietly leave it blank or guess silently. If I do estimate a condition from the photo, say so and ask him to confirm.
  - Surface ALL gaps for a batch in one go, before he shelves it — so he only has to pull the discs out once.

## NEVER show "DX" plastic on the storefront (durable rule)
- Nobody likes DX plastic, so it hurts listings. Even if a disc IS DX: leave the **plastic field blank** in the listing (don't write "DX") and strip "DX" from the notes. Keep the disc listed — just remove the DX label. Juddy fields any plastic questions over text. Applies to every new disc AND any existing listing that shows DX.

## Sales recap — show it proactively (durable preference)
- **Juddy likes to SEE the running totals. After logging ANY sale / payment / shipment, ALWAYS run `python3 scripts/disc-pics/sales-summary.py` and show him the recap** (discs sold, cash collected, still-owed, to-ship, available). Don't wait to be asked.
- The script reads `inventory.csv` + `orders.csv` and prints a compact per-buyer spreadsheet; it only reads (never writes) and stays local.

## Data & pipeline
- Inventory lives in `disc-pics-data/inventory.csv` and `disc-pics-data/sheet.csv` (the storefront live-fetches `sheet.csv`).
- Photos in `disc-pics-data/photos/<id>-<mold>.jpg`, composited on light gray (#eef0f2 / BGR 242,240,238).
- **Juddy's disc photos land on the Mac at `~/Pictures/disc-pics/inbox/` (files named `IMG_####.jpg`).** This is THE folder to pull from when he says "pics sent/pushed/in" — always check here (and the repo's `disc-pics-data/inbox-raw/` after push). Do NOT ask him where they are. If a `find` for new photos comes up empty, it's almost always because the search didn't go deep enough — this path is 3 levels under `~/Pictures`, so any depth-limited `find` will miss it (use `~/Pictures/disc-pics/inbox` directly).
- Mac mini pipeline: `import.sh` (Photo Booth → inbox) → `catalog.sh` (identify → stage to `incoming/`) → `sync.sh` (rebase + push). Photos staged to `incoming/` are additive; sync rebases before push to stay conflict-free.

## Pricing anchors
- $3 local-shop buyback is the floor; ~$9 is the average disc. Premium/signature/first-run/collectible discs priced higher.
- **ALWAYS run comps before pricing ANY disc (durable rule — Juddy, non-negotiable).** Every disc, every time — not just premium ones. Check BOTH sources:
  1. **eBay SOLD/completed listings** (`LH_Sold=1&LH_Complete=1`) for mold+plastic (and stamp/signature if notable). NOTE: eBay blocks direct WebFetch (403) — use WebSearch instead (`"<mold> <plastic> used disc golf ebay sold price"`).
  2. **Gotta Go Gotta Throw used inventory** (`gottagogottathrow.com`, e.g. `/collections/used-<brand>-discs` or WebSearch `"GGGT used <mold> <plastic>"`) — used discs graded on the SAME 1–10 sleepy scale Juddy uses, so it's often the cleanest condition-matched comp.
  **Then UNDERCUT them (durable rule — Juddy wants to WIN on price).** Price ~15–20% BELOW the cheapest condition-matched used comp (GGGT especially) so Disc Diver is always the better deal — buyers should see our price and not bother with eBay/GGGT. Discs are lake-found (~$0 cost), so we keep strong margin even below retail. Guardrails: never below the **$3 floor**, and don't fire-sale genuinely collectible/signature discs into the ground (undercut, but keep them premium vs their own comps). Note the comp range AND our undercut in the disc's notes.

## "DISC FOUND" video overlay cards (POND DISC HUNTER style)
- Branded transparent PNG overlay for TikTok/Reels/Shorts footage. Right-side dark rounded panel + top-left POND / DISC HUNTER logo, orange "DISC FOUND:" header, disc name, series, flight numbers box, teal desc, orange "AVAILABLE AT DISCDIVER.COM" CTA.
- **The TURN/FADE indicator arrows must ALWAYS point up** (green up-left for TURN, red up-right for FADE). Never point them down.
- **Always state "✓ NO NAME ON BACK — AVAILABLE FOR PURCHASE"** on the card (per Juddy's sample).
- Built from `discfound.html` in scratchpad, rendered to a transparent 1920×1080 PNG via headless chromium (`omitBackground:true`).

## Sales / order tracking (Notion — the private home)
- **Sales, buyers, paid/shipped tracking live in Notion, NOT the public repo.** Managed directly via the Notion MCP. Page: "Disc Diver — Sales Tracker" (`39a5ba8c-d26f-81b3-a0ff-cbaad82d4a56`) with an **Orders** database (data source `d9ecc30a-e988-45c3-a464-03539281e747`) and a **Customers** database (data source `ddfd0212-57b0-4864-8335-cd81208d1f3d`).
- When Juddy texts a sale/payment/shipment ("Joe paid", "shipped Nolan", "sold #14 to Sarah, Venmo"): update Notion directly (Orders: Paid/Shipped checkboxes, Paid Via, Fulfillment, Buyer; add Customer rows as needed) AND mark the disc `sold` in `disc-pics-data/*.csv` for the storefront.
- **Always log the shipping Label Cost (durable habit).** When an order ships, record the actual label cost in the Orders DB "Label Cost" field so the "Net" column reflects true profit (Net = revenue − COGS($0) − label). One label per box: record it once on one row of a multi-disc order.
- **Collector badge (storefront):** genuine collectibles/special editions get a purple "◆ COLLECTOR" badge via the `COLLECTOR` set in `docs/index.html` (PFN/patent, signature-glow, first runs, Ledgestone/team-collab limiteds). Vintage patent discs keep the gold "Vintage" badge instead. Don't badge common current-production signature discs — it dilutes the badge.
- Dashboard on the Notion page has live charts + view tabs (Ship Monday / To Collect / Pickups / Board / Repeat Buyers). Refresh the static KPI header numbers when they drift.

## Disc-return / league cross-reference (Notion — private; goodwill/community engine)
- Juddy dives Blue Ribbon Pines (BRP) most; discs often have a name/number on the back. He wants to return discs to **regulars/pros** to build goodwill. Two private Notion DBs on the Sales Tracker page:
  - **League Regulars** (data source `c6880302-1e7a-4b32-92d3-7a360344954b`): Player, Tier (Pro/Regular/Casual), Home Course, Phone, Discs Returned, Notes. **Built from Juddy's league standings/roster screenshots — he sends them, I read the names off and populate this**, tagging Pro/Regular/Casual.
  - **Found Discs / Owners** (data source `c0107352-5919-4854-9c44-f7501cd696e0`): Owner (title), Phone, Disc, Date Found, Status (Unclaimed/Contacted/Returned/Kept-Resold), Tier, **League Match** (relation → League Regulars, synced as "Discs Found"), Notes.
- **Workflow:** when Juddy rattles off a name/number found on a disc → log it in Found Discs AND cross-reference against League Regulars → tell him the tier ("that's a BRP regular/pro — prioritize returning it"). Link the relation when there's a match. Names/phones are personal data → PRIVATE (Notion only, never the public repo).
- Cleaner matches when Juddy includes a **last name or PDGA #** off the disc (first-name-only rarely matches the full-name roster). League Regulars data source: `c6880302-1e7a-4b32-92d3-7a360344954b` (currently ~111 BRP Mulligan League players loaded).
- **Quo guardrail:** Quo is currently Juddy's **recruiting / lead-nurturing** line — do NOT use it (or send disc-return texts through it) for the disc business until Juddy explicitly says he's switched it over. He'll signal when. Until then he texts owners from his personal phone and tells me who got theirs back so I mark Found Discs "Returned".
- Legacy (still present, gitignored/private): `disc-pics-data/orders.csv`, `customers.csv`, and `scripts/disc-pics/{track.py,make-tracker.py}` that built an xlsx. Notion supersedes these.

## Marking a disc sold (the most common request) — quick ref
1. Be on `claude/photobooth-disc-pics-vueawx` (this is what GitHub Pages serves).
2. In `disc-pics-data/sheet.csv`, find the row by **id** (e.g. `"062"`) and change
   the `status` column from `"available"` to `"sold"`. (Reverse to un-sell.)
3. Commit + push to `claude/photobooth-disc-pics-vueawx`. Live in ~1–2 min.
4. Also record the sale in the Notion Sales Tracker (see above).
Edits on any OTHER branch do NOT change the live site.

## Working branch
- `claude/photobooth-disc-pics-vueawx` (also the branch GitHub Pages publishes from)
