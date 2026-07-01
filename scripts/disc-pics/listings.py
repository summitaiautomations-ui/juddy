#!/usr/bin/env python3
"""Extract son-approved discs from the shared Google Sheet and generate
listing files ready to import:

  disc-pics-data/listings/shopify-products.csv  (Shopify: Products > Import)
  disc-pics-data/listings/ebay-listings.csv     (eBay Seller Hub: bulk upload / File Exchange)
  disc-pics-data/listings/listings.md           (human-readable, copy-paste fallback)

Approval flow: the Google Sheet imports sheet.csv into columns B:L; your son
marks approvals in column M (yes/x/ok/true, case-insensitive). Publish that
tab as CSV (File > Share > Publish to web > that tab > CSV) and pass the URL:

  APPROVALS_URL="https://docs.google.com/...output=csv" ./listings.py

With no APPROVALS_URL it falls back to the local sheet.csv and treats every
disc with a photo as approved (useful for testing).
"""

import csv
import io
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "disc-pics-data"
OUT_DIR = DATA_DIR / "listings"

# Verify in Seller Hub that this is the current Disc Golf category ID.
EBAY_CATEGORY = os.environ.get("EBAY_CATEGORY", "79807")
EBAY_LOCATION = os.environ.get("EBAY_LOCATION", "USA")
SHIP_COST = os.environ.get("SHIP_COST", "5.00")

APPROVED = re.compile(r"^(yes|y|x|ok|true|approved|✓)$", re.IGNORECASE)


def fetch_rows():
    url = os.environ.get("APPROVALS_URL", "")
    if url:
        with urllib.request.urlopen(url, timeout=30) as resp:
            text = resp.read().decode("utf-8")
    else:
        text = (DATA_DIR / "sheet.csv").read_text(encoding="utf-8")
    return list(csv.reader(io.StringIO(text)))


def approved_discs(rows):
    header = [h.strip().lower() for h in rows[0]]

    def col(name, default=None):
        return header.index(name) if name in header else default

    # The Google Sheet has a "Pic" IMAGE column at A; the published CSV
    # therefore has photo_url shifted right by one. Find columns by name.
    idx = {
        "photo_url": col("photo_url"),
        "id": col("id"),
        "mold": col("mold"),
        "brand": col("brand"),
        "plastic": col("plastic"),
        "color": col("color"),
        "weight": col("weight_g"),
        "condition": col("condition"),
        "price": col("price_usd"),
        "notes": col("notes"),
    }
    missing = [k for k, v in idx.items() if v is None]
    if missing:
        sys.exit(f"error: could not find columns {missing} in the sheet header: {rows[0]}")

    approve_col = col("approved")
    using_fallback = "APPROVALS_URL" not in os.environ

    discs = []
    for row in rows[1:]:
        if len(row) <= idx["notes"] or not row[idx["id"]].strip():
            continue
        if using_fallback:
            ok = bool(row[idx["photo_url"]].strip())
        elif approve_col is not None and len(row) > approve_col:
            ok = bool(APPROVED.match(row[approve_col].strip()))
        else:
            # No "Approved" header: treat the first cell past the notes column as the mark.
            extra = row[idx["notes"] + 1] if len(row) > idx["notes"] + 1 else ""
            ok = bool(APPROVED.match(extra.strip()))
        if ok:
            discs.append({k: row[v].strip() for k, v in idx.items()})
    return discs


def title(d):
    parts = [d["brand"], d["plastic"] if d["plastic"] != "unknown" else "", d["mold"]]
    t = " ".join(p for p in parts if p)
    extras = []
    if d["weight"] and d["weight"] != "unknown":
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
    if d["weight"] != "unknown":
        lines.append(f'Weight: {d["weight"]}g')
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
        f.write("# Approved disc listings\n\n")
        for d in discs:
            f.write(f'## {d["id"]}: {title(d)} — ${d["price"]}\n\n')
            if d["photo_url"]:
                f.write(f'![disc {d["id"]}]({d["photo_url"]})\n\n')
            for line in description(d):
                f.write(f"- {line}\n")
            f.write("\n")
    return path


def main():
    rows = fetch_rows()
    discs = approved_discs(rows)
    if not discs:
        print("==> no approved discs found -- nothing to generate")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (write_shopify(discs), write_ebay(discs), write_markdown(discs)):
        print(f"==> wrote {path.relative_to(REPO_ROOT)}")
    print(f"==> {len(discs)} approved disc(s) ready to list")


if __name__ == "__main__":
    main()
