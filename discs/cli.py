"""Entry: python -m discs <command> [args]."""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from discs import config, generator
from discs.disc import Disc

SEP = "=" * 72
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif"}
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _input_int(prompt):
    raw = input(prompt).strip()
    return int(raw) if raw else None


def _print_listings(result):
    """Print the listing fields shared by both text and photo paths."""
    print()
    print(SEP)
    print("eBay TITLE")
    print(SEP)
    title = result["ebay_title"]
    print(title)
    print(f"(length: {len(title)} / 80)")

    print()
    print(SEP)
    print("eBay DESCRIPTION")
    print(SEP)
    print(result["ebay_description"])

    print()
    print(SEP)
    print("BST POST  (Reddit r/discexchange · DGCR BST · Marketplace Disc Golf app)")
    print(SEP)
    print(result["bst_post"])

    print()
    print(SEP)
    print("eBay CATEGORY")
    print(SEP)
    print(result["suggested_ebay_category"])

    print()
    print(SEP)
    print("COMP PRICING — paste into eBay → Advanced → Sold listings")
    print(SEP)
    print(result["comp_pricing_search_query"])


def _print_usage(result):
    usage = result.get("_usage", {})
    print()
    print(
        f"(tokens in={usage.get('input_tokens', '?')} "
        f"out={usage.get('output_tokens', '?')} "
        f"cache_read={usage.get('cache_read_input_tokens', 0)})"
    )


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "disc"


def _save_output_file(result, *, source_label):
    """Persist the full result as markdown in discs/output/. Returns the path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    extracted = result.get("extracted_disc") or {}
    mold_slug = _slug(extracted.get("mold", "manual"))
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = OUTPUT_DIR / f"{timestamp}_{mold_slug}.md"

    lines = [f"# Disc listing — {timestamp}", f"_Source: {source_label}_", ""]
    if extracted:
        weight = extracted.get("weight")
        weight_str = f"{weight}g" if weight else "(not visible)"
        lines += [
            "## Identification",
            "",
            f"- **Brand:** {extracted['brand']}",
            f"- **Mold:** {extracted['mold']}",
            f"- **Plastic:** {extracted['plastic']}",
            f"- **Weight:** {weight_str}",
            f"- **Color:** {extracted['color']}",
            f"- **Stamp:** {extracted['stamp_condition']}",
            f"- **Back ink:** {extracted.get('back_ink', '?')}",
            f"- **Sleeve (1-10):** {extracted['estimated_sleeve']}",
            f"- **Category:** {extracted['category']}",
            f"- **Notes:** {extracted['extraction_notes']}",
            "",
        ]
    title = result["ebay_title"]
    lines += [
        "## eBay TITLE",
        f"`{title}` ({len(title)}/80)",
        "",
        "## eBay DESCRIPTION",
        "```",
        result["ebay_description"],
        "```",
        "",
        "## BST POST",
        result["bst_post"],
        "",
        "## eBay CATEGORY",
        result["suggested_ebay_category"],
        "",
        "## COMP PRICING",
        f"`{result['comp_pricing_search_query']}`",
        "",
    ]
    path.write_text("\n".join(lines))
    return path


def _copy_to_clipboard(text):
    """macOS pbcopy. Returns True on success, False if pbcopy isn't available."""
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _post_run(result, *, source_label):
    """Save markdown + copy eBay title to clipboard. Prints status to stderr."""
    path = _save_output_file(result, source_label=source_label)
    print(f"\nSaved: {path}", file=sys.stderr)
    if _copy_to_clipboard(result["ebay_title"]):
        print("(eBay title copied to clipboard — ⌘V to paste)", file=sys.stderr)


def cmd_generate(args):
    """Interactive: prompt for disc details, generate listings."""
    print("Enter disc details (blank line skips optional fields).")
    brand = input("Brand: ").strip()
    mold = input("Mold: ").strip()
    plastic = input("Plastic: ").strip()
    weight = _input_int("Weight (g): ")
    color = input("Color: ").strip() or None
    condition = _input_int("Sleeve condition (1-10): ")
    special_run = input("Special run (optional): ").strip() or None
    notes = input("Notes (optional): ").strip() or None

    if not brand or not mold or not plastic:
        print("Brand, mold, and plastic are required.", file=sys.stderr)
        sys.exit(2)

    disc = Disc(
        brand=brand, mold=mold, plastic=plastic,
        weight=weight, color=color, condition=condition,
        special_run=special_run, notes=notes,
    )

    cfg = config.load()
    print("\nGenerating…", file=sys.stderr)
    result = generator.generate_listings(disc, api_key=cfg["anthropic_api_key"])

    _print_listings(result)
    _print_usage(result)
    _post_run(result, source_label=f"manual:{brand} {mold}")


