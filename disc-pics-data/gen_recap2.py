import os

discs = [
    {"lot":"83",  "mold":"Ace Race '12",     "plastic":"—",       "color":"Red",                  "cond":"8.5", "wt":"176g", "price":"$7",  "img":"083-acerace.jpg"},
    {"lot":"100", "mold":"Zone OS",           "plastic":"—",       "color":"Confetti (AIRBORN)",   "cond":"9",   "wt":"177g", "price":"$7",  "img":"100-zoneos.jpg"},
    {"lot":"113", "mold":"Nuke",              "plastic":"—",       "color":"Blue",                 "cond":"9",   "wt":"167g", "price":"$7",  "img":"113-nuke.jpg"},
    {"lot":"126", "mold":"Fierce",            "plastic":"Big Z",   "color":"Gray",                 "cond":"9",   "wt":"—",    "price":"$14", "img":"126-fierce.jpg"},
    {"lot":"131", "mold":"Luna",              "plastic":"Big Z",   "color":"Blue Translucent",     "cond":"9.5", "wt":"173g", "price":"$15", "img":"131-luna.jpg"},
    {"lot":"171", "mold":"Challenger SS",     "plastic":"—",       "color":"Light Blue",           "cond":"7",   "wt":"173g", "price":"$8",  "img":"171-putter.jpg"},
    {"lot":"183", "mold":"Zeus",              "plastic":"—",       "color":"Green",                "cond":"9",   "wt":"175g", "price":"$11", "img":"183-zeus.jpg"},
    {"lot":"184", "mold":"Buzzz",             "plastic":"—",       "color":"Blue",                 "cond":"9",   "wt":"179g", "price":"$12", "img":"184-buzzz-brp.jpg"},
    {"lot":"189", "mold":"Flick",             "plastic":"ESP",     "color":"Pink",                 "cond":"8",   "wt":"159g", "price":"$10", "img":"189-flick.jpg"},
    {"lot":"219", "mold":"Hades",             "plastic":"ESP",     "color":"Purple",               "cond":"9",   "wt":"176g", "price":"$11", "img":"219-hades.jpg"},
    {"lot":"223", "mold":"Challenger",        "plastic":"Soft",    "color":"Red",                  "cond":"7",   "wt":"175g", "price":"$6",  "img":"223-challenger.jpg"},
    {"lot":"246", "mold":"Thrasher",          "plastic":"—",       "color":"Pink/Rose Swirl",      "cond":"7",   "wt":"173g", "price":"$8",  "img":"246-thrasher.jpg"},
    {"lot":"269", "mold":"Impact",            "plastic":"Z Swirl", "color":"Yellow",               "cond":"8.5", "wt":"178g", "price":"$13", "img":"269-impact.jpg"},
]

discs2 = [
    {"lot":"304", "mold":"Malta",             "plastic":"Z Lite",  "color":"Green",                "cond":"9",   "wt":"—",    "price":"$10", "img":"304-malta.jpg"},
    {"lot":"307", "mold":"Hades",             "plastic":"—",       "color":"Gray/Olive",           "cond":"9",   "wt":"173g", "price":"$10", "img":"307-hades.jpg"},
    {"lot":"370", "mold":"Drone",             "plastic":"—",       "color":"Confetti",             "cond":"8.5", "wt":"177g", "price":"$8",  "img":"370-drone.jpg"},
    {"lot":"371", "mold":"Captain's Raptor",  "plastic":"Z FLX",   "color":"Clear/Confetti Swirl", "cond":"8.5", "wt":"177g", "price":"$10", "img":"371-captainsraptor.jpg"},
    {"lot":"372", "mold":"Raptor",            "plastic":"Z",       "color":"Clear/Teal",           "cond":"8.5", "wt":"176g", "price":"$9",  "img":"372-raptor.jpg"},
    {"lot":"373", "mold":"Nuke SS",           "plastic":"ESP FLX", "color":"Red/Orange Swirl",     "cond":"8.5", "wt":"171g", "price":"$9",  "img":"373-nukess.jpg"},
    {"lot":"374", "mold":"Nuke OS",           "plastic":"Z",       "color":"Yellow Translucent",   "cond":"9",   "wt":"177g", "price":"$9",  "img":"374-nukeos.jpg"},
    {"lot":"375", "mold":"Nuke SS",           "plastic":"ESP",     "color":"Pink/Purple Tie-dye",  "cond":"8.5", "wt":"171g", "price":"$9",  "img":"375-nukess.jpg"},
    {"lot":"376", "mold":"Flick",             "plastic":"Z",       "color":"Yellow/Orange",        "cond":"8.5", "wt":"166g", "price":"$11", "img":"376-flick.jpg"},
    {"lot":"377", "mold":"Luna",              "plastic":"—",       "color":"Gray",                 "cond":"8.5", "wt":"174g", "price":"$12", "img":"377-luna.jpg"},
    {"lot":"378", "mold":"McBeth Prototype",  "plastic":"—",       "color":"Purple",               "cond":"8.5", "wt":"174g", "price":"$18", "img":"378-mcbethprototype.jpg"},
    {"lot":"379", "mold":"Nuke",              "plastic":"—",       "color":"Orange (worn)",        "cond":"8.5", "wt":"177g", "price":"$8",  "img":"379-nuke.jpg"},
]

