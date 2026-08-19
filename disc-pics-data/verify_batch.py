import csv

check_ids = ['115', '214', '349', '23', '424', '425', '426']

rows = list(csv.reader(open('/Users/juddy/juddy/disc-pics-data/sheet.csv')))
hdr, body = rows[0], rows[1:]
idi = hdr.index('id')
si = hdr.index('status')
mi = hdr.index('mold')
bi = hdr.index('brand')
pi = hdr.index('plastic')
ci = hdr.index('color')
condi = hdr.index('condition')
pricei = hdr.index('price_usd')
noti = hdr.index('notes')
photoi = 0

sheet_map = {r[idi]: r for r in body}

irows = list(csv.reader(open('/Users/juddy/juddy/disc-pics-data/inventory.csv')))
ihdr, ibody = irows[0], irows[1:]
iidi, isi = ihdr.index('id'), ihdr.index('status')
inv_map = {r[iidi]: r[isi] for r in ibody}

print(f"{'ID':<5} {'Status':<10} {'Sheet==Inv?':<12} {'Photo?':<8} {'Flight?':<9} {'Mold/Brand':<25} {'Price'}")
print("-"*90)
for cid in check_ids:
    r = sheet_map.get(cid)
    if not r:
        print(f"{cid:<5} MISSING FROM SHEET")
        continue
    status = r[si]
    inv_status = inv_map.get(cid, 'MISSING')
    sync = "YES" if inv_status == status else f"NO ({inv_status})"
    has_photo = "YES" if r[photoi].strip() else "NO"
    has_flight = "YES" if "flight" in r[noti].lower() else "NO (n/a for putters/unstamped)"
    mold_brand = f"{r[bi]} {r[mi]}"
    print(f"{cid:<5} {status:<10} {sync:<12} {has_photo:<8} {has_flight:<9} {mold_brand:<25} ${r[pricei]}")
