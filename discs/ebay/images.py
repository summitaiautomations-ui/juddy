"""Upload disc photos to eBay's picture service via the Trading API.

Sell API's Inventory endpoint requires public image URLs. eBay's Trading
API UploadSiteHostedPictures hosts them for us at no charge, so we don't
need a third-party host.

The Trading API uses XML over HTTP, but the contract is small: send the
image bytes in multipart form, get back a FullURL we can drop straight
into the inventory item's imageUrls array.
"""

import os
import re

import requests

from discs import image as image_loader
from discs.ebay import auth

TRADING_ENDPOINT = "https://api.ebay.com/ws/api.dll"
TRADING_VERSION = "1193"


def _xml_envelope(token):
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<UploadSiteHostedPicturesRequest xmlns="urn:ebay:apis:eBLBaseComponents">'
        f"<RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>"
        "<PictureName>disc</PictureName>"
        "<PictureSet>Supersize</PictureSet>"
        "<ExtensionInDays>30</ExtensionInDays>"
        "</UploadSiteHostedPicturesRequest>"
    )


def upload_one(image_path):
    """Upload a single image. Returns the eBay-hosted FullURL."""
    image_data, media_type = image_loader.load_for_api(image_path)
    import base64
    raw_bytes = base64.b64decode(image_data)

    app_id = os.environ.get("EBAY_APP_ID", "").strip()
    dev_id = os.environ.get("EBAY_DEV_ID", "").strip()
    cert_id = os.environ.get("EBAY_CERT_ID", "").strip()
    if not (app_id and dev_id and cert_id):
        raise RuntimeError("EBAY_APP_ID / EBAY_DEV_ID / EBAY_CERT_ID required for image upload.")

    token = auth.get_access_token()
    envelope = _xml_envelope(token)

    boundary = "----discsBoundary7Z89"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="XML Payload"\r\n'
        "Content-Type: text/xml;charset=utf-8\r\n\r\n"
        f"{envelope}\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="dummy"; filename="image"\r\n'
        f"Content-Type: {media_type}\r\n"
        "Content-Transfer-Encoding: binary\r\n\r\n"
    ).encode("utf-8") + raw_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {
        "X-EBAY-API-COMPATIBILITY-LEVEL": TRADING_VERSION,
        "X-EBAY-API-DEV-NAME": dev_id,
        "X-EBAY-API-APP-NAME": app_id,
        "X-EBAY-API-CERT-NAME": cert_id,
        "X-EBAY-API-CALL-NAME": "UploadSiteHostedPictures",
        "X-EBAY-API-SITEID": "0",  # US
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }

    resp = requests.post(TRADING_ENDPOINT, headers=headers, data=body, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Trading API HTTP {resp.status_code}: {resp.text[:500]}")

    ack_match = re.search(r"<Ack>([^<]+)</Ack>", resp.text)
    ack = ack_match.group(1) if ack_match else "?"
    if ack not in ("Success", "Warning"):
        err = re.search(r"<LongMessage>([^<]+)</LongMessage>", resp.text)
        raise RuntimeError(f"UploadSiteHostedPictures failed (Ack={ack}): {err.group(1) if err else resp.text[:500]}")

    url_match = re.search(r"<FullURL>([^<]+)</FullURL>", resp.text)
    if not url_match:
        raise RuntimeError(f"No FullURL in response: {resp.text[:500]}")
    return url_match.group(1)


def upload_all(image_paths):
    """Upload multiple photos. Returns a list of eBay-hosted URLs."""
    return [upload_one(p) for p in image_paths]
