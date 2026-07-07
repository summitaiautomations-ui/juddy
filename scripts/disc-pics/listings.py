#!/usr/bin/env python3
"""Generate listing files for every cataloged disc that has a photo:

  disc-pics-data/listings/shopify-products.csv  (Shopify: Products > Import)
  disc-pics-data/listings/ebay-listings.csv     (eBay Seller Hub: bulk upload / File Exchange)
  disc-pics-data/listings/listings.md           (human-readable, copy-paste fallback)

Runs automatically after each catalog pass (see auto-catalog.sh), or by hand:

  ./listings.py
"""

import csv
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "disc-pics-data"
OUT_DIR = DATA_DIR / "listings"

# Verify in Seller Hub that this is the current Disc Golf category ID.
EBAY_CATEGORY = os.environ.get("EBAY_CATEGORY", "79807")
EBAY_LOCATION = os.environ.get("EBAY_LOCATION", "USA")
SHIP_COST = os.environ.get("SHIP_COST", "5.00")


def load_discs():
    with (DATA_DIR / "sheet.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = [h.strip().lower() for h in rows[0]]
    fields = ["photo_url", "id", "mold", "brand", "plastic", "color",
              "stamped_weight_g", "scale_weight_g", "condition", "price_usd", "status", "notes"]
    try:
        idx = {name: header.index(name) for name in fields}
    except ValueError as e:
        sys.exit(f"error: sheet.csv header is missing a column: {e}")

    keys = {"stamped_weight_g": "stamped", "scale_weight_g": "scale", "price_usd": "price"}
    discs = []
    for row in rows[1:]:
        if len(row) <= idx["notes"] or not row[idx["id"]].strip():
            continue
        d = {keys.get(name, name): row[i].strip() for name, i in idx.items()}
        # Scale weight is the truth; stamped weight is the fallback
        d["weight"] = d["scale"] if d["scale"].isdigit() else d["stamped"]
        # Only list discs that are still for sale and have a photo
        if d["photo_url"] and d["status"].lower() in ("", "available"):
            discs.append(d)
    return discs


def title(d):
    parts = [d["brand"], d["plastic"] if d["plastic"] != "unknown" else "", d["mold"]]
    t = " ".join(p for p in parts if p)
    extras = []
    if d["weight"] and d["weight"].isdigit():
        extras.append(f'{d["weight"]}g')
    if d["condition"] and d["condition"] != "unknown":
        extras.append(f'{d["condition"]}/10')
    if d["color"] and d["color"] != "unknown":
        extras.append(d["color"].capitalize())
    return f"{t} Disc Golf Disc" + (f' - {" ".join(extras)}' if extras else "")


def description(d):
    lines = [
        f'{d["brand"]} {d["mold"]}' + (f' in {d["plastic"]} plastic' if d["plastic"] != "unknown" else ""),
        f'Color: {d["color"]}',
    ]
    if d["weight"].isdigit():
        suffix = " (on scale)" if d["scale"].isdigit() else " (stamped)"
        lines.append(f'Weight: {d["weight"]}g{suffix}')
    if d["condition"] != "unknown":
        lines.append(f'Condition: {d["condition"]}/10 (Sleepy Scale)')
    if d["notes"]:
        lines.append(d["notes"])
    lines.append("From a smoke-free home. Photo is of the actual disc.")
    return lines


def write_shopify(discs):
    headers = [
        "Handle", "Title", "Body (HTML)", "Vendor", "Type", "Tags", "Published",
        "Option1 Name", "Option1 Value", "Variant SKU", "Variant Grams",
        "Variant Inventory Tracker", "Variant Inventory Qty", "Variant Inventory Policy",
        "Variant Fulfillment Service", "Variant Price", "Variant Requires Shipping",
        "Variant Taxable", "Image Src", "Status",
    ]
    path = OUT_DIR / "shopify-products.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for d in discs:
            body = "<br>".join(description(d))
            grams = d["weight"] if d["weight"].isdigit() else ""
            w.writerow([
                f'disc-{d["id"]}', title(d), body, d["brand"], "Disc Golf Disc",
                "disc golf,used disc", "TRUE",
                "Title", "Default Title", f'DISC-{d["id"]}', grams,
                "shopify", "1", "deny",
                "manual", d["price"], "TRUE",
                "TRUE", d["photo_url"], "active",
            ])
    return path


def write_ebay(discs):
    headers = [
        "*Action(SiteID=US|Country=US|Currency=USD|Version=1193)",
        "CustomLabel", "*Category", "*Title", "Description", "*ConditionID",
        "PicURL", "*Format", "*Duration", "*StartPrice", "*Quantity",
        "*Location", "ShippingType", "ShippingService-1:Option",
        "ShippingService-1:Cost", "*DispatchTimeMax", "*ReturnsAcceptedOption",
    ]
    path = OUT_DIR / "ebay-listings.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for d in discs:
            cond = d["condition"]
            condition_id = "1000" if cond.isdigit() and int(cond) >= 10 else "3000"
            w.writerow([
                "Add", f'DISC-{d["id"]}', EBAY_CATEGORY, title(d)[:80],
                "<br>".join(description(d)), condition_id,
                d["photo_url"], "FixedPrice", "GTC", d["price"], "1",
                EBAY_LOCATION, "Flat", "USPSGroundAdvantage",
                SHIP_COST, "2", "ReturnsNotAccepted",
            ])
    return path


def write_markdown(discs):
    path = OUT_DIR / "listings.md"
    with path.open("w", encoding="utf-8") as f:
        f.write("# Disc listings\n\n")
        for d in discs:
            f.write(f'## {d["id"]}: {title(d)} — ${d["price"]}\n\n')
            f.write(f'![disc {d["id"]}]({d["photo_url"]})\n\n')
            for line in description(d):
                f.write(f"- {line}\n")
            f.write("\n")
    return path


def main():
    discs = load_discs()
    if not discs:
        print("==> no discs with photos yet -- nothing to generate")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (write_shopify(discs), write_ebay(discs), write_markdown(discs)):
        print(f"==> wrote {path.relative_to(REPO_ROOT)}")
    print(f"==> {len(discs)} disc(s) ready to list")


if __name__ == "__main__":
    main()
