import csv

# every ID that appeared on a printed label sheet today
labeled_ids = [
    44,83,88,100,104,113,123,126,131,171,183,184,189,219,223,246,
    263,269,304,307,331,347,354,
    356,358,359,360,361,362,363,364,365,366,367,368,369,
    370,371,372,373,374,375,376,377,378,379,
    380,381,382,383,384,385,386,387,388,389,390,391,392,393,394,395,
    396,397,398,399,400,401,402,403,404,405,406,407,408,
    409,410,411,412,413,414,415,416,417,418,419,420,421,422,423
]
labeled_ids = [str(i) for i in labeled_ids]

rows = list(csv.reader(open('/Users/juddy/juddy/disc-pics-data/sheet.csv')))
hdr, body = rows[0], rows[1:]
idi, si, mi = hdr.index('id'), hdr.index('status'), hdr.index('mold')

status_map = {r[idi]: (r[si], r[mi]) for r in body}

not_available = []
missing = []
for lid in labeled_ids:
    if lid not in status_map:
        missing.append(lid)
    elif status_map[lid][0].lower() != 'available':
        not_available.append((lid, status_map[lid][0], status_map[lid][1]))

print(f"Checked {len(labeled_ids)} labeled discs")
print(f"NOT available ({len(not_available)}):", not_available)
print(f"MISSING from sheet ({len(missing)}):", missing)