def _print_identification(extracted):
    print()
    print(SEP)
    print("DISC IDENTIFIED FROM PHOTO  (verify before listing)")
    print(SEP)
    weight = extracted.get("weight")
    weight_str = f"{weight}g" if weight else "(not visible — check the disc rim)"
    print(f"Brand:           {extracted['brand']}")
    print(f"Mold:            {extracted['mold']}")
    print(f"Plastic:         {extracted['plastic']}")
    print(f"Weight:          {weight_str}")
    print(f"Color:           {extracted['color']}")
    print(f"Stamp:           {extracted['stamp_condition']}")
    print(f"Back ink:        {extracted.get('back_ink', '?')}")
    print(f"Sleeve (1-10):   {extracted['estimated_sleeve']}  (estimated from photo)")
    print(f"Category:        {extracted['category']}")
    print(f"Notes:           {extracted['extraction_notes']}")


def cmd_photo(args):
    """Snap-a-pic: identify the disc from a photo, then generate listings."""
    if len(args) < 1:
        print("usage: python -m discs photo <image-path>", file=sys.stderr)
        sys.exit(2)

    image_path = args[0]
    cfg = config.load()
    print(f"Identifying disc from {image_path}…", file=sys.stderr)
    result = generator.generate_from_image(image_path, api_key=cfg["anthropic_api_key"])

    _print_identification(result["extracted_disc"])
    _print_listings(result)
    _print_usage(result)
    _post_run(result, source_label=Path(image_path).name)


def cmd_batch(args):
    """Batch: process every photo in a folder. One Claude call per photo."""
    if len(args) < 1:
        print("usage: python -m discs batch <folder>", file=sys.stderr)
        sys.exit(2)

    folder = Path(args[0]).expanduser()
    if not folder.is_dir():
        print(f"Not a directory: {folder}", file=sys.stderr)
        sys.exit(2)

    photos = sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTO_EXTENSIONS)
    if not photos:
        print(f"No photos found in {folder}", file=sys.stderr)
        sys.exit(1)

    cfg = config.load()
    print(f"Found {len(photos)} photo(s) in {folder}. Processing…\n", file=sys.stderr)

    succeeded, failed = [], []
    for i, photo in enumerate(photos, 1):
        print(f"[{i}/{len(photos)}] {photo.name}", file=sys.stderr)
        try:
            result = generator.generate_from_image(str(photo), api_key=cfg["anthropic_api_key"])
            path = _save_output_file(result, source_label=photo.name)
            ext = result["extracted_disc"]
            weight = ext.get("weight")
            weight_str = f"{weight}g" if weight else "?g"
            print(
                f"   → {ext['brand']} {ext['plastic']} {ext['mold']} "
                f"{weight_str} {ext['color']}  →  {path.name}",
                file=sys.stderr,
            )
            succeeded.append((photo.name, path))
        except Exception as e:
            print(f"   ✗ FAILED: {e}", file=sys.stderr)
            failed.append((photo.name, str(e)))

    print(f"\nDone. {len(succeeded)} saved to {OUTPUT_DIR}", file=sys.stderr)
    if failed:
        print(f"{len(failed)} failed:", file=sys.stderr)
        for name, err in failed:
            print(f"  - {name}: {err}", file=sys.stderr)


def _disc_folder_photos(folder):
    """Return all photo paths in a folder, sorted with stamp.* first if present."""
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTO_EXTENSIONS)
    stamp = [p for p in paths if p.stem.lower() == "stamp"]
    others = [p for p in paths if p.stem.lower() != "stamp"]
    return stamp + others


def _read_price(folder):
    """Read price.txt from folder; if missing, prompt interactively."""
    price_file = folder / "price.txt"
    if price_file.exists():
        raw = price_file.read_text().strip().lstrip("$")
        try:
            return float(raw)
        except ValueError:
            print(f"Invalid price in {price_file}: {raw!r}", file=sys.stderr)
            sys.exit(2)
    print(f"No price.txt in {folder.name}. Enter asking price in USD.")
    raw = input("Price ($): ").strip().lstrip("$")
    try:
        return float(raw)
    except ValueError:
        print(f"Invalid price: {raw!r}", file=sys.stderr)
        sys.exit(2)


