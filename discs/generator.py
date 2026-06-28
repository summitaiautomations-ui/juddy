"""Generate eBay + BST listings via the Claude API.

Uses Claude Opus 4.8 with adaptive thinking + structured outputs.
The system prompt is byte-stable across calls and gets cached (5-min
ephemeral TTL) so repeat generations are cheap.
"""

import json

import anthropic

from discs.disc import Disc
from discs.prompts import SYSTEM_PROMPT

MODEL = "claude-opus-4-8"
MAX_TOKENS = 4096

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
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
    },
    "required": [
        "ebay_title",
        "ebay_description",
        "bst_post",
        "suggested_ebay_category",
        "comp_pricing_search_query",
    ],
    "additionalProperties": False,
}


def generate_listings(disc: Disc, *, api_key: str) -> dict:
    """Call Claude to produce listings for a single disc.

    Returns the parsed JSON dict plus a `_usage` key with token counts
    and cache-hit info.
    """
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": disc.to_prompt()}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError(
            f"Claude refused the request: {getattr(response.stop_details, 'explanation', 'no explanation')}"
        )

    text = next(b.text for b in response.content if b.type == "text")
    result = json.loads(text)
    result["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
    }
    return result
