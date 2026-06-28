"""Generate eBay + BST listings via the Claude API.

Two entry points:
- generate_listings(disc) — manual disc input (CLI prompts)
- generate_from_image(image_path) — vision: identify the disc, then
  generate listings in a single call

Uses Claude Opus 4.8 with adaptive thinking + structured outputs.
The system prompt is byte-stable across calls and gets cached (5-min
ephemeral TTL) so repeat generations are cheap.
"""

import json

import anthropic

from discs import image as image_loader
from discs.disc import Disc
from discs.prompts import SYSTEM_PROMPT

MODEL = "claude-opus-4-8"
MAX_TOKENS = 4096

LISTING_PROPERTIES = {
    "ebay_title": {
        "type": "string",
        "description": "eBay listing title, max 80 characters.",
    },
    "ebay_description": {
        "type": "string",
        "description": "Plain-text eBay description — 4–8 lines, scannable, no HTML.",
    },
    "bst_post": {
        "type": "string",
        "description": "Markdown post for r/discexchange or DGCR BST forum.",
    },
    "suggested_ebay_category": {
        "type": "string",
        "description": "eBay category breadcrumb (e.g. 'Sporting Goods > Outdoor Sports & Recreation > Disc Golf > Discs > Distance Drivers').",
    },
    "comp_pricing_search_query": {
        "type": "string",
        "description": "Search query for eBay sold listings to find comparables.",
    },
}

LISTING_REQUIRED = list(LISTING_PROPERTIES.keys())

# Text-only schema: just the listings
TEXT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": LISTING_PROPERTIES,
    "required": LISTING_REQUIRED,
    "additionalProperties": False,
}

# Photo schema: extracted disc + listings
EXTRACTED_DISC_PROPERTIES = {
    "brand": {"type": "string"},
    "mold": {"type": "string"},
    "plastic": {"type": "string"},
    "weight": {
        "type": ["integer", "null"],
        "description": "Weight in grams, read from printed weight on rim. Null if not visible in photo.",
    },
    "color": {"type": "string"},
    "stamp_condition": {
        "type": "string",
        "enum": ["Mint", "Light Wear", "Faded", "No Stamp / Inked"],
    },
    "estimated_sleeve": {
        "type": "integer",
        "minimum": 1,
        "maximum": 10,
        "description": "Sleeve rating 1-10 based on visible wear in the photo.",
    },
    "category": {
        "type": "string",
        "enum": ["Putter", "Approach", "Midrange", "Fairway Driver", "Distance Driver", "Specialty"],
    },
    "extraction_notes": {
        "type": "string",
        "description": "What you can and can't see clearly. Be specific about uncertainty (weight not visible, rim partially obscured, etc.).",
    },
}

PHOTO_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "extracted_disc": {
            "type": "object",
            "properties": EXTRACTED_DISC_PROPERTIES,
            "required": list(EXTRACTED_DISC_PROPERTIES.keys()),
            "additionalProperties": False,
        },
        **LISTING_PROPERTIES,
    },
    "required": ["extracted_disc"] + LISTING_REQUIRED,
    "additionalProperties": False,
}


def _system_block():
    return [{
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }]


def _usage_dict(response):
    return {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
    }


def _parse_response(response):
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        explanation = getattr(details, "explanation", "no explanation") if details else "no explanation"
        raise RuntimeError(f"Claude refused the request: {explanation}")

    text = next(b.text for b in response.content if b.type == "text")
    result = json.loads(text)
    result["_usage"] = _usage_dict(response)
    return result


def generate_listings(disc: Disc, *, api_key: str) -> dict:
    """Manual path: caller supplies the Disc, get back listings."""
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": TEXT_OUTPUT_SCHEMA},
        },
        system=_system_block(),
        messages=[{"role": "user", "content": disc.to_prompt()}],
    )
    return _parse_response(response)


def generate_from_image(image_path: str, *, api_key: str) -> dict:
    """Photo path: identify the disc from an image, then generate listings.

    Returns both the extracted disc fields (so the caller can verify
    identification) and the listings. Single API call.
    """
    image_data, media_type = image_loader.load_for_api(image_path)

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        # Default effort (high) — visual identification + extraction + listing
        # generation in one shot is harder than the text-only path.
        output_config={
            "format": {"type": "json_schema", "schema": PHOTO_OUTPUT_SCHEMA},
        },
        system=_system_block(),
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "Identify this disc from the photo, then generate listings. "
                        "Be honest about what you can and can't see — if weight isn't "
                        "visible on the rim, leave it null and note it. State your "
                        "uncertainty about condition in extraction_notes."
                    ),
                },
            ],
        }],
    )
    return _parse_response(response)