def cmd_ebay_setup(args):
    """One-time: OAuth consent + fetch business policies + create inventory location."""
    from discs.ebay import auth as ebay_auth, policies as ebay_policies

    print("Step 1/3: eBay OAuth consent (browser will open)…\n")
    state = ebay_auth.run_consent_flow()

    print("\nStep 2/3: Fetching your Business Policy IDs…")
    f_id, p_id, r_id = ebay_policies.fetch_first_policies()
    state.fulfillment_policy_id = f_id
    state.payment_policy_id = p_id
    state.return_policy_id = r_id
    state.save()
    print(f"  Fulfillment: {f_id}")
    print(f"  Payment:     {p_id}")
    print(f"  Return:      {r_id}")

    print("\nStep 3/3: Inventory location.")
    zip_code = state.zip_code or input("ZIP code to ship from: ").strip()
    if not re.fullmatch(r"\d{5}", zip_code):
        print(f"Invalid ZIP: {zip_code!r}", file=sys.stderr)
        sys.exit(2)
    state.zip_code = zip_code
    state.merchant_location_key = ebay_policies.ensure_merchant_location(zip_code)
    state.save()
    print(f"  Location key: {state.merchant_location_key} (ZIP {zip_code})")

    print("\n✓ eBay setup complete. Try: python -m discs ebay-test")


def cmd_ebay_test(args):
    """Sanity check: confirm auth works + print policy IDs."""
    from discs.ebay import auth as ebay_auth, policies as ebay_policies

    state = ebay_auth.EbayState.load()
    if not state.refresh_token:
        print("No eBay auth yet. Run: python -m discs ebay-setup", file=sys.stderr)
        sys.exit(2)

    print("Refreshing access token…")
    ebay_auth.get_access_token()
    print("✓ Access token valid.\n")

    print("Business policies:")
    all_pol = ebay_policies.list_all_policies()
    for kind in ("fulfillment", "payment", "return"):
        print(f"  {kind}:")
        for p in all_pol[kind]:
            pid_key = f"{kind}PolicyId"
            print(f"    - {p.get('name')} ({p[pid_key]})")
    print(f"\nActive: fulfillment={state.fulfillment_policy_id}  "
          f"payment={state.payment_policy_id}  return={state.return_policy_id}")
    print(f"Ships from: ZIP {state.zip_code} ({state.merchant_location_key})")


def cmd_ebay_draft(args):
    """Snap a folder of disc photos → eBay draft listing.

    Folder layout:
      <disc-folder>/
        stamp.jpg     (front, used as primary photo)
        back.jpg      (back of disc — read for back_ink)
        profile.jpg   (side profile)
        weight.jpg    (rim with weight printed)
        price.txt     (optional, just the number e.g. "25" or "$25")
    """
    if len(args) < 1:
        print("usage: python -m discs ebay-draft <disc-folder>", file=sys.stderr)
        sys.exit(2)

    folder = Path(args[0]).expanduser()
    if not folder.is_dir():
        print(f"Not a directory: {folder}", file=sys.stderr)
        sys.exit(2)

    photos = _disc_folder_photos(folder)
    if not photos:
        print(f"No photos in {folder}", file=sys.stderr)
        sys.exit(1)

    cfg = config.load()
    print(f"Identifying disc from {len(photos)} photo(s) in {folder.name}…", file=sys.stderr)
    result = generator.generate_from_images(
        [str(p) for p in photos],
        api_key=cfg["anthropic_api_key"],
    )

    _print_identification(result["extracted_disc"])
    _print_listings(result)
    _print_usage(result)

    price = _read_price(folder)
    print(f"\nAsking price: ${price:.2f}", file=sys.stderr)

    from discs.ebay import draft as ebay_draft
    print("\nPushing to eBay (draft)…", file=sys.stderr)
    out = ebay_draft.create_draft(
        result["extracted_disc"],
        result,
        [str(p) for p in photos],
        price,
    )
    print()
    print(SEP)
    print("EBAY DRAFT CREATED  (unpublished — review and publish in Seller Hub)")
    print(SEP)
    print(f"SKU:        {out['sku']}")
    print(f"Offer ID:   {out['offer_id']}")
    print(f"Drafts:     {out['seller_hub_url']}")
    _post_run(result, source_label=f"ebay-draft:{folder.name}")


COMMANDS = {
    "generate": cmd_generate,
    "photo": cmd_photo,
    "batch": cmd_batch,
    "ebay-setup": cmd_ebay_setup,
    "ebay-test": cmd_ebay_test,
    "ebay-draft": cmd_ebay_draft,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(
            f"usage: python -m discs <{'|'.join(COMMANDS)}> [args]",
            file=sys.stderr,
        )
        print("  generate            interactive prompts", file=sys.stderr)
        print("  photo <path>        identify + list from a photo", file=sys.stderr)
        print("  batch <folder>      process every photo in a folder", file=sys.stderr)
        print("  ebay-setup          one-time: OAuth + policies + location", file=sys.stderr)
        print("  ebay-test           verify eBay auth works", file=sys.stderr)
        print("  ebay-draft <folder> create an eBay draft listing from a disc folder", file=sys.stderr)
        sys.exit(2)
    COMMANDS[sys.argv[1]](sys.argv[2:])
