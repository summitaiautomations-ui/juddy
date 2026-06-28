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


COMMANDS = {
    "generate": cmd_generate,
    "photo": cmd_photo,
    "batch": cmd_batch,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(
            f"usage: python -m discs <{'|'.join(COMMANDS)}> [args]",
            file=sys.stderr,
        )
        print("  generate          interactive prompts", file=sys.stderr)
        print("  photo <path>      identify + list from a photo", file=sys.stderr)
        print("  batch <folder>    process every photo in a folder", file=sys.stderr)
        sys.exit(2)
    COMMANDS[sys.argv[1]](sys.argv[2:])