PHOTO_DIR = "/Users/juddy/juddy/disc-pics-data/photos"

def card_html(d):
    plastic_line = f'{d["plastic"]} &middot; ' if d["plastic"] != "—" else ""
    img_path = os.path.join(PHOTO_DIR, d["img"])
    return f'''<div class="card">
  <img class="thumb" src="file://{img_path}">
  <div class="info">
    <div class="lot">LOT #{d["lot"]}</div>
    <div class="brand">DISCRAFT &mdash; {d["mold"]}</div>
    <div class="detail">{plastic_line}{d["color"]}</div>
    <div class="stats">Cond: {d["cond"]}/10 &nbsp;&middot;&nbsp; Wt: {d["wt"]}</div>
    <div class="price">{d["price"]}</div>
  </div>
</div>'''

def build_page(disc_list, title, page_num, total_pages, count_total):
    cards_html = "\n".join(card_html(d) for d in disc_list)
    return f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #0e2129;
    padding: 36px;
  }}
  h1 {{
    color: #eafcfb;
    font-size: 34px;
    margin: 0 0 4px;
  }}
  .sub {{
    color: #9fc0c2;
    font-size: 17px;
    margin: 0 0 26px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
  }}
  .card {{
    background: #14313b;
    border: 1px solid #1d3b44;
    border-radius: 14px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }}
  .thumb {{
    width: 100%;
    height: 320px;
    object-fit: contain;
    background: #eef0f2;
    display: block;
    image-rendering: -webkit-optimize-contrast;
  }}
  .info {{ padding: 14px 16px 16px; }}
  .lot {{
    font-size: 16px;
    font-weight: 800;
    color: #3ad6d6;
    letter-spacing: 0.03em;
  }}
  .brand {{
    font-size: 16px;
    font-weight: 700;
    color: #eafcfb;
    margin-top: 3px;
  }}
  .detail {{
    font-size: 14px;
    color: #9fc0c2;
    margin-top: 3px;
  }}
  .stats {{
    font-size: 13px;
    color: #9fc0c2;
    margin-top: 7px;
  }}
  .price {{
    font-size: 24px;
    font-weight: 800;
    color: #3ad6d6;
    margin-top: 5px;
  }}
</style>
</head>
<body>
  <h1>Disc Diver — Discraft Inventory</h1>
  <div class="sub">{count_total} Discraft discs sorted out today &middot; all live on discdiver.com &middot; page {page_num} of {total_pages}</div>
  <div class="grid">
{cards_html}
  </div>
</body>
</html>'''

with open('/Users/juddy/juddy/disc-pics-data/recap-page1.html', 'w') as f:
    f.write(build_page(discs, "page1", 1, 2, 25))

with open('/Users/juddy/juddy/disc-pics-data/recap-page2.html', 'w') as f:
    f.write(build_page(discs2, "page2", 2, 2, 25))

print("Built 2 pages:", len(discs), "+", len(discs2), "=", len(discs)+len(discs2))
