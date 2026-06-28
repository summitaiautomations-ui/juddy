"""Image loading for the Claude vision API.

Reads any image PIL can open (incl. HEIC from iPhones via pillow-heif),
converts to a Claude-supported format, downsamples if needed, and
returns base64-encoded bytes + media type ready for a vision message.
"""

import base64
import io
from pathlib import Path

from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass  # HEIC support unavailable; other formats still work

# Claude API accepts these natively
NATIVE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "GIF": "image/gif",
    "WEBP": "image/webp",
}

# Disc identification doesn't need full Opus 4.7/4.8 high-res (2576px).
# 1568px is more than enough to read stamps + weight numbers and keeps
# the image token cost predictable.
MAX_LONG_EDGE = 1568


def load_for_api(path):
    """Open image at `path`, convert + resize as needed, return
    (base64_str, media_type) ready to drop into an `image` content block.
    """
    img = Image.open(Path(path).expanduser())

    # Pick output format: keep native if Claude supports it, else JPEG
    if img.format in NATIVE_FORMATS:
        out_format = img.format
        media_type = NATIVE_FORMATS[img.format]
    else:
        out_format = "JPEG"
        media_type = "image/jpeg"

    # Downsample if larger than our cap
    long_edge = max(img.size)
    if long_edge > MAX_LONG_EDGE:
        scale = MAX_LONG_EDGE / long_edge
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size, Image.LANCZOS)

    # JPEG can't carry alpha — flatten RGBA to RGB before saving
    if out_format == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")

    buf = io.BytesIO()
    save_kwargs = {"quality": 88, "optimize": True} if out_format == "JPEG" else {}
    img.save(buf, format=out_format, **save_kwargs)
    return base64.standard_b64encode(buf.getvalue()).decode("ascii"), media_type
