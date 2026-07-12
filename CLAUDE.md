# Disc Diver — project memory

Disc golf reselling operation. Juddy dives lakes for lost discs, cleans them, and resells.

## Key facts (remember these)
- **Storefront "text me to buy" line: 612-203-9883 (Juddy's cell)** — used on the storefront's "I want this disc!" buttons, shipnote, and footer. (Quo/OpenPhone line 763-495-4851 is NOT working / abandoned — do not use it anywhere.)
- **Storefront:** discdiver.com (GitHub Pages, served from `docs/index.html`).
- **Brand:** "Disc Diver". Socials — YouTube @funny_juddy, TikTok @funny_juddy, Instagram @funny_juddy, Facebook /juddy.
- **Location / pickup:** Free local pickup in Coon Rapids, MN.
- **Shipping:** $8.50 for a single disc; discounted combined rate for multiples (worked out over text).
- **Sales flow:** buyer taps "I want this disc!" → texts 612-203-9883 → payment & shipping handled offline (no cart/checkout).

## How Juddy works with you (durable preferences — honor these)
- **Juddy runs terminal commands by copy-paste ONLY.** Every command you hand him must be complete and foolproof: NO placeholders to substitute (`<your-path>`, `<branch>`, etc.), no "edit this line first" steps. If a value is unknown (e.g. a path on his Mac), make the command discover it itself (`find`, `$(…)`) so it works pasted verbatim. Prefer one copy-paste block.
- **Be proactive.** Offer useful automations/improvements on your own initiative — don't wait to be asked.
- Juddy is non-technical about git/shell — explain in plain terms and keep steps to a minimum.

## Data & pipeline
- Inventory lives in `disc-pics-data/inventory.csv` and `disc-pics-data/sheet.csv` (the storefront live-fetches `sheet.csv`).
- Photos in `disc-pics-data/photos/<id>-<mold>.jpg`, composited on light gray (#eef0f2 / BGR 242,240,238).
- Mac mini pipeline: `import.sh` (Photo Booth → inbox) → `catalog.sh` (identify → stage to `incoming/`) → `sync.sh` (rebase + push). Photos staged to `incoming/` are additive; sync rebases before push to stay conflict-free.

## Pricing anchors
- $3 local-shop buyback is the floor; ~$9 is the average disc. Premium/signature/first-run/collectible discs priced higher.
- **Going forward: check eBay listings + sold comps before pricing, to get Juddy top dollar** — especially signature/tour-series/first-run/collectible discs. Note the comp range in the disc's notes and price toward the high end of realistic sold prices (used-disc condition adjusted).

## "DISC FOUND" video overlay cards (POND DISC HUNTER style)
- Branded transparent PNG overlay for TikTok/Reels/Shorts footage. Right-side dark rounded panel + top-left POND / DISC HUNTER logo, orange "DISC FOUND:" header, disc name, series, flight numbers box, teal desc, orange "AVAILABLE AT DISCDIVER.COM" CTA.
- **The TURN/FADE indicator arrows must ALWAYS point up** (green up-left for TURN, red up-right for FADE). Never point them down.
- **Always state "✓ NO NAME ON BACK — AVAILABLE FOR PURCHASE"** on the card (per Juddy's sample).
- Built from `discfound.html` in scratchpad, rendered to a transparent 1920×1080 PNG via headless chromium (`omitBackground:true`).

## Sales / order tracking (Notion — the private home)
- **Sales, buyers, paid/shipped tracking live in Notion, NOT the public repo.** Managed directly via the Notion MCP. Page: "Disc Diver — Sales Tracker" (`39a5ba8c-d26f-81b3-a0ff-cbaad82d4a56`) with an **Orders** database (data source `d9ecc30a-e988-45c3-a464-03539281e747`) and a **Customers** database (data source `ddfd0212-57b0-4864-8335-cd81208d1f3d`).
- When Juddy texts a sale/payment/shipment ("Joe paid", "shipped Nolan", "sold #14 to Sarah, Venmo"): update Notion directly (Orders: Paid/Shipped checkboxes, Paid Via, Fulfillment, Buyer; add Customer rows as needed) AND mark the disc `sold` in `disc-pics-data/*.csv` for the storefront.
- Dashboard on the Notion page has live charts + view tabs (Ship Monday / To Collect / Pickups / Board / Repeat Buyers). Refresh the static KPI header numbers when they drift.
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
