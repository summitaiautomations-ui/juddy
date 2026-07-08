#!/usr/bin/env python3
"""Fold every disc staged in disc-pics-data/incoming/ into the spreadsheet.

This is the ONE place disc ids are assigned and the CSVs are written, so it
never collides with the mini (which only ever adds files under incoming/).
For each sidecar it: assigns the next id, best-effort background-cleans the
photo, files it as photos/NNN-slug.jpg, appends rows to inventory.csv and
sheet.csv, and removes the incoming files.

Usage:
  ./merge-incoming.py            # clean photos if OpenCV is available
  RAW_CLEAN=0 ./merge-incoming.py  # skip cleaning, file photos as-is
"""

import csv
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DATA = REPO_ROOT / "disc-pics-data"
INCOMING = DATA / "incoming"
PHOTOS = DATA / "photos"
INVENTORY = DATA / "inventory.csv"
SHEET = DATA / "sheet.csv"
CLEANER = SCRIPT_DIR / "clean-photo.py"

INV_HEADER = ["id", "date", "photo", "mold", "brand", "plastic", "color",
              "stamped_weight", "scale_weight", "condition", "price", "status", "notes"]
SHEET_HEADER = ["photo_url", "id", "mold", "brand", "plastic", "color",
                "stamped_weight_g", "scale_weight_g", "condition", "price_usd", "status", "notes"]


def raw_base():
    remote = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "remote", "get-url", "origin"], text=True).strip()
    remote = re.sub(r"\.git$", "", remote).replace(":", "/")
    owner_repo = "/".join(remote.split("/")[-2:])
    branch = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    return f"https://raw.githubusercontent.com/{owner_repo}/{branch}/disc-pics-data/photos"


def read_sidecar(path):
    d = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def next_id():
    if not INVENTORY.exists():
        return 1
    with INVENTORY.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    mx = 0
    for r in rows[1:]:
        try:
            mx = max(mx, int(r[0]))
        except (ValueError, IndexError):
            pass
    return mx + 1


def ensure_headers():
    if not INVENTORY.exists():
        with INVENTORY.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f, quoting=csv.QUOTE_NONNUMERIC).writerow(INV_HEADER)
    if not SHEET.exists():
        with SHEET.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f, quoting=csv.QUOTE_NONNUMERIC).writerow(SHEET_HEADER)


def clean_or_copy(src, dst):
    """Background-clean src -> dst if the cleaner + OpenCV work; else copy raw."""
    if os.environ.get("RAW_CLEAN") == "0":
        dst.write_bytes(src.read_bytes())
        return "copied"
    try:
        subprocess.run([sys.executable, str(CLEANER), str(src), str(dst)],
                       check=True, capture_output=True, text=True)
        return "cleaned"
    except Exception:
        dst.write_bytes(src.read_bytes())
        return "copied (cleaner unavailable)"


def main():
    sidecars = sorted(INCOMING.glob("*.sidecar")) if INCOMING.exists() else []
    if not sidecars:
        print("==> nothing in incoming/ -- nothing to merge")
        return

    ensure_headers()
    PHOTOS.mkdir(parents=True, exist_ok=True)
    base = raw_base()
    nid = next_id()

    inv_rows, sheet_rows = [], []
    for sc in sidecars:
        meta = read_sidecar(sc)
        parts = meta.get("identify", "").split("|")
        if len(parts) != 8:
            print(f"    skipping malformed sidecar: {sc.name}", file=sys.stderr)
            continue
        mold, brand, plastic, color, stamped, condition, price, notes = [p.strip() for p in parts]
        src_photo = INCOMING / meta.get("photo", "")
        if not src_photo.exists():
            print(f"    photo missing for {sc.name}, skipping", file=sys.stderr)
            continue

        did = f"{nid:03d}"
        slug = re.sub(r"[^a-z0-9]+", "-", mold.lower()).strip("-") or "disc"
        ext = src_photo.suffix.lstrip(".") or "jpg"
        fname = f"{did}-{slug}.{ext}"
        how = clean_or_copy(src_photo, PHOTOS / fname)

        inv_rows.append([did, meta.get("date", ""), fname, mold, brand, plastic, color,
                         stamped, "unknown", condition, price, "available", notes])
        sheet_rows.append([f"{base}/{fname}", did, mold, brand, plastic, color,
                           stamped, "unknown", condition, price, "available", notes])
        print(f"    {did}: {brand} {mold} ({plastic}, {color}) ~${price}  [{how}]")

        src_photo.unlink()
        sc.unlink()
        nid += 1

    if not inv_rows:
        print("==> no valid discs merged")
        return

    with INVENTORY.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f, quoting=csv.QUOTE_NONNUMERIC).writerows(inv_rows)
    with SHEET.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f, quoting=csv.QUOTE_NONNUMERIC).writerows(sheet_rows)

    # Clean up an empty incoming dir so it doesn't linger in git status.
    leftover = list(INCOMING.iterdir()) if INCOMING.exists() else []
    print(f"\n==> merged {len(inv_rows)} disc(s); "
          f"{len(leftover)} file(s) still in incoming/")


if __name__ == "__main__":
    main()
