"""Map our disc categories to eBay leaf category IDs (US marketplace).

Verified against the live eBay category tree (Sporting Goods → Outdoor
Sports & Recreation → Disc Golf → Discs). Update if eBay reshuffles.
"""

CATEGORY_IDS = {
    "Putter": "20867",            # Putters
    "Approach": "20867",          # Approach discs → Putters (no separate leaf)
    "Midrange": "20868",          # Midrange Drivers
    "Fairway Driver": "20869",    # Fairway Drivers
    "Distance Driver": "36278",   # Distance Drivers
    "Specialty": "36280",         # Other / Specialty Discs
}

DEFAULT_CATEGORY = "20865"  # parent "Discs" leaf (fallback)


def ebay_category_id(disc_category):
    return CATEGORY_IDS.get(disc_category, DEFAULT_CATEGORY)
