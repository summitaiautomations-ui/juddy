"""Entry: python -m discs <command>."""

import sys

from discs import config, generator
from discs.disc import Disc


def _input_int(prompt):
    raw = input(prompt).strip()
    return int(raw) if raw else None


def cmd_generate():
    """Prompt for disc details, generate listings, print to stdout."""
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

    sep = "=" * 72
    print()
    print(sep)
    print("eBay TITLE")
    print(sep)
    title = result["ebay_title"]
    print(title)
    print(f"(length: {len(title)} / 80)")

    print()
    print(sep)
    print("eBay DESCRIPTION")
    print(sep)
    print(result["ebay_description"])

    print()
    print(sep)
    print("BST POST  (Reddit r/discexchange · DGCR BST · Marketplace Disc Golf app)")
    print(sep)
    print(result["bst_post"])

    print()
    print(sep)
    print("eBay CATEGORY")
    print(sep)
    print(result["suggested_ebay_category"])

    print()
    print(sep)
    print("COMP PRICING — paste into eBay → Advanced → Sold listings")
    print(sep)
    print(result["comp_pricing_search_query"])

    usage = result.get("_usage", {})
    print()
    print(
        f"(tokens in={usage.get('input_tokens', '?')} "
        f"out={usage.get('output_tokens', '?')} "
        f"cache_read={usage.get('cache_read_input_tokens', 0)})"
    )


COMMANDS = {
    "generate": cmd_generate,
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: python -m discs <{'|'.join(COMMANDS)}>", file=sys.stderr)
        sys.exit(2)
    COMMANDS[sys.argv[1]]()
