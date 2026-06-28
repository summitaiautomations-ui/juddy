"""Entry: python -m discs <command> [args]."""

import sys

from discs import config, generator
from discs.disc import Disc

SEP = "=" * 72


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


def cmd_photo(args):
    """Snap-a-pic: identify the disc from a photo, then generate listings."""
    if len(args) < 1:
        print("usage: python -m discs photo <image-path>", file=sys.stderr)
        sys.exit(2)

    image_path = args[0]
    cfg = config.load()
    print(f"Identifying disc from {image_path}…", file=sys.stderr)
    result = generator.generate_from_image(image_path, api_key=cfg["anthropic_api_key"])

    extracted = result["extracted_disc"]
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
    print(f"Sleeve (1-10):   {extracted['estimated_sleeve']}  (estimated from photo)")
    print(f"Category:        {extracted['category']}")
    print(f"Notes:           {extracted['extraction_notes']}")

    _print_listings(result)
    _print_usage(result)


COMMANDS = {
    "generate": cmd_generate,
    "photo": cmd_photo,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(
            f"usage: python -m discs <{'|'.join(COMMANDS)}> [args]",
            file=sys.stderr,
        )
        print("  generate          interactive prompts", file=sys.stderr)
        print("  photo <path>      identify + list from a photo", file=sys.stderr)
        sys.exit(2)
    COMMANDS[sys.argv[1]](sys.argv[2:])
