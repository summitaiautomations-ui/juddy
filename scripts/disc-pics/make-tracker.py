#!/usr/bin/env python3
"""Build 'Disc Diver Sales Tracker.xlsx' from inventory.csv + orders.csv.

Two tabs:
  * "Orders"     -- every sold disc, with Buyer / Paid / Shipped / Tracking you
                    can tick off (Paid & Shipped are Yes/No dropdowns that turn
                    green when done). A summary up top totals your money.
  * "For Sale"   -- everything still available, so you can see what's left.

Re-run this any time the inventory or orders change. Safe to run repeatedly.
"""
import csv, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "disc-pics-data")
OUT = os.path.join(DATA, "Disc Diver Sales Tracker.xlsx")

TEAL = "0E5A66"; TEAL_D = "093C45"; SOLD_ROW = "FDECEA"
GREEN = "D6F0DC"; GREEN_T = "1E7A34"; HEADFG = "FFFFFF"
GREY = "6B7A80"
thin = Side(style="thin", color="D9DEE1")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)


def rows_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def disc_name(d):
    parts = [d["brand"],
             d["plastic"] if d["plastic"] not in ("", "unknown") else "",
             d["mold"] if d["mold"] not in ("", "unknown") else "Disc"]
    return " ".join(p for p in parts if p)


def weight(d):
    for k in ("scale_weight", "stamped_weight"):
        v = d.get(k, "")
        if v and v.replace(".", "").isdigit():
            return f"{v}g"
    return ""


def price_num(d):
    try:
        return float(d["price"])
    except (ValueError, KeyError):
        return 0.0


def style_header(ws, headers, fill, row):
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=c, value=h)
        cell.font = Font(bold=True, color=HEADFG, size=11)
        cell.fill = PatternFill("solid", fgColor=fill)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER


def main():
    inv = {d["id"]: d for d in rows_csv("inventory.csv")}
    orders = {o["id"]: o for o in rows_csv("orders.csv")}

    wb = Workbook()

    # ---------- Orders tab ----------
    ws = wb.active
    ws.title = "Orders"
    ws.sheet_view.showGridLines = False

    ws.cell(1, 1, "DISC DIVER — SALES TRACKER").font = Font(
        bold=True, size=16, color=TEAL_D)
    summ_row = 2   # summary line filled in once totals are known

    headers = ["#", "Disc", "Color", "Weight", "Price", "Buyer",
               "Paid?", "Shipped?", "Tracking #", "Sold Date", "Notes"]
    head_row = 4
    style_header(ws, headers, TEAL, head_row)
    ws.freeze_panes = ws.cell(row=head_row + 1, column=1)

    sold_ids = [i for i, d in inv.items() if d["status"] in ("sold", "claimed")]
    # include any order id even if inventory dropped it
    for i in orders:
        if i not in sold_ids:
            sold_ids.append(i)
    sold_ids.sort()

    total = collected = to_ship = 0.0
    r = head_row
    for i in sold_ids:
        r += 1
        d = inv.get(i, {})
        o = orders.get(i, {})
        # off-website sales carry their own description + amount in the order
        amt = (o.get("amount", "") or "").strip()
        p = float(amt) if amt else price_num(d)
        name = (o.get("desc", "") or "").strip() or (
            disc_name(d) if d else "(disc " + i + ")")
        total += p
        paid = (o.get("paid", "no") or "no").lower() == "yes"
        shipped = (o.get("shipped", "no") or "no").lower() == "yes"
        if paid:
            collected += p
        if not shipped:
            to_ship += 1
        vals = [
            "#" + i,
            name,
            d.get("color", ""),
            weight(d),
            p,
            o.get("buyer", ""),
            "Yes" if paid else "No",
            "Yes" if shipped else "No",
            o.get("tracking", ""),
            o.get("sold_date", ""),
            o.get("order_notes", ""),
        ]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(r, c, v)
            cell.border = BORDER
            cell.alignment = Alignment(
                horizontal="center" if c in (1, 4, 5, 7, 8) else "left",
                vertical="center")
        ws.cell(r, 5).number_format = '"$"#,##0'

    last = r

    # Yes/No dropdowns for Paid? (G) and Shipped? (H)
    dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(f"G{head_row+1}:H{last}")

    # green when "Yes"
    green_fill = PatternFill("solid", fgColor=GREEN)
    green_font = Font(color=GREEN_T, bold=True)
    for col in ("G", "H"):
        ws.conditional_formatting.add(
            f"{col}{head_row+1}:{col}{last}",
            CellIsRule(operator="equal", formula=['"Yes"'],
                       fill=green_fill, font=green_font))

    # summary line
    s = ws.cell(summ_row, 1)
    s.value = (f"{len(sold_ids)} sold  •  "
               f"${total:,.0f} total  •  "
               f"${collected:,.0f} collected  •  "
               f"{int(to_ship)} still to ship")
    s.font = Font(bold=True, size=12, color=GREY)

    widths = [7, 30, 14, 9, 8, 18, 9, 10, 20, 12, 30]
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(c)].width = w

    # ---------- For Sale tab ----------
    ws2 = wb.create_sheet("For Sale")
    ws2.sheet_view.showGridLines = False
    ws2.cell(1, 1, "STILL AVAILABLE").font = Font(bold=True, size=16, color=TEAL_D)
    avail = sorted([d for d in inv.values() if d["status"] == "available"],
                   key=lambda d: d["id"])
    ws2.cell(2, 1, f"{len(avail)} discs available  •  "
             f"${sum(price_num(d) for d in avail):,.0f} listed").font = Font(
        bold=True, size=12, color=GREY)
    h2 = ["#", "Disc", "Color", "Weight", "Price", "Notes"]
    hr2 = 4
    style_header(ws2, h2, TEAL_D, hr2)
    ws2.freeze_panes = ws2.cell(row=hr2 + 1, column=1)
    r = hr2
    for d in avail:
        r += 1
        vals = ["#" + d["id"], disc_name(d), d["color"], weight(d),
                price_num(d), d.get("notes", "")]
        for c, v in enumerate(vals, 1):
            cell = ws2.cell(r, c, v)
            cell.border = BORDER
            cell.alignment = Alignment(
                horizontal="center" if c in (1, 4, 5) else "left",
                vertical="center")
        ws2.cell(r, 5).number_format = '"$"#,##0'
    for c, w in enumerate([7, 30, 16, 9, 8, 50], 1):
        ws2.column_dimensions[get_column_letter(c)].width = w

    wb.save(OUT)
    print(f"Wrote {OUT}")
    print(f"  {len(sold_ids)} orders, ${total:,.0f} total, "
          f"${collected:,.0f} collected, {int(to_ship)} to ship")


if __name__ == "__main__":
    main()
