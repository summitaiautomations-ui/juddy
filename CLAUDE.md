# Disc Diver — project memory

Disc golf reselling operation. Juddy dives lakes for lost discs, cleans them, and resells.

## Key facts (remember these)
- **Business contact number (Quo / OpenPhone): 763-495-4851** — this is the public "text me to buy" line used on the storefront's Claim buttons.
- **Storefront:** discdiver.com (GitHub Pages, served from `docs/index.html`).
- **Brand:** "Disc Diver". Socials — YouTube @discdiver, TikTok @funny_juddy, Instagram @disc_diver, Facebook /discdiver.
- **Location / pickup:** Free local pickup in Coon Rapids, MN.
- **Shipping:** $8.50 for a single disc; discounted combined rate for multiples (worked out over text).
- **Sales flow:** buyer taps "Claim this disc" → texts 763-495-4851 → payment & shipping handled offline (no cart/checkout).

## Data & pipeline
- Inventory lives in `disc-pics-data/inventory.csv` and `disc-pics-data/sheet.csv` (the storefront live-fetches `sheet.csv`).
- Photos in `disc-pics-data/photos/<id>-<mold>.jpg`, composited on light gray (#eef0f2 / BGR 242,240,238).
- Mac mini pipeline: `import.sh` (Photo Booth → inbox) → `catalog.sh` (identify → stage to `incoming/`) → `sync.sh` (rebase + push). Photos staged to `incoming/` are additive; sync rebases before push to stay conflict-free.

## Pricing anchors
- $3 local-shop buyback is the floor; ~$9 is the average disc. Premium/signature/first-run/collectible discs priced higher.

## Working branch
- `claude/photobooth-disc-pics-vueawx`
