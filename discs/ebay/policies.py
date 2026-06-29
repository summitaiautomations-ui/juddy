"""Fetch the user's eBay Business Policies (one-time per setup).

Each listing needs a fulfillment / payment / return policy ID. We grab
the first of each from the user's account and stash them in state. They
can override by editing discs/.ebay_state.json by hand.
"""

from discs.ebay import auth, client
from discs.ebay.client import EbayApiError


def fetch_first_policies():
    """Returns (fulfillment_id, payment_id, return_id). Raises if any missing."""
    fulfillment = client.get("/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_US")
    payment = client.get("/sell/account/v1/payment_policy?marketplace_id=EBAY_US")
    returns = client.get("/sell/account/v1/return_policy?marketplace_id=EBAY_US")

    f_policies = fulfillment.get("fulfillmentPolicies", [])
    p_policies = payment.get("paymentPolicies", [])
    r_policies = returns.get("returnPolicies", [])

    if not f_policies:
        raise RuntimeError("No fulfillment (shipping) policies on your eBay account. Create one in Seller Hub → Account → Business Policies.")
    if not p_policies:
        raise RuntimeError("No payment policies on your eBay account.")
    if not r_policies:
        raise RuntimeError("No return policies on your eBay account.")

    return (
        f_policies[0]["fulfillmentPolicyId"],
        p_policies[0]["paymentPolicyId"],
        r_policies[0]["returnPolicyId"],
    )


def list_all_policies():
    """For interactive display during setup. Returns dict with all three lists."""
    return {
        "fulfillment": client.get("/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_US").get("fulfillmentPolicies", []),
        "payment": client.get("/sell/account/v1/payment_policy?marketplace_id=EBAY_US").get("paymentPolicies", []),
        "return": client.get("/sell/account/v1/return_policy?marketplace_id=EBAY_US").get("returnPolicies", []),
    }


MERCHANT_LOCATION_KEY = "default-disc-location"


def ensure_merchant_location(zip_code):
    """Create a default inventory location if one doesn't exist. Idempotent."""
    try:
        client.get(f"/sell/inventory/v1/location/{MERCHANT_LOCATION_KEY}")
        return MERCHANT_LOCATION_KEY  # already exists
    except EbayApiError as e:
        if e.status != 404:
            raise

    client.post(
        f"/sell/inventory/v1/location/{MERCHANT_LOCATION_KEY}",
        {
            "location": {
                "address": {
                    "country": "US",
                    "postalCode": zip_code,
                }
            },
            "locationInstructions": "Ships from home office.",
            "name": "Default Disc Shipping Location",
            "merchantLocationStatus": "ENABLED",
            "locationTypes": ["WAREHOUSE"],
        },
    )
    return MERCHANT_LOCATION_KEY
