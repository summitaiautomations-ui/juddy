"""End-to-end: turn a folder of disc photos + price into an eBay draft listing.

Pipeline:
  1. Identify the disc + generate listing copy (Claude Opus 4.8)
  2. Upload all photos to eBay's picture service
  3. Create/update an inventory item with SKU + condition + images
  4. Create an offer (price, policies, category) — UNPUBLISHED = draft
  5. Return offer ID + seller-hub URL for the user to review and publish

Publishing is left to the user (Draft Mode v1). Once trusted, add a
--publish flag that calls POST /sell/inventory/v1/offer/{id}/publish.
"""

import re
import time
import uuid

from discs.ebay import auth, client, images, categories, policies


# Sleeve rating → eBay condition ID.
# eBay uses numeric condition IDs per category. For sporting goods discs,
# Used (3000) covers most resale; New (1000) for sleeve 10.
def _condition_id(sleeve):
    if sleeve is None:
        return "3000"
    if sleeve >= 10:
        return "1000"
    if sleeve >= 9:
        return "1500"  # New other
    if sleeve >= 7:
        return "2750"  # Like New
    return "3000"      # Used


def _sku(extracted):
    slug = re.sub(r"[^a-z0-9]+", "-", f"{extracted['mold']} {extracted.get('weight') or 'xx'}g {extracted['color']}".lower()).strip("-")
    suffix = uuid.uuid4().hex[:6]
    return f"{slug}-{suffix}"[:50]


def _aspects(extracted, brand_hint=None):
    """eBay item-specifics for the disc category."""
    aspects = {
        "Brand": [extracted["brand"]],
        "Type": [extracted["category"]],
        "Color": [extracted["color"]],
    }
    if extracted.get("weight"):
        aspects["Weight"] = [f"{extracted['weight']} g"]
    if extracted.get("plastic"):
        aspects["Material"] = [extracted["plastic"]]
    if extracted.get("mold"):
        aspects["Model"] = [extracted["mold"]]
    return aspects


def create_draft(extracted, listing, photo_paths, price_usd):
    """Create an unpublished offer. Returns dict with offer_id, sku, seller_hub_url."""
    state = auth.EbayState.load()
    if not (state.fulfillment_policy_id and state.payment_policy_id and state.return_policy_id):
        raise RuntimeError(
            "Business policies not configured. Run: python -m discs ebay-setup"
        )
    if not state.merchant_location_key:
        raise RuntimeError(
            "Merchant location not configured. Run: python -m discs ebay-setup"
        )

    print(f"  Uploading {len(photo_paths)} photo(s) to eBay…")
    image_urls = images.upload_all(photo_paths)

    sku = _sku(extracted)
    print(f"  Creating inventory item: {sku}")
    client.put(
        f"/sell/inventory/v1/inventory_item/{sku}",
        {
            "availability": {"shipToLocationAvailability": {"quantity": 1}},
            "condition": _condition_id(extracted.get("estimated_sleeve")),
            "conditionDescription": listing["ebay_description"][:1000],
            "product": {
                "title": listing["ebay_title"][:80],
                "description": listing["ebay_description"][:4000],
                "aspects": _aspects(extracted),
                "imageUrls": image_urls,
            },
        },
    )

    print("  Creating offer (draft, unpublished)…")
    offer_resp = client.post(
        "/sell/inventory/v1/offer",
        {
            "sku": sku,
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "availableQuantity": 1,
            "categoryId": categories.ebay_category_id(extracted["category"]),
            "merchantLocationKey": state.merchant_location_key,
            "pricingSummary": {
                "price": {"value": f"{float(price_usd):.2f}", "currency": "USD"},
            },
            "listingPolicies": {
                "fulfillmentPolicyId": state.fulfillment_policy_id,
                "paymentPolicyId": state.payment_policy_id,
                "returnPolicyId": state.return_policy_id,
            },
            "listingDescription": listing["ebay_description"][:500_000],
        },
    )
    offer_id = offer_resp["offerId"]

    return {
        "sku": sku,
        "offer_id": offer_id,
        "seller_hub_url": f"https://www.ebay.com/sh/lst/drafts",
        "offer_inspect_url": f"https://www.ebay.com/sh/lst/active",
    }
