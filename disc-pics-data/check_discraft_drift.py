import csv

srows = list(csv.reader(open('/Users/juddy/juddy/disc-pics-data/sheet.csv')))
shdr, sbody = srows[0], srows[1:]
sidi, ssi, sbi = shdr.index('id'), shdr.index('status'), shdr.index('brand')
sstatus = {r[sidi]: (r[ssi].lower(), r[sbi]) for r in sbody}

irows = list(csv.reader(open('/Users/juddy/juddy/disc-pics-data/inventory.csv')))
ihdr, ibody = irows[0], irows[1:]
iidi, isi, ibi = ihdr.index('id'), ihdr.index('status'), ihdr.index('brand')

drift = []
for r in ibody:
    id_ = r[iidi]
    istatus = r[isi].lower()
    sstat, sbrand = sstatus.get(id_, (None, None))
    if sstat is not None and sstat != istatus and (r[ibi] == 'Discraft' or sbrand == 'Discraft'):
        drift.append((id_, sbrand or r[ibi], sstat, istatus))

print(f"{len(drift)} Discraft discs with sheet/inventory status drift:")
for d in drift:
    print(d)
